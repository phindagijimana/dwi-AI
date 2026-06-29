"""Tests for IDEAS ingestion (raw BIDS + pre-processed archive)."""

from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
import pytest

from nodestrength import ideas
from nodestrength.atlases import ANALYZED_NUCLEI, all_rois


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ideas_subject(root: Path, sid: str, protocol: str = "NODDI",
                        session: str = "01") -> None:
    """Create a fake IDEAS BIDS subject with a protocol-tagged dMRI filename."""
    base = root / f"sub-{sid}" / f"ses-{session}"
    (base / "anat").mkdir(parents=True)
    (base / "dwi").mkdir(parents=True)

    (base / "anat" / f"sub-{sid}_ses-{session}_T1w.nii.gz").write_bytes(b"")
    (base / "anat" / f"sub-{sid}_ses-{session}_FLAIR.nii.gz").write_bytes(b"")

    stem = f"sub-{sid}_ses-{session}_acq-{protocol.lower()}_dir-AP_dwi"
    (base / "dwi" / f"{stem}.nii.gz").write_bytes(b"")
    (base / "dwi" / f"{stem}.bvec").write_text("0 0\n0 0\n0 0\n")
    (base / "dwi" / f"{stem}.bval").write_text("0 1000\n")
    (base / "dwi" / f"{stem}.json").write_text("{}")
    rpe = f"sub-{sid}_ses-{session}_acq-{protocol.lower()}_dir-PA_dwi"
    (base / "dwi" / f"{rpe}.nii.gz").write_bytes(b"")


def _make_participants(root: Path, rows: list[dict]) -> Path:
    df = pd.DataFrame(rows)
    path = root / "participants.tsv"
    df.to_csv(path, sep="\t", index=False)
    return path


# ---------------------------------------------------------------------------
# Raw BIDS ingestion
# ---------------------------------------------------------------------------

def test_protocol_detection_from_filename(tmp_path: Path):
    _make_ideas_subject(tmp_path, "HC001", protocol="NODDI")
    _make_ideas_subject(tmp_path, "P0001", protocol="P58")
    subs = ideas.ingest_raw_bids(tmp_path)
    assert {s.subject_id: s.protocol for s in subs} == {
        "HC001": "NODDI", "P0001": "P58",
    }


def test_topup_params_lookup(tmp_path: Path):
    _make_ideas_subject(tmp_path, "P0001", protocol="P58")
    subs = ideas.ingest_raw_bids(tmp_path)
    assert subs[0].topup_acqp == "0 1 0 0.028388"


def test_load_participants_canonicalises_columns(tmp_path: Path):
    p = _make_participants(tmp_path, [
        {"participant_id": "sub-HC001", "diagnosis": "control",
         "age": 30, "sex": "F"},
        {"participant_id": "sub-P0001", "diagnosis": "epilepsy",
         "seizure_onset_zone": "temporal", "pathology": "HS",
         "outcome": "ILAE 1", "age": 28, "sex": "M"},
    ])
    df = ideas.load_participants(p)
    assert set(df["subject"]) == {"HC001", "P0001"}
    assert set(df["group"].unique()) == {"control", "patient"}
    assert "histopathology" in df.columns
    assert "soz" in df.columns
    assert "seizure_free" in df.columns         # outcome -> seizure_free


def test_raw_bids_attaches_metadata(tmp_path: Path):
    _make_ideas_subject(tmp_path, "HC001")
    _make_ideas_subject(tmp_path, "P0001", protocol="P58")
    p = _make_participants(tmp_path, [
        {"participant_id": "sub-HC001", "diagnosis": "control",
         "age": 30, "sex": "F"},
        {"participant_id": "sub-P0001", "diagnosis": "epilepsy",
         "seizure_onset_zone": "temporal", "pathology": "HS",
         "outcome": "ILAE 1", "age": 28, "sex": "M"},
    ])
    subs = ideas.ingest_raw_bids(tmp_path, participants_tsv=p)
    by_id = {s.subject_id: s for s in subs}
    assert by_id["P0001"].metadata.get("histopathology") == "HS"
    assert by_id["HC001"].metadata.get("group") == "control"


def test_include_filter(tmp_path: Path):
    _make_ideas_subject(tmp_path, "HC001")
    _make_ideas_subject(tmp_path, "HC002")
    subs = ideas.ingest_raw_bids(tmp_path, include=["HC002"])
    assert [s.subject_id for s in subs] == ["HC002"]


