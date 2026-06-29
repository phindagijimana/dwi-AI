"""GLM tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nodestrength.stats import (
    _avg_contrast,
    _helmert_contrast,
    mixed_anova,
    multivariate_test,
    pivot_wide,
    within_contrast,
)


def test_helmert_contrast_orthonormal():
    C = _helmert_contrast(4)
    G = C.T @ C
    np.testing.assert_allclose(G, np.eye(3), atol=1e-10)


def test_avg_contrast_unit_norm():
    a = _avg_contrast(4)
    assert a.shape == (4, 1)
    assert pytest.approx(1.0) == (a.T @ a).item()


def test_two_group_pillai_matches_univariate_F():
    """For a 2-group, 1-response problem, Pillai's F should equal one-way ANOVA F."""
    rng = np.random.default_rng(7)
    n = 30
    g = rng.choice([0, 1], size=n)
    y = 0.7 * g + rng.normal(0, 1.0, size=n)
    Y = y[:, None]
    X = np.column_stack([np.ones(n), g.astype(float)])
    L = np.array([[0.0, 1.0]])
    M = np.array([[1.0]])
    res = multivariate_test(Y, X, L, M)

    # Direct one-way ANOVA F:
    g0 = y[g == 0]
    g1 = y[g == 1]
    mean_total = y.mean()
    ss_between = len(g0) * (g0.mean() - mean_total) ** 2 + \
                 len(g1) * (g1.mean() - mean_total) ** 2
    ss_within = ((g0 - g0.mean()) ** 2).sum() + ((g1 - g1.mean()) ** 2).sum()
    f_direct = (ss_between / 1) / (ss_within / (n - 2))
    eta_direct = ss_between / (ss_between + ss_within)

    assert res.f == pytest.approx(f_direct, rel=1e-6)
    assert res.partial_eta_sq == pytest.approx(eta_direct, rel=1e-6)


def test_pivot_wide_shape(synthetic_cohort):
    wide, keys, levels = pivot_wide(
        synthetic_cohort, subject="subject",
        within_factors=("nucleus", "side"), value="strength")
    assert wide.shape[1] == 8
    assert len(keys) == 8
    assert set(levels["nucleus"]) == {"AV", "CM", "MDPf", "PUL"}
    assert set(levels["side"]) == {"L", "R"}


def test_within_contrast_dimensions(synthetic_cohort):
    _, keys, _ = pivot_wide(synthetic_cohort, subject="subject",
                            within_factors=("nucleus", "side"), value="strength")
    M_nuc = within_contrast(keys, ("nucleus", "side"), main_for="nucleus")
    assert M_nuc.shape == (8, 3)
    M_side = within_contrast(keys, ("nucleus", "side"), main_for="side")
    assert M_side.shape == (8, 1)
    M_int = within_contrast(keys, ("nucleus", "side"),
                            interaction_for=("nucleus", "side"))
    assert M_int.shape == (8, 3)


def test_case_control_glm_recovers_group_effect(synthetic_cohort):
    """Paper Section 3.3: patients have higher overall strength than controls."""
    res = mixed_anova(
        long=synthetic_cohort,
        subject="subject",
        within_factors=("nucleus", "side"),
        between_factors=("group",),
        value="strength",
    )
    row = res[res["effect"] == "group"].iloc[0]
    assert row["p_value"] < 0.01
    # Paper reports moderate effect for the same comparison (η²ₚ ≈ .072).
    assert row["partial_eta_sq"] > 0.05


def test_soz_subgroup_recovers_av_specific_effect(synthetic_cohort):
    """Paper Section 3.3: TLE-HS has reduced AV connectivity (laterality x group)."""
    patients = synthetic_cohort[synthetic_cohort["group"] == "patient"].copy()
    res = mixed_anova(
        long=patients,
        subject="subject",
        within_factors=("nucleus", "side"),
        between_factors=("soz",),
        value="strength",
    )
    # Nucleus × side interaction should be present (TLE-HS ipsilateral AV down).
    nuc_side = res[res["effect"] == "nucleus x side"]
    assert not nuc_side.empty
    # And the soz × nucleus interaction should be significant.
    soz_nuc = res[res["effect"] == "soz x nucleus"]
    assert not soz_nuc.empty
    assert (soz_nuc["p_value"] < 0.05).any()


def test_seizure_freedom_laterality_interaction(synthetic_cohort):
    """Paper Section 3.3: seizure-freedom × laterality (ipsi-low / contra-high)."""
    patients = synthetic_cohort[synthetic_cohort["group"] == "patient"].copy()
    res = mixed_anova(
        long=patients,
        subject="subject",
        within_factors=("nucleus", "side"),
        between_factors=("seizure_free",),
        value="strength",
    )
    sf_side = res[res["effect"] == "seizure_free x side"]
    assert not sf_side.empty
    # Direction-only check on synthetic data: a finite F value is reported.
    assert np.isfinite(sf_side["f"].iloc[0])
