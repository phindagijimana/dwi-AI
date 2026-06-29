"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from . import asymmetry as asym
from . import connectome as conn
from . import ideas as ideas_mod
from . import inspect as inspect_mod
from . import normative as norm
from . import pipeline as pipe
from . import stats as st


def _cmd_run_subject(args: argparse.Namespace) -> int:
    artefacts = pipe.run_subject(
        subject_id=args.subject_id,
        t1=Path(args.t1),
        dwi=Path(args.dwi),
        bvec=Path(args.bvec),
        bval=Path(args.bval),
        rpe_b0=Path(args.rpe_b0),
        subjects_dir=Path(args.subjects_dir),
        out_dir=Path(args.out_dir),
        dry_run=args.dry_run,
    )
    print(json.dumps(artefacts, indent=2))
    return 0


def _cmd_compute_strength(args: argparse.Namespace) -> int:
    C = conn.load_connectome(args.connectome)
    lut = conn.load_node_lookup(args.lookup)
    record = conn.per_subject_record(
        subject_id=args.subject_id,
        connectome=C,
        node_lookup=lut,
        label_image_path=args.labels,
    )
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    record.to_csv(out_path, index=False)
    print(f"wrote {out_path} ({len(record)} rows)")
    return 0


def _cmd_fit_normative(args: argparse.Namespace) -> int:
    import pickle
    controls = pd.read_csv(args.controls)
    strength_model = norm.fit_strength_model(controls)
    volume_model = norm.fit_volume_model(controls)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as fh:
        pickle.dump({"strength": strength_model, "volume": volume_model}, fh)
    print(f"wrote {out_path}")
    return 0


def _cmd_ingest_ideas(args: argparse.Namespace) -> int:
    """List IDEAS subjects discovered in a raw BIDS root."""
    subs = ideas_mod.ingest_raw_bids(
        bids_root=Path(args.bids),
        participants_tsv=Path(args.participants) if args.participants else None,
        include=args.include,
    )
    out = [s.to_dict() for s in subs]
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(out).to_csv(out_path, index=False)
    print(f"Discovered {len(subs)} subjects; manifest written to {out_path}")
    by_proto = pd.Series([s.protocol for s in subs]).value_counts(dropna=False).to_dict()
    print("By acquisition protocol:", by_proto)
    return 0


def _cmd_ingest_preprocessed(args: argparse.Namespace) -> int:
    """Build a long-form cohort directly from the IDEAS II pre-processed archive."""
    cohort = ideas_mod.ingest_preprocessed(
        archive_root=Path(args.archive),
        participants_tsv=Path(args.participants) if args.participants else None,
        include=args.include,
    )
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cohort.to_csv(out_path, index=False)
    print(f"Wrote {out_path}  ({len(cohort)} rows, "
          f"{cohort['subject'].nunique()} subjects)")
    if "group" in cohort.columns:
        per_subject = cohort.drop_duplicates("subject")
        print("By group:", per_subject["group"].value_counts(dropna=False).to_dict())
    return 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    """Readiness probe — point at an IDEAS download and get a diagnostic."""
    report = inspect_mod.inspect_path(Path(args.path))
    print(inspect_mod.summarize(report))
    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(inspect_mod.report_to_json(report))
        print(f"\nFull JSON: {out}")
    return 0 if report.verdict.startswith("READY") else 1


def _cmd_asymmetry(args: argparse.Namespace) -> int:
    """Collapse a long-form cohort into a per-(subject, nucleus) AI table."""
    cohort = pd.read_csv(args.cohort)
    ai = asym.cohort_ai(
        cohort_long=cohort,
        value=args.value,
        soz_side_col=args.soz_side_col,
    )
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ai.to_csv(out_path, index=False)
    print(f"Wrote {out_path}  ({len(ai)} rows, "
          f"{ai['subject'].nunique()} subjects).")
    print("Summary of side_ai by nucleus:")
    print(ai.groupby("nucleus")["side_ai"]
            .describe()[["mean", "std", "min", "max"]].round(3).to_string())
    return 0


