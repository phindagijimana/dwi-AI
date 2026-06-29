"""Readiness probe for an IDEAS (or generic BIDS / pre-processed) download.

Run before launching the pipeline on a real dataset. Reports:

* Whether the path looks like a raw BIDS tree, a pre-processed archive, or both.
* How many subjects we can discover, and per subject whether all required
  files (T1, dMRI, bvec/bval, reverse-PE, connectome, lookup) exist.
* Which ``participants.tsv`` columns we recognise vs which we'd silently drop.
* Whether the thalamic ROIs in one example node-lookup resolve to all 8 ROIs
  we need (4 nuclei × 2 sides), and which name variants matched.
* A single 'ready / not-ready' verdict per discovered path.

The output is JSON for programmatic use plus a short human-readable summary
on stdout. Paste the JSON back if anything looks off and we can wire fixes.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from .atlases import ANALYZED_NUCLEI, all_rois
from .bids import iter_subjects
from .connectome import _name_to_row, _roi_row, load_node_lookup
from .ideas import (
    PARTICIPANT_COLUMN_ALIASES,
    _scan_preprocessed_archive,
    load_participants,
)


# ---------------------------------------------------------------------------
# Report records
# ---------------------------------------------------------------------------

@dataclass
class ParticipantsReport:
    path: Optional[str]
    n_rows: int
    mapped: Dict[str, str] = field(default_factory=dict)        # raw → canonical
    unmapped: List[str] = field(default_factory=list)
    canonical_present: List[str] = field(default_factory=list)
    canonical_missing: List[str] = field(default_factory=list)


@dataclass
class RawBidsReport:
    n_subjects: int
    n_with_rpe: int
    by_protocol: Dict[str, int] = field(default_factory=dict)
    sample_subject: Optional[Dict[str, str]] = None


@dataclass
class PreprocessedReport:
    n_subjects: int
    sample_subject: Optional[str] = None
    sample_lookup_head: List[str] = field(default_factory=list)
    roi_resolution: Dict[str, str] = field(default_factory=dict)  # roi_key → matched name or "MISSING"
    n_resolved: int = 0
    n_required: int = 8
    connectome_shape: Optional[List[int]] = None


@dataclass
class InspectReport:
    path: str
    raw: Optional[RawBidsReport] = None
    preprocessed: Optional[PreprocessedReport] = None
    participants: Optional[ParticipantsReport] = None
    verdict: str = ""
    notes: List[str] = field(default_factory=list)


CANONICAL_PARTICIPANT_COLS = ("subject", "group", "soz", "histopathology",
                              "seizure_free", "fbtcs", "age", "sex")


# ---------------------------------------------------------------------------
# Probes
# ---------------------------------------------------------------------------

def _inspect_participants(participants_path: Path) -> ParticipantsReport:
    raw = pd.read_csv(participants_path, sep="\t", nrows=5)
    mapped: Dict[str, str] = {}
    unmapped: List[str] = []
    for col in raw.columns:
        canonical = PARTICIPANT_COLUMN_ALIASES.get(
            col, PARTICIPANT_COLUMN_ALIASES.get(col.lower(), None))
        if canonical:
            mapped[col] = canonical
        else:
            unmapped.append(col)

    canonical_present = sorted(set(mapped.values()))
    canonical_missing = [c for c in CANONICAL_PARTICIPANT_COLS
                         if c not in canonical_present]

    # Count rows once (slurp the full file just for the row count).
    n_rows = sum(1 for _ in open(participants_path)) - 1
    return ParticipantsReport(
        path=str(participants_path),
        n_rows=max(n_rows, 0),
        mapped=mapped,
        unmapped=unmapped,
        canonical_present=canonical_present,
        canonical_missing=canonical_missing,
    )


def _inspect_raw_bids(root: Path) -> RawBidsReport:
    subs = list(iter_subjects(root))
    if not subs:
        return RawBidsReport(n_subjects=0, n_with_rpe=0)
    n_rpe = sum(1 for s in subs if s.rpe_b0 is not None)

    # Protocol via the IDEAS-aware detector (re-uses _detect_protocol).
    from .ideas import _detect_protocol
    proto_counts: Dict[str, int] = {}
    for s in subs:
        p = _detect_protocol(s.dwi) or "unknown"
        proto_counts[p] = proto_counts.get(p, 0) + 1

    sample = subs[0]
    sample_dict = {
        "subject_id": sample.subject_id,
        "session": sample.session or "",
        "t1": str(sample.t1),
        "dwi": str(sample.dwi),
        "rpe_b0": str(sample.rpe_b0) if sample.rpe_b0 else "",
    }
    return RawBidsReport(
        n_subjects=len(subs), n_with_rpe=n_rpe,
        by_protocol=proto_counts, sample_subject=sample_dict,
    )


def _inspect_preprocessed(root: Path) -> PreprocessedReport:
    subjects = _scan_preprocessed_archive(root)
    if not subjects:
        return PreprocessedReport(n_subjects=0)
    sample = subjects[0]

    rep = PreprocessedReport(
        n_subjects=len(subjects),
        sample_subject=sample.subject_id,
    )

    if not sample.node_lookup.exists():
        rep.roi_resolution = {"_error": f"node_lookup missing: {sample.node_lookup}"}
        return rep

    lookup = load_node_lookup(sample.node_lookup)
    rep.sample_lookup_head = lookup["name"].head(20).tolist()
    mapping = _name_to_row(lookup)

    n_resolved = 0
    analyzed = [r for r in all_rois() if r.name in ANALYZED_NUCLEI]
    for roi in analyzed:
        try:
            row_idx = _roi_row(roi, mapping)
            matched = next((n for n, i in mapping.items() if i == row_idx), "?")
            rep.roi_resolution[roi.key] = matched
            n_resolved += 1
        except KeyError:
            rep.roi_resolution[roi.key] = "MISSING"
    rep.n_resolved = n_resolved
    rep.n_required = len(analyzed)

    # Connectome shape.
    try:
        import numpy as np
        cmat = np.loadtxt(sample.connectome)
        rep.connectome_shape = list(cmat.shape)
    except Exception as exc:                              # pragma: no cover
        rep.connectome_shape = None
        rep.roi_resolution["_connectome_error"] = str(exc)

    return rep


def inspect_path(path: Path) -> InspectReport:
    """Detect what's at ``path`` (raw BIDS / pre-processed / both) and probe it."""
    path = Path(path)
    rep = InspectReport(path=str(path))
    if not path.is_dir():
        rep.verdict = "NOT_A_DIRECTORY"
        return rep

    # Raw BIDS detection: presence of any sub-* with anat/ and dwi/ children.
    looks_raw = any(
        (sub / d).is_dir()
        for sub in path.iterdir() if sub.is_dir() and sub.name.startswith("sub-")
        for d in ("anat", "dwi", "ses-01")
    )
    if looks_raw:
        rep.raw = _inspect_raw_bids(path)

    # Pre-processed detection: presence of any connectome.csv.
    if any(path.rglob("connectome.csv")):
        rep.preprocessed = _inspect_preprocessed(path)

    # participants.tsv detection.
    participants_candidates = [
        path / "participants.tsv",
        *path.glob("*participants*.tsv"),
    ]
    for cand in participants_candidates:
        if cand.exists():
            try:
                rep.participants = _inspect_participants(cand)
            except Exception as exc:                          # pragma: no cover
                rep.notes.append(f"participants.tsv parse error: {exc}")
            break

    # Verdict
    parts = []
    if rep.raw:
        parts.append(f"raw_bids({rep.raw.n_subjects} subjects)")
    if rep.preprocessed:
        if rep.preprocessed.n_resolved == rep.preprocessed.n_required:
            parts.append(f"preprocessed({rep.preprocessed.n_subjects} subjects, ROIs ok)")
        else:
            parts.append(f"preprocessed({rep.preprocessed.n_subjects} subjects, "
                         f"ROIs: {rep.preprocessed.n_resolved}/{rep.preprocessed.n_required})")
    if rep.participants:
        if not rep.participants.canonical_missing or rep.participants.canonical_missing == ["subject"]:
            parts.append(f"participants({rep.participants.n_rows} rows, mapped)")
        else:
            parts.append(f"participants({rep.participants.n_rows} rows, "
                         f"missing: {','.join(rep.participants.canonical_missing)})")

    if not parts:
        rep.verdict = "NOTHING_FOUND"
    elif rep.preprocessed and rep.preprocessed.n_resolved < rep.preprocessed.n_required:
        rep.verdict = "PARTIAL — fix ROI names"
    elif (rep.participants and "group" in rep.participants.canonical_missing
          and "soz" in rep.participants.canonical_missing):
        rep.verdict = "PARTIAL — fix participants.tsv mapping"
    else:
        rep.verdict = "READY"

    rep.notes.append("Discovered: " + " + ".join(parts) if parts
                     else "Nothing discovered.")
    return rep