# ---------------------------------------------------------------------------
# Pre-processed archive ingestion
# ---------------------------------------------------------------------------

def _make_preprocessed_subject(root: Path, sid: str) -> None:
    """Create a fake pre-processed archive folder for one subject."""
    sub_dir = root / f"sub-{sid}" / "ses-01"
    sub_dir.mkdir(parents=True)

    # Lookup: 4 cortical ROIs + 16 thalamic ROIs (matching tests/conftest.py).
    rows = []
    idx = 1
    for cortical in ("ctx-lh-PG1", "ctx-lh-PG2", "ctx-rh-PG1", "ctx-rh-PG2"):
        rows.append({"index": idx, "name": cortical})
        idx += 1
    for roi in all_rois():
        rows.append({"index": idx, "name": roi.key})
        idx += 1
    lookup_df = pd.DataFrame(rows)
    lookup_df.to_csv(sub_dir / "node_lookup.tsv", sep=" ",
                     index=False, header=False)

    n = len(lookup_df)
    rng = np.random.default_rng(hash(sid) % (2**32))
    M = rng.uniform(0.1, 1.0, size=(n, n))
    M = (M + M.T) / 2
    np.fill_diagonal(M, 0.0)
    np.savetxt(sub_dir / "connectome.csv", M, delimiter=" ")


def test_ingest_preprocessed_smoke(tmp_path: Path):
    for sid in ("HC001", "HC002", "P0001"):
        _make_preprocessed_subject(tmp_path, sid)
    p = _make_participants(tmp_path, [
        {"participant_id": "sub-HC001", "diagnosis": "control",
         "age": 30, "sex": "F"},
        {"participant_id": "sub-HC002", "diagnosis": "control",
         "age": 32, "sex": "M"},
        {"participant_id": "sub-P0001", "diagnosis": "epilepsy",
         "seizure_onset_zone": "temporal", "pathology": "HS",
         "outcome": "ILAE 1", "age": 28, "sex": "M"},
    ])

    cohort = ideas.ingest_preprocessed(tmp_path, participants_tsv=p)
    # 3 subjects × 4 nuclei × 2 sides = 24 rows.
    assert len(cohort) == 24
    assert set(cohort["subject"].unique()) == {"HC001", "HC002", "P0001"}
    assert set(cohort["group"].dropna()) == {"control", "patient"}
    assert cohort["strength"].notna().all()
    assert "motion" in cohort.columns and "icv" in cohort.columns


def test_ingest_preprocessed_runs_glm_end_to_end(tmp_path: Path):
    """Smoke-test that the IDEAS-style cohort can be fed to mixed_anova."""
    from nodestrength.stats import mixed_anova

    for sid in (f"HC{i:03d}" for i in range(8)):
        _make_preprocessed_subject(tmp_path, sid)
    for sid in (f"P{i:03d}" for i in range(8)):
        _make_preprocessed_subject(tmp_path, sid)

    rows = [{"participant_id": f"sub-HC{i:03d}", "diagnosis": "control",
             "age": 25 + i, "sex": "F" if i % 2 else "M"} for i in range(8)]
    rows += [{"participant_id": f"sub-P{i:03d}", "diagnosis": "epilepsy",
              "seizure_onset_zone": "temporal", "pathology": "HS",
              "outcome": "ILAE 4", "age": 26 + i,
              "sex": "F" if i % 2 else "M"} for i in range(8)]
    p = _make_participants(tmp_path, rows)

    cohort = ideas.ingest_preprocessed(tmp_path, participants_tsv=p)
    results = mixed_anova(
        long=cohort, subject="subject",
        within_factors=("nucleus", "side"),
        between_factors=("group",),
        value="strength",
    )
    assert "effect" in results.columns
    assert "partial_eta_sq" in results.columns
    assert results["partial_eta_sq"].notna().all()


def test_split_patients_by_soz_labels(tmp_path: Path):
    cohort = pd.DataFrame([
        {"subject": "P1", "soz": "temporal", "histopathology": "HS"},
        {"subject": "P2", "soz": "temporal", "histopathology": "FCD"},
        {"subject": "P3", "soz": "frontal",  "histopathology": "FCD"},
        {"subject": "P4", "soz": "occipital","histopathology": "tumor"},
    ])
    groups = ideas.split_patients_by_soz(cohort)
    assert "TLE-HS" in groups and groups["TLE-HS"]["subject"].iloc[0] == "P1"
    assert "TLE-other" in groups
    assert "frontal" in groups
    assert "other" in groups
