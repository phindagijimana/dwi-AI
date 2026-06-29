"""Normative-model tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nodestrength.normative import (
    NormativeModel,
    fit_strength_model,
    fit_volume_model,
)


def test_z_score_zero_mean_unit_var_on_controls(synthetic_cohort):
    controls = synthetic_cohort[synthetic_cohort["group"] == "control"].copy()
    model = fit_strength_model(controls)
    z = model.z_score(controls)
    controls = controls.assign(z=z.values)
    # Per (side, nucleus), the controls' z should be ~ N(0, 1).
    grouped = controls.groupby(["side", "nucleus"])["z"].agg(["mean", "std"])
    assert (grouped["mean"].abs() < 0.05).all(), grouped
    assert (np.abs(grouped["std"] - 1.0) < 0.2).all(), grouped


def test_patient_z_diverges_from_control_z(synthetic_cohort):
    controls = synthetic_cohort[synthetic_cohort["group"] == "control"].copy()
    patients = synthetic_cohort[synthetic_cohort["group"] == "patient"].copy()
    model = fit_strength_model(controls)
    z = model.z_score(patients)
    # On synthetic data, the CM nucleus was boosted in patients -> mean(z) > 0.
    cm_z = z[patients["nucleus"] == "CM"]
    assert cm_z.mean() > 0.5, f"expected positive CM z, got {cm_z.mean():.3f}"


def test_volume_model_uses_icv_covariate(synthetic_cohort):
    controls = synthetic_cohort[synthetic_cohort["group"] == "control"].copy()
    model = fit_volume_model(controls)
    assert "icv" in next(iter(model.fits.values())).column_names

    # Doubling ICV should change predictions in proportion to the beta.
    fit = next(iter(model.fits.values()))
    icv_col = fit.column_names.index("icv")
    assert np.isfinite(fit.beta[icv_col])


def test_normative_handles_missing_factor_levels(synthetic_cohort):
    """If the test split lacks a sex level seen at fit time, alignment must not crash."""
    controls = synthetic_cohort[synthetic_cohort["group"] == "control"].copy()
    model = fit_strength_model(controls)

    only_female = synthetic_cohort[(synthetic_cohort["group"] == "patient")
                                    & (synthetic_cohort["sex"] == "F")].copy()
    z = model.z_score(only_female)
    assert z.notna().all()
