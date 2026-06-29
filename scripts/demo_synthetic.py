"""End-to-end demo on a simulated cohort.

Generates a cohort that *mimics* the engineered effects in Piper et al. 2026
(higher overall thalamic strength in patients; ipsilateral AV reduction in
TLE-HS; ipsi-low/contra-high asymmetry in seizure-free patients), then runs:

* Normative GLM z-scoring against controls.
* Mixed-design ANOVA (Pillai's trace + partial η²) for the three
  paper analyses:
    1. controls vs patients (Section 3.3, Figure 3A);
    2. patients by SOZ (Figure 3B, 4A);
    3. patients by post-op seizure freedom (Figure 4C).

This is *not* a reproduction of the paper's empirical result — the patient
cohort is simulated. It demonstrates that the implementation runs end-to-end
and produces a results table in the expected shape.

Run with:
    python scripts/demo_synthetic.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Make the package importable when running the script directly from a clone.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nodestrength.normative import fit_strength_model, fit_volume_model
from nodestrength.stats import mixed_anova


# ---------------------------------------------------------------------------
# Cohort simulator (mirrors the test fixture but stand-alone).
# ---------------------------------------------------------------------------

NUCLEI = ("AV", "CM", "MDPf", "PUL")


def _simulate_subject(sid, group, soz, seizure_free, rng,
                      nucleus_effects, ipsi_av_reduction=0.0,
                      ipsi_reduction_global=0.0, contra_increase_global=0.0):
    rows = []
    for nucleus in NUCLEI:
        for side in ("L", "R"):
            offset = nucleus_effects.get(nucleus, 0.0)
            if nucleus == "AV" and side == "L" and group == "patient":
                offset += ipsi_av_reduction
            if side == "L":
                offset += ipsi_reduction_global
            else:
                offset += contra_increase_global
            s = 10.0 + offset + rng.normal(0, 0.3)
            v = 900.0 + 50.0 * offset + rng.normal(0, 50)
            rows.append({
                "subject": sid, "nucleus": nucleus, "side": side,
                "strength": s, "volume_mm3": v,
                "mean_brain_strength": 1.0 + rng.normal(0, 0.05),
                "age": float(rng.uniform(8, 18)),
                "sex": rng.choice(["F", "M"]),
                "motion": float(rng.uniform(0.4, 1.5)),
                "icv": float(1.4e6 + rng.normal(0, 5e4)),
                "group": group, "soz": soz, "seizure_free": seizure_free,
            })
    return rows


def simulate_cohort(n_controls=63, n_hs=16, n_tle_other=29, n_frontal=29,
                    seed=2026) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []

    for i in range(n_controls):
        rows += _simulate_subject(f"C{i:03d}", "control", "control", "control",
                                  rng, {n: 0.0 for n in NUCLEI})

    for i in range(n_hs):
        sf = "yes" if rng.random() < 0.55 else "no"
        rows += _simulate_subject(
            f"HS{i:03d}", "patient", "TLE-HS", sf, rng,
            nucleus_effects={"AV": -0.5, "CM": 1.0, "MDPf": 0.9, "PUL": 1.0},
            ipsi_av_reduction=-0.8,
            ipsi_reduction_global=-0.3 if sf == "yes" else 0.0,
            contra_increase_global=+0.3 if sf == "yes" else 0.0,
        )

    for i in range(n_tle_other):
        sf = "yes" if rng.random() < 0.60 else "no"
        rows += _simulate_subject(
            f"TO{i:03d}", "patient", "TLE-other", sf, rng,
            nucleus_effects={"AV": 0.1, "CM": 1.1, "MDPf": 0.9, "PUL": 1.0},
            ipsi_reduction_global=-0.2 if sf == "yes" else 0.0,
            contra_increase_global=+0.2 if sf == "yes" else 0.0,
        )

    for i in range(n_frontal):
        sf = "yes" if rng.random() < 0.55 else "no"
        rows += _simulate_subject(
            f"FR{i:03d}", "patient", "frontal", sf, rng,
            nucleus_effects={"AV": 0.2, "CM": 1.2, "MDPf": 1.0, "PUL": 0.9},
            ipsi_reduction_global=-0.2 if sf == "yes" else 0.0,
            contra_increase_global=+0.2 if sf == "yes" else 0.0,
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Demo entry point.
# ---------------------------------------------------------------------------

def _print(title, df, cols=None):
    cols = cols or ["effect", "value", "f", "df_num", "df_den", "p_value", "partial_eta_sq"]
    print("\n=== " + title + " ===")
    print(df[cols].to_string(index=False,
                              formatters={
                                  "value": "{:.3f}".format,
                                  "f": "{:.2f}".format,
                                  "df_num": "{:.1f}".format,
                                  "df_den": "{:.1f}".format,
                                  "p_value": "{:.4g}".format,
                                  "partial_eta_sq": "{:.3f}".format,
                              }))


def main() -> int:
    cohort = simulate_cohort()
    n_subjects = cohort["subject"].nunique()
    per_subject = cohort.drop_duplicates("subject")
    n_controls = (per_subject["group"] == "control").sum()
    n_patients = (per_subject["group"] == "patient").sum()
    by_soz = per_subject[per_subject["group"] == "patient"]["soz"].value_counts().to_dict()
    print(f"Simulated cohort: {n_subjects} subjects "
          f"({n_controls} controls, {n_patients} patients: {by_soz}).")

    # Normative model on controls.
    controls = cohort[cohort["group"] == "control"]
    patients = cohort[cohort["group"] == "patient"].copy()

    strength_model = fit_strength_model(controls)
    volume_model = fit_volume_model(controls)
    patients["strength_z"] = strength_model.z_score(patients).values
    patients["volume_z"] = volume_model.z_score(patients).values

    print("\nMean patient strength z by (SOZ, nucleus, side):")
    print(patients.groupby(["soz", "nucleus", "side"])["strength_z"]
                  .mean().round(2).to_string())

    # Paper Section 3.3 -- controls vs patients on raw strength.
    res_cc = mixed_anova(
        long=cohort, subject="subject",
        within_factors=("nucleus", "side"),
        between_factors=("group",), value="strength")
    _print("Controls vs Patients (strength)", res_cc)

    res_cc_vol = mixed_anova(
        long=cohort, subject="subject",
        within_factors=("nucleus", "side"),
        between_factors=("group",), value="volume_mm3")
    _print("Controls vs Patients (volume)", res_cc_vol)

    # Paper Section 3.3 -- patients only, by SOZ.
    res_soz = mixed_anova(
        long=patients, subject="subject",
        within_factors=("nucleus", "side"),
        between_factors=("soz",), value="strength")
    _print("Patients by SOZ (strength)", res_soz)

    # Paper Section 3.3 -- patients by seizure freedom.
    res_sf = mixed_anova(
        long=patients, subject="subject",
        within_factors=("nucleus", "side"),
        between_factors=("seizure_free",), value="strength")
    _print("Patients by seizure freedom (strength)", res_sf)

    res_sf_vol = mixed_anova(
        long=patients, subject="subject",
        within_factors=("nucleus", "side"),
        between_factors=("seizure_free",), value="volume_mm3")
    _print("Patients by seizure freedom (volume)", res_sf_vol)

    # Persist artefacts for inspection.
    out_dir = ROOT / "scripts" / "outputs"
    out_dir.mkdir(exist_ok=True)
    cohort.to_csv(out_dir / "synthetic_cohort.csv", index=False)
    patients.to_csv(out_dir / "synthetic_patients_zscored.csv", index=False)
    res_cc.to_csv(out_dir / "glm_controls_vs_patients_strength.csv", index=False)
    res_cc_vol.to_csv(out_dir / "glm_controls_vs_patients_volume.csv", index=False)
    res_soz.to_csv(out_dir / "glm_soz_strength.csv", index=False)
    res_sf.to_csv(out_dir / "glm_sf_strength.csv", index=False)
    res_sf_vol.to_csv(out_dir / "glm_sf_volume.csv", index=False)
    print(f"\nArtefacts written to {out_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
