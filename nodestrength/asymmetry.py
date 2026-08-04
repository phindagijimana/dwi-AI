"""Asymmetry indices (AI) derived from per-side node strength.

The Piper paper *does not* define a closed-form AI — it tests asymmetry as a
``laterality x {group, SOZ, seizure_free}`` interaction in the mixed-design
GLM. This module is a complement, not a replacement: it folds the two sides
of each thalamic nucleus into a per-(subject, nucleus) scalar, useful when

* you want a continuous biomarker to correlate with a continuous outcome
  (ILAE bins, disease duration, AED count, age at first seizure);
* you need a per-subject value for plotting (one dot per patient);
* you want a quick screen before the full mixed GLM.

Three standard formulas are provided. All are bounded except ``log_ai``.

Notation::

    L         strength of the left-side ROI
    R         strength of the right-side ROI
    ipsi      strength of the ROI on the seizure-onset-zone (SOZ) side
    contra    strength of the ROI on the contralateral side
    soz_side  "L" or "R" — which hemisphere the SOZ is in (per patient)

Formulas::

    side_ai = (L - R) / (L + R)                          # range [-1, +1]
    soz_ai  = (ipsi - contra) / (ipsi + contra)          # range [-1, +1]
    log_ai  = ln(ipsi / contra)                          # range (-inf, +inf)

``side_ai`` does not need SOZ information; it's the standard hemispheric
asymmetry. ``soz_ai`` and ``log_ai`` require a per-subject SOZ side; rows
without it return NaN. Negative ``soz_ai`` matches the paper's *"ipsilateral
reduction / contralateral preservation"* signature in seizure-free patients.
"""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Scalar formulas
# ---------------------------------------------------------------------------

def side_ai(L: float, R: float) -> float:
    """Symmetric hemispheric asymmetry, ``(L - R) / (L + R)``.

    Returns NaN if ``L + R <= 0`` (no signal).
    """
    denom = L + R
    if not np.isfinite(denom) or denom <= 0:
        return float("nan")
    return float((L - R) / denom)


def soz_ai(ipsi: float, contra: float) -> float:
    """SOZ-aligned asymmetry, ``(ipsi - contra) / (ipsi + contra)``.

    Negative values mean ipsilateral *reduction* relative to contralateral —
    the direction the paper reports for seizure-free patients (Figure 4C).
    Returns NaN if ``ipsi + contra <= 0``.
    """
    denom = ipsi + contra
    if not np.isfinite(denom) or denom <= 0:
        return float("nan")
    return float((ipsi - contra) / denom)


def log_ai(ipsi: float, contra: float) -> float:
    """Log-ratio asymmetry, ``ln(ipsi / contra)``.

    Symmetric around zero, unbounded — well-suited to downstream linear
    regression. Returns NaN if either input is <= 0 or non-finite.
    """
    if not (np.isfinite(ipsi) and np.isfinite(contra)):
        return float("nan")
    if ipsi <= 0 or contra <= 0:
        return float("nan")
    return float(np.log(ipsi / contra))


# ---------------------------------------------------------------------------
# Cohort-level helper
# ---------------------------------------------------------------------------

def resolve_soz_side(row: pd.Series, soz_side_col: Optional[str] = "soz_side") -> Optional[str]:
    """Public wrapper for SOZ hemisphere resolution ("L" / "R" / None)."""
    return _resolve_soz_side(row, soz_side_col)


def _resolve_soz_side(row: pd.Series, soz_side_col: Optional[str]) -> Optional[str]:
    """Determine the SOZ side ("L" / "R") for a subject, or None."""
    if soz_side_col and soz_side_col in row and isinstance(row[soz_side_col], str):
        s = row[soz_side_col].strip().upper()
        if s in ("L", "LEFT"):
            return "L"
        if s in ("R", "RIGHT"):
            return "R"
    # Fall back: parse from a free-text SOZ string like "left temporal".
    soz = row.get("soz")
    if isinstance(soz, str):
        s = soz.strip().lower()
        if "left" in s:
            return "L"
        if "right" in s:
            return "R"
    return None


