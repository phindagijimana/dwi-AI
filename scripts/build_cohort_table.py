"""Build the long-form cohort table from per-subject pipeline artefacts.

After ``run_micamics_cohort.py`` finishes, each subject directory contains:

    sub-HC###/[ses-01/]
        connectome.csv
        node_lookup.tsv
        labels_combined.nii.gz

This script walks the derivatives tree, calls
``nodestrength.connectome.per_subject_record`` for each subject, joins
``participants.tsv`` (age, sex) and motion (if a ``motion.tsv`` summary was
written by the dMRI preprocessing step), and emits one long-form CSV that
``nodestrength analyze`` can consume directly.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from nodestrength.bids import build_cohort_long
from nodestrength.connectome import (
    StrengthConfig,
    load_connectome,
    load_node_lookup,
    per_subject_record,
)


def _walk_subjects(derivatives: Path) -> List[Path]:
    """Yield each subject's processed directory containing ``connectome.csv``."""
    return sorted(p.parent for p in derivatives.rglob("connectome.csv"))


def _subject_id_from_path(path: Path, derivatives: Path) -> str:
    """Extract ``HC###`` from a path like ``.../sub-HC001/ses-01/``."""
    rel = path.relative_to(derivatives)
    for part in rel.parts:
        if part.startswith("sub-"):
            return part[len("sub-"):]
    return rel.parts[0]


def _per_subject_csv(subject_dir: Path, derivatives: Path) -> pd.DataFrame:
    connectome = load_connectome(subject_dir / "connectome.csv")
    lookup = load_node_lookup(subject_dir / "node_lookup.tsv")
    labels = subject_dir / "labels_combined.nii.gz"
    sid = _subject_id_from_path(subject_dir, derivatives)
    df = per_subject_record(
        subject_id=sid,
        connectome=connectome,
        node_lookup=lookup,
        label_image_path=labels if labels.exists() else None,
        config=StrengthConfig(exclude_self=True, exclude_inter_thalamic=True),
    )
    # Optional motion summary written by the preprocessing step.
    motion_tsv = subject_dir / "motion.tsv"
    if motion_tsv.exists():
        motion = pd.read_csv(motion_tsv, sep="\t").iloc[0].to_dict()
        df["motion"] = motion.get("total_displacement",
                                   motion.get("mean_fd", float("nan")))
    return df


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--derivatives", required=True, type=Path,
                   help="Root of the nodestrength derivatives tree.")
    p.add_argument("--participants", type=Path, default=None,
                   help="BIDS participants.tsv (provides age, sex).")
    p.add_argument("--group-column", default=None,
                   help="Column in participants.tsv to use as the case/control grouping.")
    p.add_argument("--out", required=True, type=Path,
                   help="Output long-form cohort CSV.")
    args = p.parse_args(argv)

    subject_dirs = _walk_subjects(args.derivatives)
    if not subject_dirs:
        print(f"No connectome.csv files found under {args.derivatives}.",
              file=sys.stderr)
        return 2
    print(f"Aggregating {len(subject_dirs)} subjects.")

    per_subject = [_per_subject_csv(d, args.derivatives) for d in subject_dirs]

    # write tmp CSVs so build_cohort_long can join participants.tsv consistently.
    tmp = args.out.parent / "_per_subject"
    tmp.mkdir(parents=True, exist_ok=True)
    paths = []
    for df in per_subject:
        path = tmp / f"{df['subject'].iloc[0]}.csv"
        df.to_csv(path, index=False)
        paths.append(path)

    cohort = build_cohort_long(paths, participants_tsv=args.participants)

    if args.group_column:
        if args.group_column in cohort.columns:
            cohort = cohort.rename(columns={args.group_column: "group"})
        else:
            print(f"Warning: --group-column {args.group_column} not found in "
                  f"participants.tsv; leaving cohort ungrouped.", file=sys.stderr)

    # Default values for missing covariates so analyses don't blow up.
    if "motion" not in cohort.columns:
        cohort["motion"] = 0.0
    if "icv" not in cohort.columns:
        cohort["icv"] = float("nan")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    cohort.to_csv(args.out, index=False)
    print(f"Wrote {args.out} ({len(cohort)} rows, "
          f"{cohort['subject'].nunique()} subjects).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
