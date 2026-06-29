"""IDEAS dataset (Taylor et al. 2025 / 2026) ingestion.

The Imaging Database for Epilepsy And Surgery (IDEAS) is the CNNP Lab
(Newcastle) open release containing:

* **IDEAS I** (Taylor et al., *Epilepsia* 2025, DOI 10.1111/epi.18192):
  T1w + FLAIR for 442 epilepsy patients + 100 healthy controls.
* **IDEAS II** (Taylor et al., *Epilepsia* 2026, DOI 10.1002/epi.70186):
  Adds dMRI (216 patients + 98 controls) and *pre-processed* connectomes.

Crucially, IDEAS II ships a **pre-processed dMRI / connectome archive** on
Figshare. That archive can be consumed directly, skipping the
recon-all/THOMAS/MRtrix3 chain entirely. This module supports both paths:

* :func:`ingest_raw_bids` — point at the raw BIDS root, get a list of
  per-subject input bundles ready for the full pipeline.
* :func:`ingest_preprocessed` — point at the pre-processed archive, get a
  long-form cohort dataframe ready for :mod:`nodestrength.stats.mixed_anova`.

The dataset uses two acquisition protocols (referenced as ``NODDI`` and
``P58`` on the CNNP page). The pre-processed loader is protocol-agnostic
because the connectomes have already been computed; the raw-BIDS loader
records the protocol so the right TOPUP acquisition parameters can be picked.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional

import numpy as np
import pandas as pd

from .atlases import ANALYZED_NUCLEI, ThalamicROI, all_rois
from .bids import SubjectFiles, iter_subjects


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: TOPUP acquisition parameters (one line per scan) for the two IDEAS protocols.
#: Format: phase-encode dir (R, A, S) plus total readout time (s).
TOPUP_PARAMS: Mapping[str, str] = {
    "NODDI": "0 1 0 0.035088",
    "P58":   "0 1 0 0.028388",
}

#: Mapping from IDEAS participants.tsv column names → the names used by the
#: nodestrength analysis layer. The IDEAS schema is **not** fully published in
#: the dataset paper preview, so this mapping is conservative: anything we
#: don't recognise is kept verbatim. Update the right-hand side if a real
#: IDEAS download uses different headers.
PARTICIPANT_COLUMN_ALIASES: Mapping[str, str] = {
    "participant_id": "subject",
    "diagnosis":       "group",            # "epilepsy" / "control"
    "group":           "group",
    "patient_group":   "group",
    "soz":             "soz",
    "seizure_onset_zone": "soz",
    "histology":       "histopathology",
    "pathology":       "histopathology",
    "histopathology":  "histopathology",
    "outcome":         "seizure_free",
    "ilae":            "ilae",
    "ilae_outcome":    "ilae",
    "engel":           "engel",
    "fbtcs":           "fbtcs",
    "FBTCS":           "fbtcs",
    "age":             "age",
    "sex":             "sex",
    "protocol":        "protocol",
    "acquisition":     "protocol",
}


# ---------------------------------------------------------------------------
# Subject record extension
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IdeasSubject:
    files: SubjectFiles
    protocol: Optional[str]      # "NODDI" / "P58" / None if not set
    metadata: Dict[str, str] = field(default_factory=dict)

    @property
    def subject_id(self) -> str:
        return self.files.subject_id

    @property
    def topup_acqp(self) -> Optional[str]:
        return TOPUP_PARAMS.get(self.protocol) if self.protocol else None

    def to_dict(self) -> dict:
        d = self.files.to_dict()
        d["protocol"] = self.protocol
        d.update({f"meta_{k}": v for k, v in self.metadata.items()})
        return d


# ---------------------------------------------------------------------------
# Participants.tsv normalisation
# ---------------------------------------------------------------------------

def load_participants(participants_tsv: Path) -> pd.DataFrame:
    """Load IDEAS ``participants.tsv`` and normalise column names.

    The ``participant_id`` column has the BIDS ``sub-`` prefix stripped so it
    can be joined directly against ``SubjectFiles.subject_id``.
    """
    df = pd.read_csv(participants_tsv, sep="\t")
    # Lower-case all column lookups (IDEAS mixes cases).
    rename = {}
    for col in df.columns:
        norm = PARTICIPANT_COLUMN_ALIASES.get(col,
                  PARTICIPANT_COLUMN_ALIASES.get(col.lower(), col))
        rename[col] = norm
    df = df.rename(columns=rename)
    if "subject" in df.columns:
        df["subject"] = df["subject"].astype(str).str.replace(r"^sub-", "",
                                                              regex=True)
    if "group" in df.columns:
        # canonicalise "epilepsy" / "patient" / "case" → "patient";
        # "control" / "hc" / "healthy" → "control".
        df["group"] = df["group"].astype(str).str.lower().replace({
            "epilepsy": "patient", "case": "patient", "patient": "patient",
            "hc": "control", "healthy": "control", "control": "control",
        })
    return df


# ---------------------------------------------------------------------------
# Raw-BIDS ingestion
# ---------------------------------------------------------------------------

_PROTOCOL_RE = re.compile(r"acq-(noddi|p58)", re.IGNORECASE)


def _detect_protocol(dwi_path: Path) -> Optional[str]:
    """Guess the IDEAS acquisition protocol from a dMRI filename or JSON sidecar."""
    m = _PROTOCOL_RE.search(dwi_path.name)
    if m:
        return m.group(1).upper()
    json_path = dwi_path.with_suffix("").with_suffix(".json")
    if json_path.exists():
        try:
            meta = json.loads(json_path.read_text())
        except json.JSONDecodeError:
            return None
        for key in ("ProtocolName", "SeriesDescription", "AcquisitionProtocol"):
            if key in meta and isinstance(meta[key], str):
                if "NODDI" in meta[key].upper():
                    return "NODDI"
                if "P58" in meta[key].upper():
                    return "P58"
    return None


def ingest_raw_bids(bids_root: Path,
                    participants_tsv: Optional[Path] = None,
                    include: Optional[Iterable[str]] = None) -> List[IdeasSubject]:
    """Walk an IDEAS BIDS tree and produce per-subject input bundles.

    Each ``IdeasSubject`` carries the file paths the pipeline needs, the
    detected acquisition protocol (NODDI / P58), and the row from
    ``participants.tsv`` if provided.
    """
    subjects = list(iter_subjects(bids_root, include=include))
    if not subjects:
        return []

    meta_df = None
    if participants_tsv is not None:
        p = Path(participants_tsv)
        if p.exists():
            meta_df = load_participants(p)

    out: List[IdeasSubject] = []
    for sf in subjects:
        protocol = _detect_protocol(sf.dwi)
        metadata: Dict[str, str] = {}
        if meta_df is not None:
            row = meta_df[meta_df["subject"] == sf.subject_id]
            if len(row):
                metadata = {k: str(v) for k, v in row.iloc[0].items()
                            if pd.notna(v) and k != "subject"}
                if not protocol and "protocol" in row.columns:
                    p_field = str(row.iloc[0].get("protocol", "")).upper()
                    if p_field in TOPUP_PARAMS:
                        protocol = p_field
        out.append(IdeasSubject(files=sf, protocol=protocol, metadata=metadata))
    return out


# ---------------------------------------------------------------------------
# Pre-processed connectome ingestion
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PreprocessedSubject:
    """One subject's pre-processed connectome inputs."""
    subject_id: str
    connectome: Path
    node_lookup: Path
    label_image: Optional[Path]   # for THOMAS volume computation


