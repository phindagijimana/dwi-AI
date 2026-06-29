"""Tests for asymmetry-index formulas and cohort-level helper."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from nodestrength.asymmetry import (
    cohort_ai,
    log_ai,
    side_ai,
    soz_ai,
)


# ---------------------------------------------------------------------------
# Scalar formulas
# ---------------------------------------------------------------------------

def test_side_ai_basic():
    assert side_ai(10.0, 5.0) == pytest.approx((10 - 5) / 15)
    assert side_ai(5.0, 10.0) == pytest.approx((5 - 10) / 15)


def test_side_ai_symmetric_returns_zero():
    assert side_ai(7.0, 7.0) == 0.0


def test_side_ai_handles_zeros_and_negatives():
    assert math.isnan(side_ai(0.0, 0.0))
    assert math.isnan(side_ai(1.0, -1.0))   # denom = 0


def test_soz_ai_directionality():
    # Ipsi reduction is negative -- the paper's seizure-free signature.
    assert soz_ai(3.0, 7.0) < 0
    assert soz_ai(7.0, 3.0) > 0
    assert soz_ai(5.0, 5.0) == 0.0


def test_log_ai_basic():
    assert log_ai(math.e, 1.0) == pytest.approx(1.0)
    assert log_ai(1.0, math.e) == pytest.approx(-1.0)


def test_log_ai_invalid_inputs_nan():
    assert math.isnan(log_ai(0.0, 1.0))
    assert math.isnan(log_ai(1.0, 0.0))
    assert math.isnan(log_ai(-1.0, 1.0))
    assert math.isnan(log_ai(float("nan"), 1.0))


# ---------------------------------------------------------------------------
# Cohort-level helper
# ---------------------------------------------------------------------------

def _toy_cohort() -> pd.DataFrame:
    """Two subjects × two nuclei × two sides, with engineered values."""
    return pd.DataFrame([
        # subject HC001 (no SOZ): L=10, R=8 for AV;  L=12, R=12 for CM.
        {"subject": "HC001", "nucleus": "AV", "side": "L", "strength": 10.0,
         "group": "control"},
        {"subject": "HC001", "nucleus": "AV", "side": "R", "strength": 8.0,
         "group": "control"},
        {"subject": "HC001", "nucleus": "CM", "side": "L", "strength": 12.0,
         "group": "control"},
        {"subject": "HC001", "nucleus": "CM", "side": "R", "strength": 12.0,
         "group": "control"},

        # subject P0001 (SOZ = left): L=5, R=9 for AV (ipsi reduction);
        # L=10, R=10 for CM.
        {"subject": "P0001", "nucleus": "AV", "side": "L", "strength": 5.0,
         "group": "patient", "soz_side": "L"},
        {"subject": "P0001", "nucleus": "AV", "side": "R", "strength": 9.0,
         "group": "patient", "soz_side": "L"},
        {"subject": "P0001", "nucleus": "CM", "side": "L", "strength": 10.0,
         "group": "patient", "soz_side": "L"},
        {"subject": "P0001", "nucleus": "CM", "side": "R", "strength": 10.0,
         "group": "patient", "soz_side": "L"},
    ])


def test_cohort_ai_shape():
    ai = cohort_ai(_toy_cohort())
    # 2 subjects × 2 nuclei = 4 rows
    assert len(ai) == 4
    assert set(ai["nucleus"]) == {"AV", "CM"}
    assert {"L", "R", "ipsi", "contra", "side_ai", "soz_ai", "log_ai"} <= set(ai.columns)


def test_cohort_ai_side_ai_values_correct():
    ai = cohort_ai(_toy_cohort()).set_index(["subject", "nucleus"])
    # HC001 AV: (10 - 8) / 18 = 0.111...
    assert ai.loc[("HC001", "AV"), "side_ai"] == pytest.approx(2 / 18)
    # HC001 CM: symmetric -> 0
    assert ai.loc[("HC001", "CM"), "side_ai"] == 0.0


def test_cohort_ai_soz_aware_for_patients():
    ai = cohort_ai(_toy_cohort()).set_index(["subject", "nucleus"])
    # P0001 SOZ = left, AV: ipsi=L=5, contra=R=9 → (5-9)/14 ≈ -0.286.
    row = ai.loc[("P0001", "AV")]
    assert row["soz_side"] == "L"
    assert row["ipsi"] == 5.0
    assert row["contra"] == 9.0
    assert row["soz_ai"] == pytest.approx((5 - 9) / 14)
    assert row["log_ai"] == pytest.approx(math.log(5 / 9))


def test_cohort_ai_soz_nan_for_controls():
    ai = cohort_ai(_toy_cohort()).set_index(["subject", "nucleus"])
    # HC001 has no soz_side -> SOZ-aware AIs are NaN.
    assert pd.isna(ai.loc[("HC001", "AV"), "soz_ai"])
    assert pd.isna(ai.loc[("HC001", "AV"), "log_ai"])
    # ... but side_ai is still computable.
    assert ai.loc[("HC001", "AV"), "side_ai"] == pytest.approx(2 / 18)


def test_cohort_ai_passthrough_columns_join():
    ai = cohort_ai(_toy_cohort())
    assert "group" in ai.columns
    assert (ai[ai["subject"] == "HC001"]["group"] == "control").all()
    assert (ai[ai["subject"] == "P0001"]["group"] == "patient").all()


def test_cohort_ai_parses_soz_from_free_text(_toy_cohort_=_toy_cohort):
    """If soz_side isn't given but a free-text 'soz' contains 'left'/'right',
    we fall back to parsing it."""
    df = _toy_cohort_()
    df = df.drop(columns=["soz_side"], errors="ignore")
    df["soz"] = ["", "", "", "",
                 "right temporal", "right temporal",
                 "right temporal", "right temporal"]
    ai = cohort_ai(df).set_index(["subject", "nucleus"])
    row = ai.loc[("P0001", "AV")]
    # Now SOZ is right, so ipsi=R=9, contra=L=5 -> soz_ai > 0.
    assert row["soz_side"] == "R"
    assert row["ipsi"] == 9.0
    assert row["contra"] == 5.0
    assert row["soz_ai"] == pytest.approx((9 - 5) / 14)


def test_cohort_ai_on_volume_column():
    df = _toy_cohort()
    df["volume_mm3"] = df["strength"] * 100
    ai = cohort_ai(df, value="volume_mm3")
    assert (ai["value_kind"] == "volume_mm3").all()
    # AI ratios are scale-invariant, so values should match the strength run.
    ai_strength = cohort_ai(df, value="strength").set_index(["subject", "nucleus"])
    ai_volume = ai.set_index(["subject", "nucleus"])
    assert (ai_strength["side_ai"] - ai_volume["side_ai"]).abs().max() < 1e-12
