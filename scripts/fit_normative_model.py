"""Fit and save a NormativeModel from controls long-form CSV.

Example:
    python scripts/fit_normative_model.py --controls controls_long.csv \
        --target strength --out strength_model.pkl
"""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nodestrength.normative import fit_strength_model, fit_volume_model, save_model


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--controls", required=True, type=Path, help="CSV of controls long-form (subject,nucleus,side,strength,age,sex,mean_brain_strength,motion,...)")
    p.add_argument("--target", choices=("strength", "volume"), default="strength")
    p.add_argument("--out", required=True, type=Path, help="Path to write model pickle")
    args = p.parse_args(argv)

    controls = pd.read_csv(args.controls)

    if args.target == "strength":
        model = fit_strength_model(controls)
    else:
        model = fit_volume_model(controls)

    save_model(args.out, model)
    print(f"Saved {args.target} normative model to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