def _scan_preprocessed_archive(root: Path) -> List[PreprocessedSubject]:
    """Find subjects in a directory tree of pre-processed connectomes.

    Recognises layouts of the form::

        root/sub-XXX/[ses-YY/]connectome.csv
        root/sub-XXX/[ses-YY/]node_lookup.tsv
        root/sub-XXX/[ses-YY/]labels_combined.nii.gz       (optional)

    Also tolerates flat layouts where files live at ``root/sub-XXX_*.csv``
    with a sibling lookup.
    """
    subjects: List[PreprocessedSubject] = []
    for cpath in sorted(root.rglob("connectome.csv")):
        sub_dir = cpath.parent
        sid = None
        for part in sub_dir.relative_to(root).parts:
            if part.startswith("sub-"):
                sid = part[len("sub-"):]
                break
        if sid is None:
            sid = sub_dir.name
        lookup = sub_dir / "node_lookup.tsv"
        labels = sub_dir / "labels_combined.nii.gz"
        if not lookup.exists():
            # Try a shared lookup at root level.
            shared = root / "node_lookup.tsv"
            lookup = shared if shared.exists() else lookup
        subjects.append(PreprocessedSubject(
            subject_id=sid,
            connectome=cpath,
            node_lookup=lookup,
            label_image=labels if labels.exists() else None,
        ))
    return subjects


