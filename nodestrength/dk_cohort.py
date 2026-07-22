"""Run BCT node strength + asymmetry index on a directory of DK connectomes.

Expected layout under ``--root``:

    sub-XXX/dk_connectome.csv     84x84, symmetric, zero diagonal
    sub-XXX/dk_nodes.mif          label image (required for --with-volume-ai)

See ``dk-ai-cohort --help`` and ``containers/README.md`` for container usage.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

from nodestrength.asymmetry import log_ai, side_ai
from nodestrength.connectome import _strengths_und, load_connectome, uses_bctpy
from nodestrength.dk_atlas import (
    build_dk_nodes,
    compute_dk_volumes_mm3,
    lr_pair_table,
)


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


def _node_table(subject_id: str, values: np.ndarray, value_col: str) -> pd.DataFrame:
    """Per-node table for one scalar measure (strength or volume)."""
    nodes = build_dk_nodes()
    rows = []
    for n in nodes:
        rows.append({
            "subject": subject_id,
            "fs_default_index": n.fs_default_index,
            "name": n.name,
            "side": n.side,
            "region_type": n.region_type,
            value_col: float(values[n.fs_default_index - 1]),
        })
    return pd.DataFrame(rows)


def _pair_ai_table(
    subject_id: str,
    values: np.ndarray,
    l_col: str,
    r_col: str,
) -> pd.DataFrame:
    """Interhemispheric AI for matched L/R pairs from a length-84 value vector."""
    pairs = lr_pair_table()
    rows = []
    for _, p in pairs.iterrows():
        L = float(values[int(p["L_index"]) - 1])
        R = float(values[int(p["R_index"]) - 1])
        rows.append({
            "subject": subject_id,
            "roi_name": p["roi_name"],
            "region_type": p["region_type"],
            "L_index": int(p["L_index"]),
            "R_index": int(p["R_index"]),
            l_col: L,
            r_col: R,
            "side_ai": side_ai(L, R),
            "log_ai": log_ai(L, R),
        })
    return pd.DataFrame(rows)


def _ai_summary(df: pd.DataFrame, out_path: Path) -> None:
    summary = (df.groupby(["roi_name", "region_type"])
               .agg(n_subjects=("subject", "count"),
                    side_ai_mean=("side_ai", "mean"),
                    side_ai_std=("side_ai", "std"),
                    log_ai_mean=("log_ai", "mean"),
                    log_ai_std=("log_ai", "std"))
               .reset_index()
               .sort_values(["region_type", "roi_name"]))
    summary.to_csv(out_path, index=False)


def _strength_vs_volume_table(strength_ai: pd.DataFrame,
                              volume_ai: pd.DataFrame) -> pd.DataFrame:
    keys = ["subject", "roi_name", "region_type", "L_index", "R_index"]
    s = strength_ai.rename(columns={
        "L_strength": "L_strength",
        "R_strength": "R_strength",
        "side_ai": "strength_side_ai",
        "log_ai": "strength_log_ai",
    })
    v = volume_ai.rename(columns={
        "L_volume_mm3": "L_volume_mm3",
        "R_volume_mm3": "R_volume_mm3",
        "side_ai": "volume_side_ai",
        "log_ai": "volume_log_ai",
    })
    merged = s.merge(v, on=keys, how="inner")
    return merged.sort_values(["subject", "region_type", "roi_name"]).reset_index(drop=True)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True, type=Path,
                   help="Directory containing sub-*/dk_connectome.csv files.")
    p.add_argument("--out", required=True, type=Path,
                   help="Output directory for node_strength_results (will be created).")
    p.add_argument("--include", nargs="*", default=None,
                   help="Restrict to these subject IDs (with or without 'sub-' prefix).")
    p.add_argument("--with-volume-ai", action="store_true",
                   help="Also compute ROI volumes from dk_nodes.mif and volume AI.")
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
    if args.with_volume_ai:
        print("Volume AI enabled (dk_nodes.mif).")

    strength_frames: List[pd.DataFrame] = []
    ai_frames: List[pd.DataFrame] = []
    volume_frames: List[pd.DataFrame] = []
    volume_ai_frames: List[pd.DataFrame] = []
    all_warns: List[str] = []

    strength_dir = args.out / "strength"
    strength_ps = strength_dir / "per_subject"
    strength_ps.mkdir(parents=True, exist_ok=True)

    volume_dir: Optional[Path] = None
    volume_ps: Optional[Path] = None
    if args.with_volume_ai:
        volume_dir = args.out / "volume"
        volume_ps = volume_dir / "per_subject"
        volume_ps.mkdir(parents=True, exist_ok=True)

    for sub_dir in subjects:
        sid = sub_dir.name[len("sub-"):]
        W = load_connectome(sub_dir / "dk_connectome.csv")
        warns = _validate_connectome(W, sid)
        all_warns.extend(warns)
        for w in warns:
            print(f"  WARN: {w}")

        s_vec = _strengths_und(W)
        st = _node_table(sid, s_vec, "strength")
        ai = _pair_ai_table(sid, s_vec, "L_strength", "R_strength")

        st.to_csv(strength_ps / f"sub-{sid}_strength.csv", index=False)
        ai.to_csv(strength_ps / f"sub-{sid}_ai.csv", index=False)
        strength_frames.append(st)
        ai_frames.append(ai)

        thal = ai[ai["roi_name"] == "Thalamus-Proper"]
        if len(thal):
            t = thal.iloc[0]
            msg = (f"  sub-{sid}: thalamus strength L={t['L_strength']:.1f}, "
                   f"R={t['R_strength']:.1f}, side_ai={t['side_ai']:+.4f}")
            if args.with_volume_ai:
                mif_path = sub_dir / "dk_nodes.mif"
                if mif_path.is_file():
                    try:
                        v_vec = compute_dk_volumes_mm3(mif_path)
                        vt = _pair_ai_table(sid, v_vec, "L_volume_mm3", "R_volume_mm3")
                        vrow = vt[vt["roi_name"] == "Thalamus-Proper"].iloc[0]
                        msg += (f" | volume L={vrow['L_volume_mm3']:.1f}, "
                                f"R={vrow['R_volume_mm3']:.1f}, "
                                f"side_ai={vrow['side_ai']:+.4f}")
                    except Exception:
                        pass
            print(msg)

        if args.with_volume_ai:
            mif_path = sub_dir / "dk_nodes.mif"
            if not mif_path.is_file():
                w = f"{sid}: dk_nodes.mif not found — skipping volume AI"
                all_warns.append(w)
                print(f"  WARN: {w}")
                continue
            try:
                v_vec = compute_dk_volumes_mm3(mif_path)
            except Exception as exc:
                w = f"{sid}: failed to read dk_nodes.mif: {exc}"
                all_warns.append(w)
                print(f"  WARN: {w}")
                continue

            vol = _node_table(sid, v_vec, "volume_mm3")
            vai = _pair_ai_table(sid, v_vec, "L_volume_mm3", "R_volume_mm3")
            vol.to_csv(volume_ps / f"sub-{sid}_volume.csv", index=False)
            vai.to_csv(volume_ps / f"sub-{sid}_volume_ai.csv", index=False)
            volume_frames.append(vol)
            volume_ai_frames.append(vai)

    cohort_strength = pd.concat(strength_frames, ignore_index=True)
    cohort_ai = pd.concat(ai_frames, ignore_index=True)
    cohort_strength.to_csv(strength_dir / "node_strength_cohort.csv", index=False)
    cohort_ai.to_csv(strength_dir / "asymmetry_index_cohort.csv", index=False)
    _ai_summary(cohort_ai, strength_dir / "cohort_summary.csv")

    manifest = {
        "subjects": [s.name for s in subjects],
        "n_subjects": len(subjects),
        "bct_backend": uses_bctpy(),
        "atlas": "Desikan-Killiany (MRtrix3 fs_default labelconvert)",
        "connectome_shape": [84, 84],
        "layout": {
            "strength": "strength/ — per-subject strength + strength AI and cohort tables",
            "volume": "volume/ — per-subject volume + volume AI (with --with-volume-ai)",
            "compare": "compare/ — cross-modality tables (with --with-volume-ai)",
        },
        "ai_formulas": {
            "side_ai": "(L - R) / (L + R)",
            "log_ai":  "ln(L / R)",
        },
        "volume_ai_enabled": args.with_volume_ai,
        "caveats": [
            "DK does NOT subdivide the thalamus into AV/CM/MDPf/PUL nuclei.",
            "Whole-thalamus AI here is L vs R of the single Thalamus-Proper node.",
            "For per-nucleus AI as in Piper et al. 2026, add a THOMAS step on top.",
        ],
        "warnings": all_warns,
    }

    if args.with_volume_ai and volume_frames:
        cohort_volume = pd.concat(volume_frames, ignore_index=True)
        cohort_volume_ai = pd.concat(volume_ai_frames, ignore_index=True)
        assert volume_dir is not None
        cohort_volume.to_csv(volume_dir / "node_volume_cohort.csv", index=False)
        cohort_volume_ai.to_csv(volume_dir / "volume_asymmetry_index_cohort.csv",
                                 index=False)
        _ai_summary(cohort_volume_ai, volume_dir / "cohort_volume_summary.csv")
        compare_dir = args.out / "compare"
        compare_dir.mkdir(exist_ok=True)
        cmp_df = _strength_vs_volume_table(cohort_ai, cohort_volume_ai)
        cmp_df.to_csv(compare_dir / "strength_vs_volume_ai.csv", index=False)
        manifest["volume_source"] = "dk_nodes.mif (tractography grid)"
        manifest["n_subjects_with_volume"] = len(volume_frames)
    elif args.with_volume_ai:
        manifest["volume_source"] = "dk_nodes.mif (none loaded)"
        manifest["n_subjects_with_volume"] = 0
        all_warns.append("Volume AI requested but no subject volumes were computed.")

    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2))

    _write_readme(args.out, len(subjects), all_warns, args.with_volume_ai)
    print(f"\nWrote results to {args.out}")
    return 0


def _write_readme(out_dir: Path, n_subjects: int, warnings: List[str],
                  with_volume_ai: bool) -> None:
    volume_section = ""
    volume_cohort = ""
    compare_cohort = ""
    volume_caveat = "- **Strength AI only** — re-run with `--with-volume-ai` for volumetric AI.\n"
    if with_volume_ai:
        volume_section = """
