"""Run the full per-subject pipeline over a MICA-MICs BIDS tree.

Usage
-----
    python scripts/run_micamics_cohort.py \
        --bids /data/openneuro/ds003969 \
        --derivatives /data/openneuro/ds003969/derivatives/nodestrength \
        --subjects-dir /data/openneuro/ds003969/derivatives/freesurfer \
        [--include HC001 HC002 ...] \
        [--dry-run] \
        [--slurm /path/to/submit.sh]

If ``--slurm`` is given, instead of executing locally, this script emits one
``sbatch``-style command per subject into the given file, ready for cluster
submission. Locally it runs subjects sequentially (intentional — recon-all is
single-threaded per subject and this avoids accidentally fork-bombing a
workstation).

The script is **deliberately a thin loop** around
``nodestrength run-subject``; the heavy logic lives in
``nodestrength.pipeline``.
"""

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nodestrength.bids import SubjectFiles, iter_subjects


def _subject_cmd(subject: SubjectFiles, derivatives: Path, subjects_dir: Path,
                 dry_run: bool) -> List[str]:
    out_dir = derivatives / f"sub-{subject.subject_id}"
    if subject.session:
        out_dir = out_dir / f"ses-{subject.session}"

    cmd = [
        sys.executable, "-m", "nodestrength.cli", "run-subject",
        subject.subject_id,
        "--t1", str(subject.t1),
        "--dwi", str(subject.dwi),
        "--bvec", str(subject.bvec),
        "--bval", str(subject.bval),
        "--rpe-b0", str(subject.rpe_b0 or subject.dwi),
        "--subjects-dir", str(subjects_dir),
        "--out-dir", str(out_dir),
    ]
    if dry_run:
        cmd.append("--dry-run")
    return cmd


def _emit_slurm(commands: List[List[str]], submit_file: Path,
                memory: str = "32G", time: str = "12:00:00",
                cpus: int = 8) -> None:
    """Write one ``sbatch`` line per subject into ``submit_file``."""
    submit_file.parent.mkdir(parents=True, exist_ok=True)
    with submit_file.open("w") as fh:
        fh.write("#!/bin/bash\n")
        for cmd in commands:
            wrapped = " ".join(shlex.quote(p) for p in cmd)
            fh.write(
                f"sbatch --job-name=nodestrength --mem={memory} "
                f"--time={time} --cpus-per-task={cpus} "
                f"--wrap={shlex.quote(wrapped)}\n"
            )
    submit_file.chmod(0o755)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bids", required=True, type=Path)
    p.add_argument("--derivatives", required=True, type=Path)
    p.add_argument("--subjects-dir", required=True, type=Path,
                   help="FreeSurfer SUBJECTS_DIR (will be created if missing).")
    p.add_argument("--include", nargs="*", default=None,
                   help="Restrict to these subject IDs (e.g. HC001 HC002).")
    p.add_argument("--dry-run", action="store_true",
                   help="Print commands without executing.")
    p.add_argument("--slurm", type=Path, default=None,
                   help="If set, emit a SLURM submission script instead of running.")
    args = p.parse_args(argv)

    subjects = list(iter_subjects(args.bids, include=args.include))
    if not subjects:
        print(f"No subjects discovered under {args.bids}.", file=sys.stderr)
        return 2

    print(f"Found {len(subjects)} subjects.")
    args.derivatives.mkdir(parents=True, exist_ok=True)
    args.subjects_dir.mkdir(parents=True, exist_ok=True)

    commands = [_subject_cmd(s, args.derivatives, args.subjects_dir, args.dry_run)
                for s in subjects]

    if args.slurm:
        _emit_slurm(commands, args.slurm)
        print(f"Wrote SLURM submission script: {args.slurm}")
        return 0

    import subprocess
    for cmd in commands:
        print(">>> " + " ".join(shlex.quote(p) for p in cmd))
        if not args.dry_run:
            subprocess.run(cmd, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
