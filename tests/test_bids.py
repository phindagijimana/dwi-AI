"""Tests for the BIDS walker + cohort table builder.

Builds a fake MICA-MICs-like tree under ``tmp_path`` (no real NIfTI content
required — empty files suffice, since the walker only checks paths).
"""

from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
import pytest

from nodestrength.bids import (
    SubjectFiles,
    build_cohort_long,
    iter_subjects,
    list_subjects,
)


def _make_bids_subject(root: Path, sid: str, session: str = "01",
                       with_rpe: bool = True) -> None:
    """Create a MICA-MICs-style folder layout for one subject."""
    base = root / f"sub-{sid}" / f"ses-{session}"
    (base / "anat").mkdir(parents=True)
    (base / "dwi").mkdir(parents=True)

    (base / "anat" / f"sub-{sid}_ses-{session}_T1w.nii.gz").write_bytes(b"")
    dwi = base / "dwi" / f"sub-{sid}_ses-{session}_dir-AP_dwi.nii.gz"
    bvec = base / "dwi" / f"sub-{sid}_ses-{session}_dir-AP_dwi.bvec"
    bval = base / "dwi" / f"sub-{sid}_ses-{session}_dir-AP_dwi.bval"
    dwi.write_bytes(b"")
    bvec.write_text("0\n0\n0\n")
    bval.write_text("0\n")

    if with_rpe:
        rpe = base / "dwi" / f"sub-{sid}_ses-{session}_dir-PA_dwi.nii.gz"
        rpe.write_bytes(b"")


def test_walker_finds_each_subject(tmp_path: Path):
    _make_bids_subject(tmp_path, "HC001")
    _make_bids_subject(tmp_path, "HC002")
    _make_bids_subject(tmp_path, "HC003", with_rpe=False)
    subs = list_subjects(tmp_path)
    assert [s.subject_id for s in subs] == ["HC001", "HC002", "HC003"]
    assert all(s.session == "01" for s in subs)
    assert subs[0].rpe_b0 is not None
    assert subs[2].rpe_b0 is None    # the no-rpe one


def test_include_filter(tmp_path: Path):
    _make_bids_subject(tmp_path, "HC001")
    _make_bids_subject(tmp_path, "HC002")
    subs = list_subjects(tmp_path, include=["HC002"])
    assert [s.subject_id for s in subs] == ["HC002"]


def test_walker_handles_no_session(tmp_path: Path):
    sid = "HC100"
    base = tmp_path / f"sub-{sid}"
    (base / "anat").mkdir(parents=True)
    (base / "dwi").mkdir(parents=True)
    (base / "anat" / f"sub-{sid}_T1w.nii.gz").write_bytes(b"")
    (base / "dwi" / f"sub-{sid}_dwi.nii.gz").write_bytes(b"")
    (base / "dwi" / f"sub-{sid}_dwi.bvec").write_text("0")
    (base / "dwi" / f"sub-{sid}_dwi.bval").write_text("0")
    subs = list_subjects(tmp_path)
    assert len(subs) == 1
    assert subs[0].session is None


def test_walker_skips_subjects_missing_dwi(tmp_path: Path):
    sid = "HC050"
    base = tmp_path / f"sub-{sid}" / "ses-01"
    (base / "anat").mkdir(parents=True)
    (base / "anat" / f"sub-{sid}_ses-01_T1w.nii.gz").write_bytes(b"")
    # no dwi/ folder at all
    subs = list_subjects(tmp_path)
    assert subs == []


def test_subject_files_to_dict_serializes_paths(tmp_path: Path):
    _make_bids_subject(tmp_path, "HC001")
    subs = list_subjects(tmp_path)
    d = subs[0].to_dict()
    assert isinstance(d["t1"], str)
    assert d["t1"].endswith(".nii.gz")


# ---------------------------------------------------------------------------
# Cohort builder
# ---------------------------------------------------------------------------

def _write_subject_record(tmp_path: Path, sid: str) -> Path:
    df = pd.DataFrame([
        {"subject": sid, "nucleus": "AV", "side": "L", "strength": 10.0,
         "volume_mm3": 900.0, "mean_brain_strength": 1.0},
        {"subject": sid, "nucleus": "AV", "side": "R", "strength": 11.0,
         "volume_mm3": 910.0, "mean_brain_strength": 1.0},
    ])
    path = tmp_path / f"{sid}.csv"
    df.to_csv(path, index=False)
    return path


def test_build_cohort_long_joins_participants(tmp_path: Path):
    a = _write_subject_record(tmp_path, "HC001")
    b = _write_subject_record(tmp_path, "HC002")
    participants = tmp_path / "participants.tsv"
    participants.write_text("participant_id\tage\tsex\n"
                            "sub-HC001\t25\tF\n"
                            "sub-HC002\t30\tM\n")
    cohort = build_cohort_long([a, b], participants_tsv=participants)
    assert set(cohort["subject"]) == {"HC001", "HC002"}
    assert {"age", "sex"} <= set(cohort.columns)
    assert cohort.loc[cohort["subject"] == "HC001", "age"].iloc[0] == 25


def test_build_cohort_long_without_participants(tmp_path: Path):
    a = _write_subject_record(tmp_path, "HC001")
    cohort = build_cohort_long([a])
    assert "age" not in cohort.columns
    assert len(cohort) == 2
