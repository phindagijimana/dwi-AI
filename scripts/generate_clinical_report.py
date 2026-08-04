#!/usr/bin/env python3
"""Generate a minimal clinical HTML report for one subject."""

from __future__ import annotations

import argparse
from pathlib import Path

from nodestrength.clinical_report import generate_clinical_report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results", required=True, type=Path,
                   help="node_strength_results directory")
    p.add_argument("--subject", required=True,
                   help="Subject ID, e.g. 001 or sub-001")
    p.add_argument("--connectome", type=Path, default=None,
                   help="Optional dkt_connectome.csv for seed/heatmap figures")
    p.add_argument("--subject-dir", type=Path, default=None,
                   help="Optional connectome subject folder (aparc+aseg for FS volumes)")
    p.add_argument("--participants", type=Path, default=None,
                   help="participants.tsv for SOZ side and normative z-scores")
    p.add_argument("--normative-model", type=Path, default=None,
                   help="Pre-fitted normative_strength_model.pkl")
    p.add_argument("--control-group", default="control",
                   help="Control group label in participants.tsv")
    args = p.parse_args(argv)

    out = generate_clinical_report(
        args.results,
        args.subject,
        connectome_csv=args.connectome,
        subject_dir=args.subject_dir,
        participants_path=args.participants,
        normative_model_path=args.normative_model,
        control_group=args.control_group,
    )
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