def cohort_ai(
    cohort_long: pd.DataFrame,
    value: str = "strength",
    subject_col: str = "subject",
    nucleus_col: str = "nucleus",
    side_col: str = "side",
    soz_side_col: Optional[str] = "soz_side",
    extra_passthrough: Sequence[str] = ("group", "soz", "seizure_free",
                                        "fbtcs", "histopathology",
                                        "age", "sex"),
) -> pd.DataFrame:
    """Collapse long-form (subject, nucleus, side, ...) → per-(subject, nucleus) AI.

    Parameters
    ----------
    cohort_long
        Long-form cohort dataframe as produced by ``per_subject_record`` or
        ``ingest_preprocessed`` — one row per (subject, nucleus, side).
    value
        Column to compute AI on. Default ``"strength"``; pass
        ``"volume_mm3"`` for nucleus-volume asymmetry.
    soz_side_col
        Optional column carrying the SOZ side ("L" / "R" / "left" / "right").
        If ``None`` or missing, ``soz_ai`` / ``log_ai`` are NaN; ``side_ai``
        is still computed.
    extra_passthrough
        Per-subject columns to carry forward into the AI dataframe (joined
        on ``subject``). Missing columns are silently skipped.

    Returns
    -------
    pd.DataFrame
        One row per (subject, nucleus) with columns:
        ``subject, nucleus, L, R, ipsi, contra, soz_side,
        side_ai, soz_ai, log_ai, value_kind`` + any pass-through columns.
    """
    if value not in cohort_long.columns:
        raise KeyError(f"Column {value!r} not found in cohort.")

    # Pivot to wide so each (subject, nucleus) is one row with L / R cells.
    wide = (
        cohort_long
        .pivot_table(index=[subject_col, nucleus_col],
                     columns=side_col, values=value, aggfunc="mean")
        .reset_index()
    )
    # Ensure both columns exist even if one side is entirely missing.
    for s in ("L", "R"):
        if s not in wide.columns:
            wide[s] = float("nan")

    # Per-subject SOZ side (one value per subject).
    per_subject_cols = [subject_col]
    if soz_side_col and soz_side_col in cohort_long.columns:
        per_subject_cols.append(soz_side_col)
    if "soz" in cohort_long.columns and "soz" not in per_subject_cols:
        per_subject_cols.append("soz")
    per_subject = cohort_long[per_subject_cols].drop_duplicates(subject_col)
    side_lookup = {
        sid: _resolve_soz_side(row, soz_side_col)
        for sid, row in per_subject.set_index(subject_col).iterrows()
    }
    wide["soz_side"] = wide[subject_col].map(side_lookup)

    # Ipsi / contra columns.
    def _ipsi(row):
        return row["L"] if row["soz_side"] == "L" else (
               row["R"] if row["soz_side"] == "R" else float("nan"))

    def _contra(row):
        return row["R"] if row["soz_side"] == "L" else (
               row["L"] if row["soz_side"] == "R" else float("nan"))

    wide["ipsi"] = wide.apply(_ipsi, axis=1)
    wide["contra"] = wide.apply(_contra, axis=1)

    # The three formulas.
    wide["side_ai"] = [side_ai(L, R) for L, R in zip(wide["L"], wide["R"])]
    wide["soz_ai"] = [soz_ai(i, c) for i, c in zip(wide["ipsi"], wide["contra"])]
    wide["log_ai"] = [log_ai(i, c) for i, c in zip(wide["ipsi"], wide["contra"])]
    wide["value_kind"] = value

    # Join optional per-subject pass-through columns.
    keep_extra = [c for c in extra_passthrough if c in cohort_long.columns]
    if keep_extra:
        meta = cohort_long[[subject_col] + keep_extra].drop_duplicates(subject_col)
        wide = wide.merge(meta, on=subject_col, how="left")

    # Order columns predictably.
    front = [subject_col, nucleus_col, "L", "R", "ipsi", "contra", "soz_side",
             "side_ai", "soz_ai", "log_ai", "value_kind"]
    extras = [c for c in wide.columns if c not in front]
    return wide[front + extras].reset_index(drop=True)
