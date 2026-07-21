"""Inspect a mounted SMB outputs tree and report manifest / BCT usage.

Usage:
    python scripts/inspect_smb_outputs.py --root /mnt/smb/Workflows/DWI-AI --out report.csv

The script will look for `sub-*` subject folders and for each subject try to
read `manifest.json`, `connectome.csv` and `node_lookup.tsv`. It also
reports `uses_bctpy()` by importing the local `nodestrength` package.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import csv
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def check_bct_backend():
    try:
        from nodestrength.connectome import uses_bctpy
        return bool(uses_bctpy())
    except Exception:
        return None


def inspect_subject(sub_path: Path):
    manifest_p = sub_path / "manifest.json"
    connectome_p = sub_path / "connectome.csv"
    lookup_p = sub_path / "node_lookup.tsv"

    manifest = None
    if manifest_p.exists():
        try:
            manifest = json.loads(manifest_p.read_text())
        except Exception as e:
            manifest = {"_manifest_error": str(e)}

    found_manifest_bct = None
    if isinstance(manifest, dict) and "bct_backend" in manifest:
        found_manifest_bct = manifest.get("bct_backend")

    bct_runtime = check_bct_backend()

    return {
        "subject_dir": str(sub_path),
        "manifest_exists": manifest_p.exists(),
        "manifest_bct": found_manifest_bct,
        "manifest_summary": json.dumps(manifest) if manifest is not None else "",
        "connectome_exists": connectome_p.exists(),
        "lookup_exists": lookup_p.exists(),
        "bct_runtime_active": bct_runtime,
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True, type=Path, help="Root path to mounted SMB outputs (e.g. /mnt/smb/Workflows/DWI-AI)")
    p.add_argument("--out", type=Path, default=None, help="CSV report path (default stdout)")
    args = p.parse_args(argv)

    root = args.root
    if not root.exists():
        print(f"Root path {root} does not exist. Mount the SMB share first.")
        return 2

    subjects = sorted([d for d in root.iterdir() if d.is_dir() and d.name.startswith("sub-")])
    if not subjects:
        print(f"No subject sub-* folders found under {root}")
        return 2

    rows = []
    for s in subjects:
        rows.append(inspect_subject(s))

    fieldnames = [
        "subject_dir", "manifest_exists", "manifest_bct", "connectome_exists",
        "lookup_exists", "bct_runtime_active", "manifest_summary",
    ]

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote report to {args.out}")
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