# ---------------------------------------------------------------------------
# Pretty-printer
# ---------------------------------------------------------------------------

def summarize(report: InspectReport) -> str:
    lines = [
        f"=== nodestrength inspect: {report.path} ===",
        f"Verdict: {report.verdict}",
        "",
    ]
    for note in report.notes:
        lines.append(f"- {note}")
    lines.append("")

    if report.raw:
        r = report.raw
        lines.append(f"[RAW BIDS] {r.n_subjects} subjects "
                     f"({r.n_with_rpe} with reverse-PE).")
        if r.by_protocol:
            lines.append(f"  Protocols: {r.by_protocol}")
        if r.sample_subject:
            lines.append(f"  Sample subject: {r.sample_subject['subject_id']}")
            for k in ("t1", "dwi", "rpe_b0"):
                if r.sample_subject.get(k):
                    lines.append(f"    {k}: {r.sample_subject[k]}")
        lines.append("")

    if report.preprocessed:
        p = report.preprocessed
        lines.append(f"[PRE-PROCESSED] {p.n_subjects} subjects.")
        if p.connectome_shape:
            lines.append(f"  Connectome shape: {tuple(p.connectome_shape)}")
        lines.append(f"  Thalamic ROIs resolved: {p.n_resolved}/{p.n_required}")
        for roi_key in sorted(p.roi_resolution):
            marker = "" if p.roi_resolution[roi_key] != "MISSING" else "  ← FIX"
            lines.append(f"    {roi_key:8s} → {p.roi_resolution[roi_key]}{marker}")
        if p.sample_lookup_head:
            lines.append(f"  Sample node-lookup head: {p.sample_lookup_head[:8]}")
        lines.append("")

    if report.participants:
        pp = report.participants
        lines.append(f"[participants.tsv] {pp.n_rows} rows.")
        for raw, canon in pp.mapped.items():
            lines.append(f"  {raw:25s} → {canon}")
        if pp.unmapped:
            lines.append(f"  Unmapped columns (silently dropped): {pp.unmapped}")
        if pp.canonical_missing:
            lines.append(f"  Canonical labels missing: {pp.canonical_missing}")
        lines.append("")

    return "\n".join(lines)


def report_to_json(report: InspectReport) -> str:
    """Serialize the report — paste this back if anything looks off."""
    def encode(obj):
        if hasattr(obj, "__dict__"):
            return asdict(obj)
        return obj
    return json.dumps(encode(report), indent=2)
