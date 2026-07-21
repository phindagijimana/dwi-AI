"""Run BCT node strength + asymmetry index on a directory of DK connectomes.

Targets the Gugger_Lab dwi_test2 pipeline output:

    <root>/sub-XXX/dk_connectome.csv     84x84, symmetric, zero diagonal
    <root>/sub-XXX/dk_nodes.mrinfo.txt   confirms fs_default LUT used

Caveat: the Desikan-Killiany parcellation treats each thalamus as **one node
per hemisphere**. This script does NOT compute per-thalamic-nucleus AI as in
the Piper paper — that requires a THOMAS segmentation step on top of the
existing FreeSurfer outputs. What this script DOES compute, per subject:

* BCT node strength for all 84 DK nodes.
* Per-pair side_ai = (L-R)/(L+R) and log_ai = ln(L/R) for the 41 matched
  L/R DK ROIs (34 cortical + 7 subcortical, including whole-thalamus).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nodestrength.asymmetry import log_ai, side_ai
from nodestrength.connectome import _strengths_und, load_connectome, uses_bctpy
from nodestrength.dk_atlas import build_dk_nodes, lr_pair_table


def _find_subjects(root: Path) -> List[Path]:
    """Return ``sub-*`` directories that contain a ``dk_connectome.csv``."""
    return sorted([
        sub for sub in root.iterdir()
        if sub.is_dir() and sub.name.startswith("sub-")
           and (sub / "dk_connectome.csv").is_file()
    ])


def _validate_connectome(W: np.ndarray, subject_id: str) -> List[str]:
    """Sanity checks; returns a list of warnings (empty if all good)."""
    warns: List[str] = []
    if W.shape != (84, 84):
        warns.append(f"{subject_id}: unexpected shape {W.shape}, expected (84,84)")
    if not np.allclose(W, W.T):
        warns.append(f"{subject_id}: connectome not symmetric")
    if not np.allclose(np.diag(W), 0):
        warns.append(f"{subject_id}: connectome has non-zero diagonal")
    if W.min() < 0:
        warns.append(f"{subject_id}: connectome has negative edges")
    return warns


def _strength_table(subject_id: str, W: np.ndarray) -> pd.DataFrame:
    """Per-node BCT strength for one subject, joined with the DK lookup."""
    s = _strengths_und(W)
    nodes = build_dk_nodes()
    rows = []
    for n in nodes:
        rows.append({
            "subject": subject_id,
            "fs_default_index": n.fs_default_index,
            "name": n.name,
            "side": n.side,
            "region_type": n.region_type,
            "strength": float(s[n.fs_default_index - 1]),
        })
    return pd.DataFrame(rows)


def _ai_table(subject_id: str, W: np.ndarray) -> pd.DataFrame:
    """Per L/R pair AI table — 41 rows."""
    s = _strengths_und(W)
    pairs = lr_pair_table()
    rows = []
    for _, p in pairs.iterrows():
        L = float(s[int(p["L_index"]) - 1])
        R = float(s[int(p["R_index"]) - 1])
        rows.append({
            "subject": subject_id,
            "roi_name": p["roi_name"],
            "region_type": p["region_type"],
            "L_index": int(p["L_index"]),
            "R_index": int(p["R_index"]),
            "L_strength": L,
            "R_strength": R,
            "side_ai": side_ai(L, R),
            "log_ai": log_ai(L, R),     # well-defined since L,R > 0 for DK
        })
    return pd.DataFrame(rows)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True, type=Path,
                   help="Directory containing sub-*/dk_connectome.csv files.")
    p.add_argument("--out", required=True, type=Path,
                   help="Output directory for node_strength_results (will be created).")
    p.add_argument("--include", nargs="*", default=None,
                   help="Restrict to these subject IDs (with or without 'sub-' prefix).")
    args = p.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)

    subjects = _find_subjects(args.root)
    if args.include:
        wanted = {s.lstrip("sub-") for s in args.include}
        subjects = [s for s in subjects if s.name[len("sub-"):] in wanted]
    if not subjects:
        print(f"No subjects found under {args.root}", file=sys.stderr)
        return 2

    print(f"Found {len(subjects)} subjects under {args.root}.")
    print(f"BCT backend active: {uses_bctpy()}")

    strength_frames: List[pd.DataFrame] = []
    ai_frames: List[pd.DataFrame] = []
    all_warns: List[str] = []
    per_subject_dir = args.out / "per_subject"
    per_subject_dir.mkdir(exist_ok=True)

    for sub_dir in subjects:
        sid = sub_dir.name[len("sub-"):]
        W = load_connectome(sub_dir / "dk_connectome.csv")
        warns = _validate_connectome(W, sid)
        all_warns.extend(warns)
        for w in warns:
            print(f"  WARN: {w}")

        st = _strength_table(sid, W)
        ai = _ai_table(sid, W)

        st.to_csv(per_subject_dir / f"sub-{sid}_strength.csv", index=False)
        ai.to_csv(per_subject_dir / f"sub-{sid}_ai.csv", index=False)

        strength_frames.append(st)
        ai_frames.append(ai)

        # Highlight whole-thalamus AI for stdout.
        thal = ai[ai["roi_name"] == "Thalamus-Proper"]
        if len(thal):
            t = thal.iloc[0]
            print(f"  sub-{sid}: thalamus L={t['L_strength']:.1f}, "
                  f"R={t['R_strength']:.1f}, "
                  f"side_ai={t['side_ai']:+.4f}, log_ai={t['log_ai']:+.4f}")

    cohort_strength = pd.concat(strength_frames, ignore_index=True)
    cohort_ai = pd.concat(ai_frames, ignore_index=True)
    cohort_strength.to_csv(args.out / "node_strength_cohort.csv", index=False)
    cohort_ai.to_csv(args.out / "asymmetry_index_cohort.csv", index=False)

    # Cohort-level summary per ROI pair.
    summary = (cohort_ai.groupby(["roi_name", "region_type"])
               .agg(n_subjects=("subject", "count"),
                    side_ai_mean=("side_ai", "mean"),
                    side_ai_std=("side_ai", "std"),
                    log_ai_mean=("log_ai", "mean"),
                    log_ai_std=("log_ai", "std"))
               .reset_index()
               .sort_values(["region_type", "roi_name"]))
    summary.to_csv(args.out / "cohort_summary.csv", index=False)

    # Run manifest.
    manifest = {
        "subjects": [s.name for s in subjects],
        "n_subjects": len(subjects),
        "bct_backend": uses_bctpy(),
        "atlas": "Desikan-Killiany (MRtrix3 fs_default labelconvert)",
        "connectome_shape": [84, 84],
        "ai_formulas": {
            "side_ai": "(L - R) / (L + R)",
            "log_ai":  "ln(L / R)",
        },
        "caveats": [
            "DK does NOT subdivide the thalamus into AV/CM/MDPf/PUL nuclei.",
            "Whole-thalamus AI here is L vs R of the single Thalamus-Proper node.",
            "For per-nucleus AI as in Piper et al. 2026, add a THOMAS step on top.",
        ],
        "warnings": all_warns,
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2))

    _write_readme(args.out, len(subjects), all_warns)
    print(f"\nWrote results to {args.out}")
    return 0


def _write_readme(out_dir: Path, n_subjects: int, warnings: List[str]) -> None:
    text = f"""# node_strength_results — node strength + asymmetry index

