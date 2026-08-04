"""Tests for DK clinical metrics (SOZ AI and normative z-scores)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nodestrength.asymmetry import soz_ai
from nodestrength.clinical_report import generate_clinical_report
from nodestrength.dk_clinical import pair_soz_ai_table, soz_side_for_subject
from nodestrength.dk_normative import (
    fit_dk_strength_model,
    prepare_dk_strength_long,
    side_ai_z_from_controls,
)
from nodestrength.ideas import load_participants
from tests.test_report_viz import _write_full_strength, _write_minimal_ai, _write_minimal_intra


def _write_participants(path: Path) -> None:
    rows = [
        {"participant_id": "sub-001", "group": "patient", "soz_side": "L",
         "age": 12, "sex": "F"},
        {"participant_id": "sub-002", "group": "control", "age": 11, "sex": "M"},
        {"participant_id": "sub-003", "group": "control", "age": 13, "sex": "F"},
    ]
    pd.DataFrame(rows).to_csv(path, sep="\t", index=False)


def test_soz_side_resolution():
    df = pd.DataFrame([
        {"subject": "001", "soz_side": "L"},
        {"subject": "002", "soz": "right temporal"},
    ])
    assert soz_side_for_subject(df, "001") == "L"
    assert soz_side_for_subject(df, "002") == "R"


def test_pair_soz_ai_table():
    ai = pd.DataFrame([
        {"roi_name": "Thalamus-Proper", "region_type": "subcortical",
         "L_strength": 100.0, "R_strength": 80.0, "side_ai": 0.11},
    ])
    out = pair_soz_ai_table("001", ai, "L")
    assert out.iloc[0]["soz_ai"] == pytest.approx(soz_ai(100.0, 80.0))


def test_dk_normative_z_on_controls(tmp_path: Path):
    _write_full_strength(tmp_path, subject="002")
    _write_full_strength(tmp_path, subject="003")
    frames = []
    for sid in ("002", "003"):
        p = tmp_path / "strength" / "per_subject" / f"sub-{sid}_strength.csv"
        df = pd.read_csv(p)
        df["strength"] = df["strength"] * (1.0 + 0.01 * int(sid))
        frames.append(df)
    cohort = pd.concat(frames, ignore_index=True)
    participants = pd.DataFrame([
        {"subject": "002", "group": "control", "age": 11, "sex": "M"},
        {"subject": "003", "group": "control", "age": 13, "sex": "F"},
    ])
    long = prepare_dk_strength_long(cohort, participants)
    model = fit_dk_strength_model(long)
    z = model.z_score(long)
    assert z.notna().sum() > 0
    assert z.std() == pytest.approx(1.0, abs=0.5)


def test_side_ai_z_from_controls():
    control = pd.DataFrame([
        {"subject": "c1", "roi_name": "Hippocampus", "side_ai": 0.0},
        {"subject": "c2", "roi_name": "Hippocampus", "side_ai": 0.2},
    ])
    patient = pd.DataFrame([
        {"subject": "p1", "roi_name": "Hippocampus", "side_ai": 0.4},
    ])
    out = side_ai_z_from_controls(patient, control)
    assert out.iloc[0]["side_ai_z"] == pytest.approx(2.121, abs=0.05)


def test_clinical_report_with_soz_and_z(tmp_path: Path) -> None:
    _write_full_strength(tmp_path)
    _write_minimal_ai(tmp_path)
    _write_minimal_intra(tmp_path)
    participants = tmp_path / "participants.tsv"
    _write_participants(participants)

    # cohort strength for normative fit
    cohort = pd.read_csv(tmp_path / "strength" / "per_subject" / "sub-001_strength.csv")
    for sid in ("002", "003"):
        df = cohort.copy()
        df["subject"] = sid
        df["strength"] = df["strength"] * (1.0 + 0.01 * int(sid))
        df.to_csv(tmp_path / "strength" / "per_subject" / f"sub-{sid}_strength.csv", index=False)
    cohort_all = pd.concat([
        pd.read_csv(tmp_path / "strength" / "per_subject" / f"sub-{sid}_strength.csv")
        for sid in ("001", "002", "003")
    ], ignore_index=True)
    assert len(cohort_all) == 84 * 3
    cohort_all.to_csv(tmp_path / "strength" / "node_strength_cohort.csv", index=False)
    ai_all = pd.concat([
        pd.read_csv(tmp_path / "strength" / "per_subject" / "sub-001_ai.csv"),
        pd.read_csv(tmp_path / "strength" / "per_subject" / "sub-001_ai.csv").assign(subject="002"),
        pd.read_csv(tmp_path / "strength" / "per_subject" / "sub-001_ai.csv").assign(subject="003"),
    ], ignore_index=True)
    ai_all.to_csv(tmp_path / "strength" / "asymmetry_index_cohort.csv", index=False)

    from nodestrength.dk_clinical import pair_soz_ai_table, strength_z_pair_table
    from nodestrength.dk_normative import fit_dk_strength_model, prepare_dk_strength_long
    parts = load_participants(participants)
    controls_long = prepare_dk_strength_long(
        cohort_all.loc[cohort_all["subject"].map(lambda s: str(s).lstrip("0") or "0").isin({"2", "3"})],
        parts,
    )
    model = fit_dk_strength_model(controls_long)
    ai = pd.read_csv(tmp_path / "strength" / "per_subject" / "sub-001_ai.csv")
    pair_soz_ai_table("001", ai, "L").to_csv(
        tmp_path / "strength" / "per_subject" / "sub-001_soz_ai.csv", index=False)
    strength = pd.read_csv(tmp_path / "strength" / "per_subject" / "sub-001_strength.csv")
    meta = parts.loc[parts["subject"] == "001"].iloc[0]
    strength_z_pair_table("001", strength, model, meta).to_csv(
        tmp_path / "strength" / "per_subject" / "sub-001_strength_z.csv", index=False)

    pdf = generate_clinical_report(
        tmp_path, "sub-001", participants_path=participants, with_figures=False)
    assert pdf.is_file()
    assert pdf.stat().st_size > 800