def _cmd_analyze(args: argparse.Namespace) -> int:
    cohort = pd.read_csv(args.cohort)
    results = st.mixed_anova(
        long=cohort,
        subject=args.subject_col,
        within_factors=args.within,
        between_factors=args.between,
        value=args.value,
    )
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(out_path, index=False)
    print(results.to_string(index=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="nodestrength",
                                description="Piper et al. 2026 thalamocortical-connectivity reimplementation.")
    sub = p.add_subparsers(dest="cmd", required=True)

    rs = sub.add_parser("run-subject",
                        help="Run the full FreeSurfer/THOMAS/MRtrix3 pipeline for one subject.")
    rs.add_argument("subject_id")
    rs.add_argument("--t1", required=True)
    rs.add_argument("--dwi", required=True)
    rs.add_argument("--bvec", required=True)
    rs.add_argument("--bval", required=True)
    rs.add_argument("--rpe-b0", required=True)
    rs.add_argument("--subjects-dir", required=True)
    rs.add_argument("--out-dir", required=True)
    rs.add_argument("--dry-run", action="store_true")
    rs.set_defaults(func=_cmd_run_subject)

    cs = sub.add_parser("compute-strength",
                        help="Compute per-nucleus strength + volume from a connectome.")
    cs.add_argument("--subject-id", required=True)
    cs.add_argument("--connectome", required=True, help="MRtrix3 connectome CSV")
    cs.add_argument("--lookup", required=True, help="Node-lookup table")
    cs.add_argument("--labels", required=True, help="Merged Lausanne+THOMAS label NIfTI")
    cs.add_argument("--out", required=True, help="Output CSV path")
    cs.set_defaults(func=_cmd_compute_strength)

    fn = sub.add_parser("fit-normative",
                        help="Fit per-(nucleus, side) GLM on a control cohort and save it.")
    fn.add_argument("--controls", required=True, help="Long-form controls cohort CSV")
    fn.add_argument("--out", required=True, help="Pickle output path")
    fn.set_defaults(func=_cmd_fit_normative)

    an = sub.add_parser("analyze",
                        help="Run mixed-design GLM (Pillai's trace + partial eta-squared).")
    an.add_argument("--cohort", required=True)
    an.add_argument("--subject-col", default="subject")
    an.add_argument("--within", nargs="+", required=True)
    an.add_argument("--between", nargs="+", required=True)
    an.add_argument("--value", required=True)
    an.add_argument("--out", required=True)
    an.set_defaults(func=_cmd_analyze)

    ii = sub.add_parser("ingest-ideas",
                        help="Walk an IDEAS raw BIDS root and write a subject manifest CSV.")
    ii.add_argument("--bids", required=True)
    ii.add_argument("--participants", default=None)
    ii.add_argument("--include", nargs="*", default=None)
    ii.add_argument("--out", required=True)
    ii.set_defaults(func=_cmd_ingest_ideas)

    ip = sub.add_parser("ingest-preprocessed",
                        help="Build a long-form cohort directly from the IDEAS II "
                             "pre-processed dMRI archive (skips recon-all/THOMAS/MRtrix3).")
    ip.add_argument("--archive", required=True)
    ip.add_argument("--participants", default=None)
    ip.add_argument("--include", nargs="*", default=None)
    ip.add_argument("--out", required=True)
    ip.set_defaults(func=_cmd_ingest_preprocessed)

    insp = sub.add_parser("inspect",
                          help="Readiness probe — point at an IDEAS download "
                               "(raw BIDS, pre-processed archive, or both).")
    insp.add_argument("path")
    insp.add_argument("--json", default=None,
                      help="Write the full diagnostic as JSON to this path.")
    insp.set_defaults(func=_cmd_inspect)

    ai = sub.add_parser("asymmetry",
                        help="Collapse strength/volume into per-subject asymmetry "
                             "indices (side / SOZ / log).")
    ai.add_argument("--cohort", required=True, help="Long-form cohort CSV.")
    ai.add_argument("--value", default="strength",
                    help="Column to compute AI on (default: strength).")
    ai.add_argument("--soz-side-col", default="soz_side",
                    help="Column carrying the SOZ side (L/R) per patient.")
    ai.add_argument("--out", required=True)
    ai.set_defaults(func=_cmd_asymmetry)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
