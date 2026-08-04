"""Normative z-scoring for Desikan–Killiany node strength cohorts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Sequence, Tuple

import numpy as np
import pandas as pd

from nodestrength.normative import (
    OLSFit,
    STRENGTH_COVARIATES,
    VOLUME_COVARIATES,
    _align_columns,
    _build_design,
    _fit_ols,
)


@dataclass
class DkNormativeModel:
    """Per-(side, roi_name) OLS fits on a DK control cohort."""

    target: str
    covariates: Tuple[str, ...]
    fits: Dict[str, OLSFit] = field(default_factory=dict)

    def fit(self, controls_long: pd.DataFrame) -> "DkNormativeModel":
        required = {"side", "roi_name", self.target}
        missing = required - set(controls_long.columns)
        if missing:
            raise KeyError(f"controls_long missing columns: {sorted(missing)}")
        n_subjects = controls_long["subject"].nunique()
        covs = self.covariates
        while len(covs) + 2 > n_subjects and len(covs) > 0:
            covs = covs[:-1]
        self.covariates = covs
        for (side, roi_name), sub in controls_long.groupby(["side", "roi_name"]):
            if len(sub) < 2:
                continue
            key = f"{side}.{roi_name}"
            X, names = _build_design(sub, covs)
            y = sub[self.target].to_numpy(dtype=float)
            self.fits[key] = _fit_ols(X, y, names)
        return self

    def z_score(self, subjects_long: pd.DataFrame) -> pd.Series:
        z = pd.Series(np.nan, index=subjects_long.index, name=f"{self.target}_z")
        for (side, roi_name), sub in subjects_long.groupby(["side", "roi_name"]):
            key = f"{side}.{roi_name}"
            if key not in self.fits:
                continue
            fit = self.fits[key]
            X, current = _build_design(sub, self.covariates)
            X_aligned = _align_columns(X, current, fit.column_names)
            y = sub[self.target].to_numpy(dtype=float)
            resid = y - X_aligned @ fit.beta
            z.loc[sub.index] = resid / fit.residual_std if fit.residual_std > 0 else np.nan
        return z


def _available_covariates(df: pd.DataFrame, covariates: Sequence[str]) -> Tuple[str, ...]:
    out: list[str] = []
    for col in covariates:
        if col not in df.columns:
            continue
        if df[col].notna().sum() == 0:
            continue
        out.append(col)
    return tuple(out)


def _normalize_subject_id(subject_id: str) -> str:
    sid = str(subject_id)
    if sid.startswith("sub-"):
        sid = sid[4:]
    return sid.lstrip("0") or "0"


def prepare_dk_strength_long(
    cohort_strength: pd.DataFrame,
    participants: pd.DataFrame,
) -> pd.DataFrame:
    """Merge node strength with participant covariates for normative fitting."""
    df = cohort_strength.copy()
    df["subject"] = df["subject"].map(_normalize_subject_id)
    df["roi_name"] = df["name"].astype(str).str.split(".", n=1).str[1]
    mb = df.groupby("subject")["strength"].mean().rename("mean_brain_strength")
    df = df.merge(mb, on="subject", how="left")
    meta = participants.drop_duplicates("subject").copy()
    meta["subject"] = meta["subject"].map(_normalize_subject_id)
    df = df.merge(meta, on="subject", how="left")
    return df


def prepare_dk_volume_long(
    cohort_volume: pd.DataFrame,
    participants: pd.DataFrame,
) -> pd.DataFrame:
    df = cohort_volume.copy()
    df["subject"] = df["subject"].map(_normalize_subject_id)
    df["roi_name"] = df["name"].astype(str).str.split(".", n=1).str[1]
    meta = participants.drop_duplicates("subject").copy()
    meta["subject"] = meta["subject"].map(_normalize_subject_id)
    return df.merge(meta, on="subject", how="left")


def fit_dk_strength_model(
    controls_long: pd.DataFrame,
    covariates: Sequence[str] = STRENGTH_COVARIATES,
) -> DkNormativeModel:
    covs = _available_covariates(controls_long, covariates)
    if "mean_brain_strength" not in covs:
        raise ValueError("controls_long must include mean_brain_strength")
    return DkNormativeModel(target="strength", covariates=covs).fit(controls_long)


def fit_dk_volume_model(
    controls_long: pd.DataFrame,
    covariates: Sequence[str] = VOLUME_COVARIATES,
) -> DkNormativeModel:
    covs = _available_covariates(controls_long, covariates)
    return DkNormativeModel(target="volume_mm3", covariates=covs).fit(controls_long)


def side_ai_z_from_controls(
    subject_ai: pd.DataFrame,
    control_ai: pd.DataFrame,
) -> pd.DataFrame:
    """Z-score each ROI's side_ai against the control cohort distribution."""
    stats = (
        control_ai.groupby("roi_name")["side_ai"]
        .agg(["mean", "std"])
        .rename(columns={"mean": "control_mean", "std": "control_std"})
    )
    out = subject_ai.merge(stats, on="roi_name", how="left")
    std = out["control_std"].replace(0, np.nan)
    out["side_ai_z"] = (out["side_ai"] - out["control_mean"]) / std
    return out


def save_dk_model(path: str | Path, model: DkNormativeModel) -> None:
    import pickle
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("wb") as fh:
        pickle.dump(model, fh)


def load_dk_model(path: str | Path) -> DkNormativeModel:
    import pickle
    with Path(path).open("rb") as fh:
        obj = pickle.load(fh)
    if not isinstance(obj, DkNormativeModel):
        raise TypeError(f"Expected DkNormativeModel, got {type(obj).__name__}")
    return obj
