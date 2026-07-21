"""Run diagnostics on a cohort_long.csv: residuals (optional) and permutation tests.

Example:
    python scripts/run_diagnostics.py --cohort out/cohort_long.csv --out out/diagnostics --effect "group"
"""
from __future__ import annotations

import argparse
from pathlib import Path
import json
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nodestrength.diagnostics import permutation_test_mixed_anova
from nodestrength.normative import load_model


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cohort", type=Path, required=True, help="cohort_long.csv (long-form)")
    p.add_argument("--out", type=Path, required=True, help="output directory for diagnostics")
    p.add_argument("--subject-col", default="subject")
    p.add_argument("--within", nargs="+", default=["nucleus", "side"])
    p.add_argument("--between", nargs="+", default=["group"])
    p.add_argument("--value", default="strength")
    p.add_argument("--effect", required=True, help="Effect name to test (as in mixed_anova output, e.g. 'group' or 'group x nucleus')")
    p.add_argument("--permutations", type=int, default=1000)
    p.add_argument("--model", type=Path, default=None, help="Optional NormativeModel pickle to compute residuals (not required)")
    args = p.parse_args(argv)

    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.cohort)

    res = permutation_test_mixed_anova(
        long=df,
        subject=args.subject_col,
        within_factors=args.within,
        between_factors=args.between,
        value=args.value,
        effect_name=args.effect,
        n_permutations=args.permutations,
    )

    # Save summary
    (out / "permutation_result.json").write_text(json.dumps({
        'effect': res['effect'], 'observed': float(res['observed']), 'p_empirical': float(res['p_empirical'])
    }, indent=2))

    # Save permutation values as CSV
    import numpy as np
    pd.DataFrame({'perm_value': np.asarray(res['perm_values']).tolist()}).to_csv(out / 'perm_values.csv', index=False)

    # If model provided, compute residuals per-subject and save
    if args.model:
        try:
            model = load_model(args.model)
            z = model.z_score(df)
            df[f"{args.value}_z"] = z.values
            df.to_csv(out / "cohort_with_z.csv", index=False)
        except Exception as e:
            (out / "model_error.txt").write_text(str(e))

    print(f"Wrote diagnostics to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