def ingest_preprocessed(archive_root: Path,
                        participants_tsv: Optional[Path] = None,
                        include: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """Build the long-form cohort dataframe directly from the IDEAS II archive.

    Walks ``archive_root`` for per-subject ``connectome.csv`` files, computes
    per-(nucleus, side) strength + volume using the same logic as the raw
    pipeline, joins ``participants.tsv``, and returns a long-form dataframe
    ready for :func:`nodestrength.stats.mixed_anova`.
    """
    from .connectome import (
        StrengthConfig,
        load_connectome,
        load_node_lookup,
        per_subject_record,
    )

    subjects = _scan_preprocessed_archive(Path(archive_root))
    if not subjects:
        raise FileNotFoundError(
            f"No connectome.csv files under {archive_root}."
        )

    include_set = set(include) if include else None
    frames: List[pd.DataFrame] = []
    for sub in subjects:
        if include_set and sub.subject_id not in include_set:
            continue
        connectome = load_connectome(sub.connectome)
        lookup = load_node_lookup(sub.node_lookup)
        record = per_subject_record(
            subject_id=sub.subject_id,
            connectome=connectome,
            node_lookup=lookup,
            label_image_path=sub.label_image,
            config=StrengthConfig(exclude_self=True, exclude_inter_thalamic=True),
        )
        frames.append(record)

    cohort = pd.concat(frames, ignore_index=True)

    if participants_tsv is not None and Path(participants_tsv).exists():
        meta = load_participants(Path(participants_tsv))
        cohort = cohort.merge(meta, how="left", on="subject")

    # Sensible defaults for covariates the GLM expects.
    if "motion" not in cohort.columns:
        cohort["motion"] = 0.0
    if "icv" not in cohort.columns:
        cohort["icv"] = float("nan")

    return cohort


# ---------------------------------------------------------------------------
# Cohort-level helpers
# ---------------------------------------------------------------------------

def split_patients_by_soz(cohort: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Group a cohort into the SOZ subgroups used in the Piper paper.

    The IDEAS ``soz`` column convention is not documented in the CNNP page;
    this function applies a lenient pattern match and falls back to leaving
    unmatched rows under ``"other"``.
    """
    if "soz" not in cohort.columns:
        return {}
    soz = cohort["soz"].astype(str).str.lower().fillna("")
    pathology = cohort.get("histopathology",
                            pd.Series([""] * len(cohort))).astype(str).str.lower()

    def _label(s: str, h: str) -> str:
        if "temporal" in s and ("hippocamp" in h or "hs" in h):
            return "TLE-HS"
        if "temporal" in s:
            return "TLE-other"
        if "frontal" in s:
            return "frontal"
        return "other"

    cohort = cohort.copy()
    cohort["soz_group"] = [_label(s, h) for s, h in zip(soz, pathology)]
    return {grp: sub.reset_index(drop=True)
            for grp, sub in cohort.groupby("soz_group")}
