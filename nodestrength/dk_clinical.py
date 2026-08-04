"""Clinical-report helpers: SOZ-aligned AI and normative tables for DK cohorts."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from nodestrength.asymmetry import resolve_soz_side, soz_ai
from nodestrength.dk_atlas import lr_pair_table
from nodestrength.dk_inputs import subject_file_prefix
from nodestrength.dk_normative import (
    DkNormativeModel,
    _normalize_subject_id,
    fit_dk_strength_model,
    prepare_dk_strength_long,
    side_ai_z_from_controls,
)
from nodestrength.ideas import load_participants


def subject_metadata(participants: pd.DataFrame, subject_id: str) -> Optional[pd.Series]:
    sid = _normalize_subject_id(subject_id)
    rows = participants.loc[
        participants["subject"].map(_normalize_subject_id) == sid
    ]
    if rows.empty:
        return None
    return rows.iloc[0]


def soz_side_for_subject(participants: pd.DataFrame, subject_id: str) -> Optional[str]:
    row = subject_metadata(participants, subject_id)
    if row is None:
        return None
    return resolve_soz_side(row)


def pair_soz_ai_table(
    subject_id: str,
    pair_ai: pd.DataFrame,
    soz_side: Optional[str],
) -> pd.DataFrame:
    """Add ipsi/contra and soz_ai columns to a per-subject ``_ai.csv`` frame."""
    df = pair_ai.copy()
    if soz_side not in ("L", "R"):
        df["soz_side"] = np.nan
        df["ipsi_strength"] = np.nan
        df["contra_strength"] = np.nan
        df["soz_ai"] = np.nan
        return df

    l_col = "L_strength_intra" if "L_strength_intra" in df.columns else "L_strength"
    r_col = "R_strength_intra" if "R_strength_intra" in df.columns else "R_strength"

    def _row(row: pd.Series) -> Tuple[float, float]:
        l_val = float(row[l_col])
        r_val = float(row[r_col])
        if soz_side == "L":
            return l_val, r_val
        return r_val, l_val

    ipsi_contra = df.apply(_row, axis=1, result_type="expand")
    df["soz_side"] = soz_side
    df["ipsi_strength"] = ipsi_contra[0]
    df["contra_strength"] = ipsi_contra[1]
    df["soz_ai"] = [
        soz_ai(i, c) for i, c in zip(df["ipsi_strength"], df["contra_strength"])
    ]
    df["subject"] = subject_id
    return df


def strength_z_pair_table(
    subject_id: str,
    strength: pd.DataFrame,
    model: DkNormativeModel,
    participants_row: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """Per-pair L/R normative z-scores."""
    long = strength.copy()
    long["roi_name"] = long["name"].astype(str).str.split(".", n=1).str[1]
    long["mean_brain_strength"] = float(long["strength"].mean())
    if participants_row is not None:
        for col in model.covariates:
            if col not in long.columns and col in participants_row.index:
                long[col] = participants_row[col]
    long["strength_z"] = model.z_score(long)

    z_by_index = {
        int(row["fs_default_index"]): float(row["strength_z"])
        for _, row in long.iterrows()
        if np.isfinite(row["strength_z"])
    }

    rows: List[dict] = []
    for _, pair in lr_pair_table().iterrows():
        l_z = z_by_index.get(int(pair["L_index"]), np.nan)
        r_z = z_by_index.get(int(pair["R_index"]), np.nan)
        side_z = np.nan
        if np.isfinite(l_z) and np.isfinite(r_z):
            side_z = float(l_z - r_z)
        rows.append({
            "subject": subject_id,
            "roi_name": pair["roi_name"],
            "region_type": pair["region_type"],
            "L_index": int(pair["L_index"]),
            "R_index": int(pair["R_index"]),
            "L_strength_z": l_z,
            "R_strength_z": r_z,
            "side_strength_z": side_z,
        })
    return pd.DataFrame(rows)


def fit_or_load_strength_model(
    results_dir: Path,
    participants: pd.DataFrame,
    *,
    normative_model_path: Optional[Path] = None,
    control_group: str = "control",
) -> Optional[DkNormativeModel]:
    if normative_model_path is not None and normative_model_path.is_file():
        from nodestrength.dk_normative import load_dk_model
        return load_dk_model(normative_model_path)

    cohort_path = results_dir / "strength" / "node_strength_cohort.csv"
    if not cohort_path.is_file() or "group" not in participants.columns:
        return None

    controls = participants.loc[
        participants["group"].astype(str).str.lower() == control_group.lower(),
        "subject",
    ]
    if controls.empty:
        return None

    cohort = pd.read_csv(cohort_path)
    control_ids = {_normalize_subject_id(s) for s in controls}
    controls_long = prepare_dk_strength_long(
        cohort.loc[cohort["subject"].map(_normalize_subject_id).isin(control_ids)],
        participants,
    )
    if controls_long.empty:
        return None
    try:
        return fit_dk_strength_model(controls_long)
    except (ValueError, KeyError):
        return None


def load_subject_clinical_tables(
    results_dir: Path,
    folder_name: str,
    *,
    participants_path: Optional[Path] = None,
    normative_model_path: Optional[Path] = None,
    control_group: str = "control",
) -> Tuple[
    pd.DataFrame,
    Optional[pd.DataFrame],
    Optional[pd.DataFrame],
    Optional[pd.DataFrame],
    Optional[pd.DataFrame],
    Optional[str],
]:
    """Load AI / z / SOZ tables for one subject's clinical report."""
    prefix = subject_file_prefix(folder_name)
    strength_ai = pd.read_csv(results_dir / "strength" / "per_subject" / f"{prefix}_ai.csv")

    intra_path = results_dir / "strength" / "per_subject" / f"{prefix}_ai_intra.csv"
    intra_ai = pd.read_csv(intra_path) if intra_path.is_file() else None

    volume_path = results_dir / "volume" / "per_subject" / f"{prefix}_volume_ai.csv"
    volume_ai = pd.read_csv(volume_path) if volume_path.is_file() else None

    soz_path = results_dir / "strength" / "per_subject" / f"{prefix}_soz_ai.csv"
    soz_ai_df = pd.read_csv(soz_path) if soz_path.is_file() else None

    z_path = results_dir / "strength" / "per_subject" / f"{prefix}_strength_z.csv"
    strength_z = pd.read_csv(z_path) if z_path.is_file() else None

    participants: Optional[pd.DataFrame] = None
    soz_side: Optional[str] = None
    if participants_path is not None and participants_path.is_file():
        participants = load_participants(participants_path)
        sid = prefix[4:] if prefix.startswith("sub-") else prefix
        soz_side = soz_side_for_subject(participants, sid)

    if soz_ai_df is None and soz_side is not None:
        soz_ai_df = pair_soz_ai_table(sid, strength_ai, soz_side)

    if strength_z is None and participants is not None:
        model = fit_or_load_strength_model(
            results_dir,
            participants,
            normative_model_path=normative_model_path,
            control_group=control_group,
        )
        if model is not None:
            strength = pd.read_csv(
                results_dir / "strength" / "per_subject" / f"{prefix}_strength.csv")
            meta = subject_metadata(participants, sid)
            strength_z = strength_z_pair_table(sid, strength, model, meta)
            if "group" in participants.columns:
                controls = participants.loc[
                    participants["group"].astype(str).str.lower() == control_group.lower(),
                    "subject",
                ]
                if not controls.empty:
                    cohort_ai = pd.read_csv(
                        results_dir / "strength" / "asymmetry_index_cohort.csv")
                    control_ids = {_normalize_subject_id(s) for s in controls}
                    control_ai = cohort_ai.loc[
                        cohort_ai["subject"].map(_normalize_subject_id).isin(control_ids)
                    ]
                    z_ai = side_ai_z_from_controls(strength_ai, control_ai)
                    strength_z = strength_z.merge(
                        z_ai[["roi_name", "side_ai_z"]], on="roi_name", how="left")

    return strength_ai, intra_ai, volume_ai, soz_ai_df, strength_z, soz_side
