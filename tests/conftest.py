"""Shared fixtures: tiny synthetic connectome, controls, and patient cohorts."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nodestrength.atlases import ANALYZED_NUCLEI, LEFT_LABELS, RIGHT_LABELS, all_rois


@pytest.fixture
def tiny_lookup() -> pd.DataFrame:
    """Lookup with 4 cortical ROIs + 16 thalamic ROIs (8 nuclei × 2 sides)."""
    rows = []
    idx = 1
    for cortical in ("ctx-lh-PG1", "ctx-lh-PG2", "ctx-rh-PG1", "ctx-rh-PG2"):
        rows.append({"index": idx, "name": cortical})
        idx += 1
    for roi in all_rois():
        rows.append({"index": idx, "name": roi.key})
        idx += 1
    return pd.DataFrame(rows)


@pytest.fixture
def tiny_connectome(tiny_lookup: pd.DataFrame) -> np.ndarray:
    """Symmetric connectome with engineered edge weights."""
    n = len(tiny_lookup)
    rng = np.random.default_rng(0)
    M = rng.uniform(0.1, 1.0, size=(n, n))
    M = (M + M.T) / 2.0
    np.fill_diagonal(M, 0.0)
    return M


def _make_subject_long(subject_id: str, base_strength: float, base_volume: float,
                       age: float, sex: str, motion: float, icv: float,
                       rng: np.random.Generator,
                       group: str, soz: str = "TLE-HS",
                       seizure_free: str = "yes",
                       nucleus_effects: dict | None = None) -> pd.DataFrame:
    rows = []
    for nucleus in ANALYZED_NUCLEI:
        for side in ("L", "R"):
            offset = (nucleus_effects or {}).get(nucleus, 0.0)
            laterality_offset = 0.0
            if group == "patient" and soz == "TLE-HS" and nucleus == "AV":
                # paper finding: ipsilateral AV reduction in TLE-HS
                if side == "L":
                    laterality_offset = -1.2
            s = base_strength + offset + laterality_offset + rng.normal(0, 0.3)
            v = base_volume + 50.0 * offset + rng.normal(0, 50.0)
            rows.append({
                "subject": subject_id,
                "nucleus": nucleus,
                "side": side,
                "strength": s,
                "volume_mm3": v,
                "mean_brain_strength": 1.0 + rng.normal(0, 0.05),
                "age": age,
                "sex": sex,
                "motion": motion,
                "icv": icv,
                "group": group,
                "soz": soz,
                "seizure_free": seizure_free,
            })
    return pd.DataFrame(rows)


@pytest.fixture
def synthetic_cohort() -> pd.DataFrame:
    """Long-form cohort: 30 controls + 30 patients (15 TLE-HS, 15 frontal).

    Engineered so that:
      * patients have overall higher CM, MDPf, PUL strength than controls (paper Fig 3A);
      * TLE-HS patients have lower AV strength, especially ipsilaterally (Fig 3B, 4A);
      * seizure-free patients have an ipsi-low / contra-high asymmetry (Fig 4C).
    """
    rng = np.random.default_rng(42)
    frames = []

    for i in range(30):
        frames.append(_make_subject_long(
            subject_id=f"C{i:03d}",
            base_strength=10.0,
            base_volume=900.0,
            age=10 + rng.uniform(0, 8),
            sex=rng.choice(["F", "M"]),
            motion=rng.uniform(0.5, 1.5),
            icv=1.4e6 + rng.normal(0, 5e4),
            rng=rng,
            group="control",
            soz="control",
            seizure_free="control",
            nucleus_effects={"AV": 0.0, "CM": 0.0, "MDPf": 0.0, "PUL": 0.0},
        ))

    for i in range(15):
        frames.append(_make_subject_long(
            subject_id=f"P-HS-{i:03d}",
            base_strength=10.0,
            base_volume=900.0,
            age=12 + rng.uniform(0, 6),
            sex=rng.choice(["F", "M"]),
            motion=rng.uniform(0.4, 1.4),
            icv=1.4e6 + rng.normal(0, 5e4),
            rng=rng,
            group="patient",
            soz="TLE-HS",
            seizure_free=rng.choice(["yes", "no"]),
            nucleus_effects={"AV": -0.4, "CM": 1.2, "MDPf": 1.0, "PUL": 1.1},
        ))

    for i in range(15):
        frames.append(_make_subject_long(
            subject_id=f"P-FR-{i:03d}",
            base_strength=10.0,
            base_volume=900.0,
            age=10 + rng.uniform(0, 6),
            sex=rng.choice(["F", "M"]),
            motion=rng.uniform(0.4, 1.4),
            icv=1.4e6 + rng.normal(0, 5e4),
            rng=rng,
            group="patient",
            soz="frontal",
            seizure_free=rng.choice(["yes", "no"]),
            nucleus_effects={"AV": 0.2, "CM": 1.3, "MDPf": 1.0, "PUL": 1.1},
        ))

    return pd.concat(frames, ignore_index=True)