## Volume files (`volume/`)

### `volume/per_subject/sub-XXX_volume.csv` (84 rows)

**ROI volume** — voxel count × voxel size from ``dk_nodes.mif`` on the tractography grid (mm³).

Columns: `subject`, `fs_default_index`, `name`, `side`, `region_type`, `volume_mm3`.

### `volume/per_subject/sub-XXX_volume_ai.csv` (42 rows)

**Interhemispheric asymmetry index on volume** — same formulas as strength AI:

```
    side_ai = (L_volume - R_volume) / (L_volume + R_volume)
    log_ai  = ln(L_volume / R_volume)
```

Columns: `subject`, `roi_name`, `region_type`, `L_index`, `R_index`,
`L_volume_mm3`, `R_volume_mm3`, `side_ai`, `log_ai`.
"""
        volume_cohort = """
| `volume/node_volume_cohort.csv` | Stack of all `_volume.csv` files |
| `volume/volume_asymmetry_index_cohort.csv` | Stack of all `_volume_ai.csv` files |
| `volume/cohort_volume_summary.csv` | Per-ROI mean/SD of volume `side_ai` and `log_ai` |
"""
        compare_cohort = """
## Cross-modality files (`compare/`)

| File | Contents |
|------|----------|
| `compare/strength_vs_volume_ai.csv` | Side-by-side strength AI vs volume AI per ROI |

