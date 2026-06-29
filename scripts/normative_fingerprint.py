"""Reproduce the paper's Figure 2 / Table S1 on a healthy-control cohort.

For each analyzed nucleus (AV, CM, MDPf, PUL), rank the strongest cortical
and subcortical connections (mean SIFT2 weight across controls) and emit:

* ``fingerprint_long.csv`` — every (nucleus, side, target_roi) row with the
  cohort-mean weight, 10th and 90th percentiles, and rank within the nucleus.
* ``fingerprint_topN.csv`` — top-N targets per nucleus, the form most directly
  comparable to the paper's Table S1.

Inputs
------
``--connectomes`` either a directory full of subject connectome CSVs, or a
list of CSV paths. The script expects each subject also has a node-lookup at
``<connectome_dir>/node_lookup.tsv`` (the standard layout written by the
pipeline). A single ``--lookup`` can be passed instead if all subjects share
one parcellation.

Usage
-----
    python scripts/normative_fingerprint.py \
        --derivatives /data/openneuro/ds003969/derivatives/nodestrength \
        --out /data/openneuro/ds003969/derivatives/fingerprint \
        [--top 30]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nodestrength.atlases import ANALYZED_NUCLEI, all_rois
from nodestrength.connectome import (
    StrengthConfig,
    _name_to_row,        # internal helper, fine to reuse here
    _roi_row,
    load_connectome,
    load_node_lookup,
)


def _adjusted_edges_for_nucleus(
    connectome: np.ndarray, node_lookup: pd.DataFrame, roi_row: int,
    drop_thalamic_rows: List[int]
) -> pd.Series:
    """Return one row of the connectome with self + inter-thalamic edges zeroed."""
    row = connectome[roi_row].copy()
    row[roi_row] = 0.0
    for j in drop_thalamic_rows:
        row[j] = 0.0
    target_names = node_lookup.sort_values("index")["name"].to_list()
    return pd.Series(row, index=target_names, name="weight")


def _gather_fingerprint(
    connectome_paths: List[Path],
    lookup: pd.DataFrame,
    config: StrengthConfig,
) -> pd.DataFrame:
    """Stack per-subject edge weights into a long-form table."""
    rois = [r for r in all_rois() if r.name in ANALYZED_NUCLEI]
    mapping = _name_to_row(lookup)
    roi_rows = {roi.key: _roi_row(roi, mapping) for roi in rois}
    inter_rows = list(roi_rows.values()) if config.exclude_inter_thalamic else []

    rows = []
    for cpath in connectome_paths:
        C = load_connectome(cpath)
        sid = cpath.parent.name  # "sub-HC001" or similar
        for roi in rois:
            row = _adjusted_edges_for_nucleus(C, lookup, roi_rows[roi.key], inter_rows)
            for target, weight in row.items():
                if weight <= 0:
                    continue
                rows.append({
                    "subject": sid, "nucleus": roi.name, "side": roi.side,
                    "target": target, "weight": float(weight),
                })
    return pd.DataFrame(rows)


def _aggregate(fingerprint_long: pd.DataFrame) -> pd.DataFrame:
    grouped = fingerprint_long.groupby(["nucleus", "side", "target"])["weight"]
    agg = grouped.agg(
        n_subjects="count",
        mean="mean",
        p10=lambda s: np.percentile(s, 10),
        p50=lambda s: np.percentile(s, 50),
        p90=lambda s: np.percentile(s, 90),
    ).reset_index()
    agg["rank"] = (agg.sort_values(["nucleus", "side", "mean"], ascending=[True, True, False])
                      .groupby(["nucleus", "side"]).cumcount() + 1)
    return agg.sort_values(["nucleus", "side", "rank"]).reset_index(drop=True)


def _top_n(agg: pd.DataFrame, n: int) -> pd.DataFrame:
    return agg[agg["rank"] <= n].reset_index(drop=True)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--derivatives", type=Path, default=None,
                   help="Walk this tree for connectome.csv + node_lookup.tsv.")
    p.add_argument("--connectomes", nargs="*", type=Path, default=None,
                   help="Alternative: explicit list of connectome CSV paths.")
    p.add_argument("--lookup", type=Path, default=None,
                   help="Shared node-lookup TSV (overrides per-subject lookups).")
    p.add_argument("--out", required=True, type=Path,
                   help="Output directory.")
    p.add_argument("--top", type=int, default=30,
                   help="Top N targets per nucleus to emit (default 30).")
    args = p.parse_args(argv)

    if args.derivatives:
        connectome_paths = sorted(args.derivatives.rglob("connectome.csv"))
    elif args.connectomes:
        connectome_paths = args.connectomes
    else:
        print("Provide either --derivatives or --connectomes.", file=sys.stderr)
        return 2

    if not connectome_paths:
        print("No connectomes found.", file=sys.stderr)
        return 2
    print(f"Processing {len(connectome_paths)} connectomes.")

    if args.lookup:
        shared_lookup = load_node_lookup(args.lookup)
    else:
        shared_lookup = None

    config = StrengthConfig(exclude_self=True, exclude_inter_thalamic=True)

    if shared_lookup is not None:
        long = _gather_fingerprint(connectome_paths, shared_lookup, config)
    else:
        # Per-subject lookup -- assume <connectome>/node_lookup.tsv next to each.
        frames = []
        for cpath in connectome_paths:
            lkup = load_node_lookup(cpath.parent / "node_lookup.tsv")
            frames.append(_gather_fingerprint([cpath], lkup, config))
        long = pd.concat(frames, ignore_index=True)

    agg = _aggregate(long)
    top = _top_n(agg, args.top)

    args.out.mkdir(parents=True, exist_ok=True)
    long.to_csv(args.out / "fingerprint_long.csv", index=False)
    agg.to_csv(args.out / "fingerprint_all.csv", index=False)
    top.to_csv(args.out / "fingerprint_topN.csv", index=False)

    # Pretty-print the top-10 per nucleus for stdout.
    print()
    for (nucleus, side), block in top[top["rank"] <= 10].groupby(["nucleus", "side"]):
        print(f"=== {side}.{nucleus} (top 10) ===")
        for _, r in block.iterrows():
            print(f"  {r['rank']:>2d}.  {r['target']:<40s}  "
                  f"mean={r['mean']:.2f}  p10={r['p10']:.2f}  p90={r['p90']:.2f}")
        print()
    print(f"Wrote {args.out}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
