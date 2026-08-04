"""Compute per-subject strength/volume records from existing connectomes.

Processes a directory of `sub-*` folders containing `connectome.csv` and
`node_lookup.tsv`. Optionally reads a merged label NIfTI per subject to
compute per-nucleus volumes. Can load a saved normative model (pickle) to
produce z-scores for `strength` and/or `volume_mm3`.

Writes per-subject CSVs under `--out/per_subject/` and a concatenated
`cohort_long.csv` in `--out` plus a `manifest.json` describing the run.

Usage:
    python scripts/score_connectomes.py --root /path/to/derivatives --out /path/to/out \
        [--covariates covariates.csv] [--model model.pkl]
"""
from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path
import sys
from typing import List, Dict, Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nodestrength.connectome import (
    load_connectome,
    load_node_lookup,
    per_subject_record,
    uses_bctpy,
)
from nodestrength.dk_inputs import find_connectome_csv
import pandas as pd


def find_subject_dirs(root: Path) -> List[Path]:
    return sorted([p for p in root.iterdir() if p.is_dir() and p.name.startswith("sub-")])


def load_covariates(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "subject" not in df.columns:
        raise ValueError("Covariates CSV must contain a 'subject' column matching sub-IDs (sub-XXX).")
    return df


def try_load_model(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {path}")
    with path.open("rb") as fh:
        return pickle.load(fh)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True, type=Path,
                   help="Root directory containing sub-*/connectome.csv and node_lookup.tsv")
    p.add_argument("--out", required=True, type=Path, help="Output directory")
    p.add_argument("--covariates", type=Path, default=None,
                   help="Optional CSV of covariates with column 'subject' (sub-XXX)")
    p.add_argument("--model", type=Path, default=None,
                   help="Optional pickle file with a fitted NormativeModel to z-score subjects")
    p.add_argument("--labels-name", type=str, default="labels_combined.nii.gz",
                   help="Relative filename in each subject dir for merged label image")
    args = p.parse_args(argv)

    root = args.root
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    per_subject_dir = out / "per_subject"
    per_subject_dir.mkdir(exist_ok=True)

    cov_df = None
    if args.covariates:
        cov_df = load_covariates(args.covariates)

    model = None
    if args.model:
        model = try_load_model(args.model)

    subjects = find_subject_dirs(root)
    if not subjects:
        print(f"No subjects found under {root}")
        return 2

    frames = []
    warnings: List[str] = []

    for s in subjects:
        sid = s.name
        conn_path = find_connectome_csv(s)
        if conn_path is None:
            gz = s / "connectome.csv.gz"
            conn_path = gz if gz.exists() else None
        if conn_path is None:
            warnings.append(f"{sid}: connectome CSV not found (dkt_connectome.csv, dk_connectome.csv, or connectome.csv)")
            continue

        lookup_path = s / "node_lookup.tsv"
        if not lookup_path.exists():
            warnings.append(f"{sid}: node_lookup.tsv not found")
            continue

        try:
            C = load_connectome(conn_path)
            lookup = load_node_lookup(lookup_path)
        except Exception as exc:
            warnings.append(f"{sid}: failed to load connectome/lookup: {exc}")
            continue

        label_p = s / args.labels_name
        label_arg = label_p if label_p.exists() else None

        rec = per_subject_record(sid, C, lookup, label_image_path=label_arg)

        # Merge covariates if provided
        if cov_df is not None:
            row = cov_df[cov_df["subject"] == sid]
            if len(row) == 0:
                warnings.append(f"{sid}: covariates row not found in {args.covariates}")
            else:
                # broadcast all covariate columns (except 'subject') onto rec
                cov_row = row.iloc[0].drop(labels=["subject"])
                for col, val in cov_row.items():
                    rec[col] = val

        # z-score if model provided
        if model is not None:
            try:
                z = model.z_score(rec)
                rec[f"{model.target}_z"] = z.values
            except Exception as exc:
                warnings.append(f"{sid}: failed to z-score {model.target}: {exc}")

        out_path = per_subject_dir / f"{sid}_per_subject_record.csv"
        rec.to_csv(out_path, index=False)
        frames.append(rec)

    if frames:
        cohort = pd.concat(frames, ignore_index=True)
        cohort.to_csv(out / "cohort_long.csv", index=False)

    manifest: Dict[str, Any] = {
        "n_subjects": len(frames),
        "bct_backend": uses_bctpy(),
        "warnings": warnings,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Wrote per-subject records for {len(frames)} subjects to {per_subject_dir}")
    if warnings:
        print("Warnings:\n" + "\n".join(warnings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