Generated by `scripts/run_dk_ai_cohort.py` (from the `node_strength` Python
package).

## Documentation

| File | Description |
|------|-------------|
| **`nodestrength.docx`** | Full pipeline documentation (analysis + Gugger Lab runbook). Start here. |
| **`paper.md`** | Summary of Piper et al. 2026 — question, findings, key ideas |
| **`BCT.md`** | Brain Connectivity Toolbox — node strength and `strengths_und` |
| This `README.md` | Short summary of inputs, outputs, and caveats for this results folder |

Per-subject file definitions, sources, and limitations: **§12** in `nodestrength.docx`
(or `nodestrength.md` in the source repo).

## Input

- Parcellation: **Desikan-Killiany** (MRtrix3 `fs_default.txt`, 84 nodes).
- Connectome: 84×84, SIFT2-weighted streamline counts from
  `tck2connectome -symmetric -zero_diagonal`.
- Pipeline upstream: QSIPrep → FreeSurfer → QSIRecon → DK labelconvert.
- Subjects processed: **{n_subjects}**.

## Per-subject files

### `per_subject/sub-XXX_strength.csv` (84 rows)

**Node strength** — sum of connectome edge weights per DK node:

```
    s_i = sum_{{j != i}} W_ij
```

| Source | Reference |
|--------|-----------|
| Connectivity strength concept | Piper et al. *Epilepsia* 2026; DOI 10.1002/epi.70099 |
| BCT implementation | Rubinov & Sporns 2010, *NeuroImage* 52(3):1059–1069 (`strengths_und`) |
| Connectome | MRtrix3 `tck2connectome` + SIFT2 (Tournier et al. 2019) |

Columns: `subject`, `fs_default_index`, `name`, `side`, `region_type`, `strength`.

### `per_subject/sub-XXX_ai.csv` (41 rows)

**Interhemispheric asymmetry index** on node strength — one row per matched L/R
ROI pair (34 cortical + 7 subcortical):

```
    side_ai = (L_strength - R_strength) / (L_strength + R_strength)   [-1, +1]
    log_ai  = ln(L_strength / R_strength)
```

| Source | Reference |
|--------|-----------|
| L/R strengths | From `_strength.csv` at paired node indices |
| AI formula | Standard normalized asymmetry index; same as Gugger Lab ASL-AI pipeline |
| L/R pairing | `nodestrength.dk_atlas.lr_pair_table()` (empirically verified) |

**Note:** Piper et al. test laterality via mixed GLM interactions, not this
closed-form index. `_ai.csv` is a complementary scalar for plots and screening.

Columns: `subject`, `roi_name`, `region_type`, `L_index`, `R_index`,
`L_strength`, `R_strength`, `side_ai`, `log_ai`.

## Cohort files

| File | Contents |
|------|----------|
| `node_strength_cohort.csv` | Stack of all `_strength.csv` files |
| `asymmetry_index_cohort.csv` | Stack of all `_ai.csv` files |
| `cohort_summary.csv` | Per-ROI mean/SD of `side_ai` and `log_ai` |
| `manifest.json` | Run metadata, atlas info, warnings |

## Caveats

- **Raw values** — not normative z-scores (no age/sex/motion/mean-brain adjustment).
- **DK whole thalamus** — not THOMAS nuclei (AV/CM/MDPf/PUL). See Piper 2026.
- **No SOZ-AI** — `soz_ai` not computed unless SOZ side is supplied separately.
- **Not volumetric AI** — `_ai.csv` is on connectivity strength, not ROI volume.

## Validation warnings
"""
    if warnings:
        text += "\n".join(f"- {w}" for w in warnings) + "\n"
    else:
        text += "(none)\n"
    (out_dir / "README.md").write_text(text)


if __name__ == "__main__":
    raise SystemExit(main())
