"""BIDS layout walker for the MICA-MICs dataset (and similar).

MICA-MICs (Lariviere et al. 2022, *Scientific Data*) ships in BIDS with a
predictable layout for each healthy adult control. The relevant files we need:

  sub-HC###/
    ses-01/
      anat/sub-HC###_ses-01_T1w.nii.gz
      dwi/ sub-HC###_ses-01_dir-AP_dwi.{nii.gz, bvec, bval, json}
           sub-HC###_ses-01_dir-PA_dwi.{nii.gz, bvec, bval, json}   (reverse PE)

This module discovers those files without depending on ``pybids`` (which pulls
a heavy install graph). It also tolerates the slightly different conventions
of HCP-D, ABCD, and OpenNeuro epilepsy datasets — anything that follows
``sub-*/ses-*/{anat,dwi}/`` will work.

The walker yields ``SubjectFiles`` records — a flat description of each
subject's inputs — which can be fed straight into ``nodestrength run-subject``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, Iterator, List, Optional


# ---------------------------------------------------------------------------
# Record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SubjectFiles:
    """Files for a single subject/session pair."""
    subject_id: str           # e.g. "HC001"
    session: Optional[str]    # e.g. "01" or None for single-session datasets
    t1: Path
    dwi: Path                 # forward-PE diffusion volume
    bvec: Path
    bval: Path
    rpe_b0: Optional[Path]    # reverse-PE b=0 (or full reverse-PE acquisition)

    def to_dict(self) -> dict:
        d = asdict(self)
        for k, v in d.items():
            if isinstance(v, Path):
                d[k] = str(v)
        return d


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

_SUB_RE = re.compile(r"^sub-([A-Za-z0-9]+)$")
_SES_RE = re.compile(r"^ses-([A-Za-z0-9]+)$")


def _list_subjects(bids_root: Path) -> List[Path]:
    return sorted(p for p in bids_root.iterdir()
                  if p.is_dir() and _SUB_RE.match(p.name))


def _list_sessions(subject_dir: Path) -> List[Optional[Path]]:
    sessions = sorted(p for p in subject_dir.iterdir()
                      if p.is_dir() and _SES_RE.match(p.name))
    return sessions if sessions else [None]


def _first_match(directory: Path, patterns: Iterable[str]) -> Optional[Path]:
    """Return the first existing file under ``directory`` matching any pattern."""
    if not directory.exists():
        return None
    for pat in patterns:
        hits = sorted(directory.glob(pat))
        if hits:
            return hits[0]
    return None


def _resolve_t1(anat_dir: Path) -> Optional[Path]:
    return _first_match(anat_dir, [
        "*_T1w.nii.gz",
        "*_run-01_T1w.nii.gz",
        "*_acq-mp2rage_T1w.nii.gz",
    ])


def _resolve_dwi_triple(dwi_dir: Path) -> Optional[tuple[Path, Path, Path]]:
    """Find the forward-PE dMRI volume + its bvec/bval."""
    forward = _first_match(dwi_dir, [
        "*_dir-AP_dwi.nii.gz",
        "*_dir-LR_dwi.nii.gz",
        "*_acq-multiband_dwi.nii.gz",
        "*_dwi.nii.gz",
    ])
    if forward is None:
        return None
    stem = forward.name.replace(".nii.gz", "")
    bvec = dwi_dir / f"{stem}.bvec"
    bval = dwi_dir / f"{stem}.bval"
    if not (bvec.exists() and bval.exists()):
        return None
    return forward, bvec, bval


def _resolve_rpe(dwi_dir: Path, forward: Path) -> Optional[Path]:
    """Find a reverse-PE acquisition matching the forward."""
    # MICA-MICs: dir-PA paired with dir-AP.
    forward_name = forward.name
    candidates = []
    if "_dir-AP_" in forward_name:
        candidates.append(forward_name.replace("_dir-AP_", "_dir-PA_"))
    if "_dir-LR_" in forward_name:
        candidates.append(forward_name.replace("_dir-LR_", "_dir-RL_"))
    candidates.append("*_dir-PA_dwi.nii.gz")
    candidates.append("*_acq-rpe_dwi.nii.gz")
    candidates.append("*_acq-rpe_epi.nii.gz")

    for cand in candidates:
        path = dwi_dir / cand if "*" not in cand else _first_match(dwi_dir, [cand])
        if path is not None and path.exists():
            return path
    return None


def iter_subjects(bids_root: Path,
                  include: Optional[Iterable[str]] = None) -> Iterator[SubjectFiles]:
    """Yield ``SubjectFiles`` for each subject in a BIDS tree.

    Parameters
    ----------
    bids_root : root of the BIDS dataset (the directory containing ``sub-*``).
    include : optional iterable of subject IDs (without the ``sub-`` prefix)
              to restrict the output. ``None`` = include all subjects found.
    """
    bids_root = Path(bids_root)
    if not bids_root.is_dir():
        raise FileNotFoundError(f"BIDS root does not exist: {bids_root}")
    include_set = {s.lstrip("sub-") for s in include} if include else None

    for sub_dir in _list_subjects(bids_root):
        sub_id = _SUB_RE.match(sub_dir.name).group(1)
        if include_set and sub_id not in include_set:
            continue

        for ses_dir in _list_sessions(sub_dir):
            session = _SES_RE.match(ses_dir.name).group(1) if ses_dir else None
            anat_dir = (ses_dir or sub_dir) / "anat"
            dwi_dir = (ses_dir or sub_dir) / "dwi"

            t1 = _resolve_t1(anat_dir)
            triple = _resolve_dwi_triple(dwi_dir)
            if t1 is None or triple is None:
                continue
            forward, bvec, bval = triple
            rpe = _resolve_rpe(dwi_dir, forward)

            yield SubjectFiles(
                subject_id=sub_id,
                session=session,
                t1=t1, dwi=forward, bvec=bvec, bval=bval, rpe_b0=rpe,
            )


def list_subjects(bids_root: Path,
                  include: Optional[Iterable[str]] = None) -> List[SubjectFiles]:
    return list(iter_subjects(bids_root, include=include))


# ---------------------------------------------------------------------------
# Dataset description sniffing
# ---------------------------------------------------------------------------

def dataset_description(bids_root: Path) -> dict:
    """Read ``dataset_description.json`` if present, else return ``{}``."""
    p = Path(bids_root) / "dataset_description.json"
    if not p.exists():
        return {}
    with p.open("r") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Cohort table aggregation
# ---------------------------------------------------------------------------

def build_cohort_long(strength_csvs: Iterable[Path],
                      participants_tsv: Optional[Path] = None) -> "pd.DataFrame":
    """Concatenate per-subject strength CSVs into a long-form cohort table.

    If ``participants_tsv`` is provided (BIDS standard ``participants.tsv``),
    its rows are joined on ``subject``. MICA-MICs ships a participants.tsv
    with ``age`` and ``sex`` columns, which the normative GLM will pick up
    automatically.
    """
    import pandas as pd  # local import keeps the module import-cheap

    frames: List["pd.DataFrame"] = []
    for csv in strength_csvs:
        frames.append(pd.read_csv(csv))
    if not frames:
        raise ValueError("No per-subject strength CSVs provided.")
    cohort = pd.concat(frames, ignore_index=True)

    if participants_tsv is not None and Path(participants_tsv).exists():
        meta = pd.read_csv(participants_tsv, sep="\t")
        # Normalize the participants column to "subject" without the sub- prefix.
        if "participant_id" in meta.columns:
            meta = meta.rename(columns={"participant_id": "subject"})
            meta["subject"] = meta["subject"].astype(str).str.replace(
                r"^sub-", "", regex=True)
        cohort = cohort.merge(meta, how="left", on="subject")

    return cohort
