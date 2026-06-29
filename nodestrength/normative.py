"""Normative GLM z-scoring against a healthy control cohort.

Section 2.6 of Piper et al. 2026:

  "Before analyzing thalamocortical strengths, the strength of each nucleus in
  the patient and control groups were z-scored against the distribution of the
  controls after using a general linear model (GLM) built using control data
  that accounted for age, sex, average ROI strength (mean of the connectivity
  strength of all the ROI across the whole brain parcellation), and total
  motion in dMRI sequence."

The same idea is applied to nucleus volumes, with covariates age, sex,
intracranial volume.

Per-nucleus and per-side (R-side patients z-scored vs R-side controls, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Tiny OLS implementation -- avoids a hard statsmodels dependency.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OLSFit:
    """Output of a least-squares fit ``y = X @ beta + eps``."""
    beta: np.ndarray            # (p,)
    residual_std: float         # sample std of residuals (ddof = p)
    column_names: Tuple[str, ...]

    def predict(self, X: np.ndarray) -> np.ndarray:
        return X @ self.beta

    def residual(self, X: np.ndarray, y: np.ndarray) -> np.ndarray:
        return y - self.predict(X)


def _fit_ols(X: np.ndarray, y: np.ndarray, column_names: Sequence[str]) -> OLSFit:
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = max(X.shape[0] - X.shape[1], 1)
    sigma = float(np.sqrt(np.sum(resid ** 2) / dof))
    return OLSFit(beta=beta, residual_std=sigma, column_names=tuple(column_names))


# ---------------------------------------------------------------------------
# Design matrix
# ---------------------------------------------------------------------------

def _build_design(df: pd.DataFrame, covariates: Sequence[str]) -> Tuple[np.ndarray, List[str]]:
    """Build a design matrix with intercept + the listed covariates.

    Categorical covariates (object/category dtype) are one-hot encoded with
    ``drop_first=True`` to avoid singularity. All parts share ``df.index``
    so a final ``pd.concat(axis=1)`` aligns row-wise without introducing
    NaNs.
    """
    parts: List[pd.DataFrame] = [pd.DataFrame({"const": np.ones(len(df))}, index=df.index)]
    for col in covariates:
        series = df[col]
        if series.dtype == object or str(series.dtype).startswith("category"):
            dummies = pd.get_dummies(series, prefix=col, drop_first=True, dtype=float)
            parts.append(dummies)
        else:
            parts.append(series.astype(float).rename(col).to_frame())
    X = pd.concat(parts, axis=1)
    return X.to_numpy(dtype=float), list(X.columns)


# ---------------------------------------------------------------------------
# Normative model
# ---------------------------------------------------------------------------

@dataclass
class NormativeModel:
    """Per-(nucleus, side) OLS fits on a control cohort.

    The model is stratified by ROI key (e.g. ``"L.AV"``) so right-side patients
    are z-scored to right-side controls, as in the paper.
    """
    target: str                                       # "strength" or "volume_mm3"
    covariates: Tuple[str, ...]
    fits: Dict[str, OLSFit] = field(default_factory=dict)

    def fit(self, controls_long: pd.DataFrame) -> "NormativeModel":
        for roi_key, sub in controls_long.groupby(["side", "nucleus"]):
            side, nucleus = roi_key
            key = f"{side}.{nucleus}"
            X, names = _build_design(sub, self.covariates)
            y = sub[self.target].to_numpy(dtype=float)
            self.fits[key] = _fit_ols(X, y, names)
        return self

    def z_score(self, subjects_long: pd.DataFrame) -> pd.Series:
        """Return a Series of z-scores aligned to ``subjects_long.index``."""
        z = pd.Series(np.nan, index=subjects_long.index, name=f"{self.target}_z")
        for roi_key, sub in subjects_long.groupby(["side", "nucleus"]):
            side, nucleus = roi_key
            key = f"{side}.{nucleus}"
            if key not in self.fits:
                continue
            fit = self.fits[key]
            X, current = _build_design(sub, self.covariates)
            # Align to the column space the model was fit in: missing columns
            # (e.g. a sex level absent here) become zero, extras are dropped.
            X_aligned = _align_columns(X, current, fit.column_names)
            y = sub[self.target].to_numpy(dtype=float)
            resid = y - X_aligned @ fit.beta
            z.loc[sub.index] = resid / fit.residual_std
        return z


def _align_columns(X: np.ndarray, current: Sequence[str], target: Sequence[str]) -> np.ndarray:
    """Reshape X so its columns match ``target`` (missing -> 0, extras dropped)."""
    current = list(current)
    target = list(target)
    out = np.zeros((X.shape[0], len(target)), dtype=float)
    for j, col in enumerate(target):
        if col in current:
            out[:, j] = X[:, current.index(col)]
    return out


# Convenience defaults matching the paper.
STRENGTH_COVARIATES: Tuple[str, ...] = ("age", "sex", "mean_brain_strength", "motion")
VOLUME_COVARIATES: Tuple[str, ...] = ("age", "sex", "icv")


def fit_strength_model(controls_long: pd.DataFrame,
                       covariates: Sequence[str] = STRENGTH_COVARIATES) -> NormativeModel:
    return NormativeModel(target="strength", covariates=tuple(covariates)).fit(controls_long)


def fit_volume_model(controls_long: pd.DataFrame,
                     covariates: Sequence[str] = VOLUME_COVARIATES) -> NormativeModel:
    return NormativeModel(target="volume_mm3", covariates=tuple(covariates)).fit(controls_long)
