"""Tests for the readiness-probe."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nodestrength.atlases import all_rois
from nodestrength.inspect import inspect_path, summarize, report_to_json


# Re-use synthetic fixtures from sibling test modules.
from tests.test_bids import _make_bids_subject              # noqa: F401
from tests.test_ideas import (
    _make_ideas_subject,
    _make_participants,
    _make_preprocessed_subject,
)


def test_inspect_empty_dir(tmp_path: Path):
    rep = inspect_path(tmp_path)
    assert rep.verdict == "NOTHING_FOUND"
    assert rep.raw is None and rep.preprocessed is None


def test_inspect_raw_bids_only(tmp_path: Path):
    _make_ideas_subject(tmp_path, "HC001", protocol="NODDI")
    _make_ideas_subject(tmp_path, "P0001", protocol="P58")
    rep = inspect_path(tmp_path)
    assert rep.raw is not None
    assert rep.raw.n_subjects == 2
    assert rep.raw.by_protocol == {"NODDI": 1, "P58": 1}
    assert rep.preprocessed is None


def test_inspect_preprocessed_with_thomas_naming(tmp_path: Path):
    for sid in ("HC001", "HC002"):
        _make_preprocessed_subject(tmp_path, sid)
    rep = inspect_path(tmp_path)
    assert rep.preprocessed is not None
    assert rep.preprocessed.n_subjects == 2
    # The synthetic fixture uses canonical "L.AV" / "R.AV" naming.
    assert rep.preprocessed.n_resolved == rep.preprocessed.n_required == 8


def test_inspect_preprocessed_with_missing_roi(tmp_path: Path):
    """If the node lookup uses unrecognized names, the probe must flag it."""
    sub_dir = tmp_path / "sub-HC001" / "ses-01"
    sub_dir.mkdir(parents=True)
    # Lookup with thalamic ROIs renamed to nonsense the resolver won't match.
    rows = [{"index": 1, "name": "cortex-1"}]
    for i, roi in enumerate(all_rois(), start=2):
        rows.append({"index": i, "name": f"nucleus-{i}-NOPE"})
    pd.DataFrame(rows).to_csv(sub_dir / "node_lookup.tsv", sep=" ",
                              index=False, header=False)
    n = len(rows)
    rng = np.random.default_rng(0)
    M = rng.uniform(0.1, 1.0, size=(n, n))
    M = (M + M.T) / 2
    np.fill_diagonal(M, 0.0)
    np.savetxt(sub_dir / "connectome.csv", M, delimiter=" ")

    rep = inspect_path(tmp_path)
    assert rep.verdict.startswith("PARTIAL")
    assert rep.preprocessed.n_resolved == 0
    assert any(v == "MISSING" for v in rep.preprocessed.roi_resolution.values())


def test_inspect_reads_participants(tmp_path: Path):
    _make_ideas_subject(tmp_path, "HC001", protocol="NODDI")
    _make_participants(tmp_path, [
        {"participant_id": "sub-HC001", "diagnosis": "control",
         "age": 30, "sex": "F"},
    ])
    rep = inspect_path(tmp_path)
    assert rep.participants is not None
    assert rep.participants.n_rows == 1
    # participant_id maps to "subject"; diagnosis maps to "group".
    assert rep.participants.mapped["participant_id"] == "subject"
    assert rep.participants.mapped["diagnosis"] == "group"


def test_inspect_participants_flags_unmapped(tmp_path: Path):
    p = _make_participants(tmp_path, [
        {"participant_id": "sub-HC001", "weird_custom_column": "value",
         "age": 30},
    ])
    rep = inspect_path(tmp_path)
    assert rep.participants is not None
    assert "weird_custom_column" in rep.participants.unmapped


def test_summarize_human_readable(tmp_path: Path):
    _make_ideas_subject(tmp_path, "HC001", protocol="NODDI")
    _make_participants(tmp_path, [
        {"participant_id": "sub-HC001", "diagnosis": "control",
         "age": 30, "sex": "F"},
    ])
    rep = inspect_path(tmp_path)
    text = summarize(rep)
    assert "Verdict:" in text
    assert "RAW BIDS" in text or "participants" in text


def test_report_to_json_roundtrip(tmp_path: Path):
    _make_ideas_subject(tmp_path, "HC001")
    rep = inspect_path(tmp_path)
    blob = report_to_json(rep)
    loaded = json.loads(blob)
    assert loaded["path"] == str(tmp_path)
    assert "verdict" in loaded