"""
        volume_caveat = (
            "- **Volume from dk_nodes.mif** — tractography grid, not FreeSurfer segstats.\n"
        )

    text = f"""# node_strength_results — node strength + asymmetry index

Generated by `dk-ai-cohort` (from the `nodestrength` package / container image).

## Folder layout

```
node_strength_results/
├── strength/          # connectivity (always written)
│   ├── per_subject/
│   ├── node_strength_cohort.csv
│   ├── asymmetry_index_cohort.csv
│   └── cohort_summary.csv
├── volume/            # optional (--with-volume-ai)
│   ├── per_subject/
│   └── … cohort volume tables
└── compare/           # optional (--with-volume-ai)
    └── strength_vs_volume_ai.csv
```

Shared docs (`README.md`, `manifest.json`, `nodestrength.md`, …) live at the
root of this folder.

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
- Volume AI: **{"enabled" if with_volume_ai else "disabled"}**.

## Strength files (`strength/`)

### `strength/per_subject/sub-XXX_strength.csv` (84 rows)

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

### `strength/per_subject/sub-XXX_ai.csv` (42 rows)

**Interhemispheric asymmetry index** on node strength — one row per matched L/R
ROI pair (34 cortical + 7 subcortical + 1 cerebellum):

```
    side_ai = (L_strength - R_strength) / (L_strength + R_strength)   [-1, +1]
    log_ai  = ln(L_strength / R_strength)
```

Columns: `subject`, `roi_name`, `region_type`, `L_index`, `R_index`,
`L_strength`, `R_strength`, `side_ai`, `log_ai`.
{volume_section}
## Strength cohort files

| File | Contents |
|------|----------|
| `strength/node_strength_cohort.csv` | Stack of all `_strength.csv` files |
| `strength/asymmetry_index_cohort.csv` | Stack of all `_ai.csv` files |
| `strength/cohort_summary.csv` | Per-ROI mean/SD of strength `side_ai` and `log_ai` |
{volume_cohort}{compare_cohort}## Root files

| File | Contents |
|------|----------|
| `manifest.json` | Run metadata, atlas info, warnings |

## Caveats

- **Raw values** — not normative z-scores (no age/sex/motion/mean-brain adjustment).
- **DK whole thalamus** — not THOMAS nuclei (AV/CM/MDPf/PUL). See Piper 2026.
- **No SOZ-AI** — `soz_ai` not computed unless SOZ side is supplied separately.
{volume_caveat}
## Validation warnings
"""
    if warnings:
        text += "\n".join(f"- {w}" for w in warnings) + "\n"
    else:
        text += "(none)\n"
    (out_dir / "README.md").write_text(text)


if __name__ == "__main__":
    raise SystemExit(main())
