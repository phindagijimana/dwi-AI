"""Run BCT node strength + asymmetry index on a directory of DKT connectomes.

Expected layout under ``--root`` (any subject folder name):

    <subject>/dkt_connectome.csv    78×78 fs_dkt connectome (DKT analysis; default)
    <subject>/dk_connectome.csv     84×84 fs_default (legacy)
    <subject>/nodes.mif             label image (required for --with-volume-ai)

Analysis auto-detects 78-node fs_dkt (dwi_pipeline Step 4) or legacy 84-node fs_default.
ENIGMA brain maps in ``reports/`` project values onto standard FreeSurfer DK aparc (fsa5).

See ``dkt-ai-cohort --help`` and ``containers/README.md`` for container usage.
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
from nodestrength.connectome import (
    _strengths_und,
    interhemispheric_strengths_und,
    intrahemispheric_strengths_und,
    load_connectome,
    uses_bctpy,
)
from nodestrength.analysis_atlas import AnalysisAtlas, node_index, resolve_analysis_atlas
from nodestrength.dk_clinical import (
    pair_soz_ai_table,
    soz_side_for_subject,
    strength_z_pair_table,
)
from nodestrength.dk_normative import (
    _normalize_subject_id,
    fit_dk_strength_model,
    prepare_dk_strength_long,
    save_dk_model,
    side_ai_z_from_controls,
)
from nodestrength.dk_inputs import (
    SubjectInputs,
    discover_subjects,
    filter_subjects,
    subject_file_prefix,
)
from nodestrength.ideas import load_participants
from nodestrength.parcellations import analysis_manifest_fields


def _write_clinical_derivatives(
    out_dir: Path,
    subjects: List[SubjectInputs],
    cohort_strength: pd.DataFrame,
    cohort_ai: pd.DataFrame,
    *,
    participants_path: Optional[Path],
    normative_model_path: Optional[Path],
    control_group: str,
) -> Optional[Path]:
    """Write per-subject SOZ AI and normative z-score tables when metadata allows."""
    if participants_path is None or not participants_path.is_file():
        return None

    participants = load_participants(participants_path)
    strength_ps = out_dir / "strength" / "per_subject"

    model = None
    model_out: Optional[Path] = None
    if normative_model_path is not None and normative_model_path.is_file():
        from nodestrength.dk_normative import load_dk_model
        model = load_dk_model(normative_model_path)
    elif "group" in participants.columns:
        controls = participants.loc[
            participants["group"].astype(str).str.lower() == control_group.lower(),
            "subject",
        ]
        control_ids = {_normalize_subject_id(s) for s in controls}
        if control_ids:
            controls_long = prepare_dk_strength_long(
                cohort_strength.loc[
                    cohort_strength["subject"].map(_normalize_subject_id).isin(control_ids)
                ],
                participants,
            )
            try:
                model = fit_dk_strength_model(controls_long)
                model_out = out_dir / "normative_strength_model.pkl"
                save_dk_model(model_out, model)
            except (ValueError, KeyError) as exc:
                print(f"  WARN: normative model not fitted: {exc}")

    control_ai = pd.DataFrame()
    if "group" in participants.columns:
        controls = participants.loc[
            participants["group"].astype(str).str.lower() == control_group.lower(),
            "subject",
        ]
        if not controls.empty:
            control_ids = {_normalize_subject_id(s) for s in controls}
            control_ai = cohort_ai.loc[
                cohort_ai["subject"].map(_normalize_subject_id).isin(control_ids)
            ]

    for subj in subjects:
        prefix = subject_file_prefix(subj.folder_name)
        sid = subj.subject_id
        ai_path = strength_ps / f"{prefix}_ai.csv"
        if not ai_path.is_file():
            continue
        ai = pd.read_csv(ai_path)

        soz_side = soz_side_for_subject(participants, sid)
        if soz_side in ("L", "R"):
            soz_df = pair_soz_ai_table(sid, ai, soz_side)
            soz_df.to_csv(strength_ps / f"{prefix}_soz_ai.csv", index=False)

        if model is not None:
            strength = pd.read_csv(strength_ps / f"{prefix}_strength.csv")
            from nodestrength.dk_clinical import subject_metadata
            meta = subject_metadata(participants, sid)
            z_df = strength_z_pair_table(sid, strength, model, meta)
            if not control_ai.empty:
                z_ai = side_ai_z_from_controls(ai, control_ai)
                z_df = z_df.merge(z_ai[["roi_name", "side_ai_z"]], on="roi_name", how="left")
            z_df.to_csv(strength_ps / f"{prefix}_strength_z.csv", index=False)

    return model_out


def _validate_connectome(W: np.ndarray, subject_id: str) -> tuple[List[str], AnalysisAtlas]:
    """Sanity checks; returns warnings and resolved atlas."""
    warns: List[str] = []
    try:
        atlas = resolve_analysis_atlas(W.shape[0])
    except ValueError:
        warns.append(
            f"{subject_id}: unexpected shape {W.shape}, expected (78,78) or (84,84)"
        )
        raise
    if W.shape != (atlas.n_nodes, atlas.n_nodes):
        warns.append(f"{subject_id}: unexpected shape {W.shape}, expected ({atlas.n_nodes},{atlas.n_nodes})")
    if not np.allclose(W, W.T):
        warns.append(f"{subject_id}: connectome not symmetric")
    if not np.allclose(np.diag(W), 0):
        warns.append(f"{subject_id}: connectome has non-zero diagonal")
    if W.min() < 0:
        warns.append(f"{subject_id}: connectome has negative edges")
    return warns, atlas


def _node_table(subject_id: str, values: np.ndarray, value_col: str,
                atlas: AnalysisAtlas) -> pd.DataFrame:
    """Per-node table for one scalar measure (strength or volume)."""
    nodes = atlas.build_nodes()
    rows = []
    for n in nodes:
        idx = node_index(n)
        rows.append({
            "subject": subject_id,
            "fs_default_index": idx,
            "name": n.name,
            "side": n.side,
            "region_type": n.region_type,
            value_col: float(values[idx - 1]),
        })
    return pd.DataFrame(rows)


def _pair_ai_table(
    subject_id: str,
    values: np.ndarray,
    l_col: str,
    r_col: str,
    atlas: AnalysisAtlas,
) -> pd.DataFrame:
    """Interhemispheric AI for matched L/R pairs."""
    pairs = atlas.lr_pair_table()
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
                   help="Directory containing one folder per subject with connectome CSV.")
    p.add_argument("--out", required=True, type=Path,
                   help="Output directory for node_strength_results (will be created).")
    p.add_argument("--fs-root", type=Path, default=None,
                   help="Optional FreeSurfer SUBJECTS_DIR (for dk_nodes.mif lookup).")
    p.add_argument("--include", nargs="*", default=None,
                   help="Restrict to these subject IDs (with or without 'sub-' prefix).")
    p.add_argument("--with-volume-ai", action="store_true",
                   help="Also compute ROI volumes from dk_nodes.mif and volume AI.")
    p.add_argument("--report", action="store_true",
                   help="Write clinical PDF + figures (default unless --no-report).")
    p.add_argument("--no-report", action="store_true",
                   help="Skip clinical PDF reports.")
    p.add_argument("--participants", type=Path, default=None,
                   help="participants.tsv for SOZ side, group, and normative covariates.")
    p.add_argument("--normative-model", type=Path, default=None,
                   help="Pre-fitted DK strength normative model (.pkl). "
                        "If omitted, fit from controls in --participants.")
    p.add_argument("--control-group", default="control",
                   help="Group label for normative controls (default: control).")
    args = p.parse_args(argv)

    if args.no_report:
        write_report = False
    else:
        write_report = True

    args.out.mkdir(parents=True, exist_ok=True)

    subjects = filter_subjects(discover_subjects(args.root, args.fs_root), args.include)
    if not subjects:
        print(f"No subjects found under {args.root}", file=sys.stderr)
        if args.fs_root:
            print(f"(also checked FreeSurfer root {args.fs_root})", file=sys.stderr)
        return 2

    print(f"Found {len(subjects)} subjects under {args.root}.")
    if args.fs_root:
        print(f"FreeSurfer root: {args.fs_root}")
    print(f"BCT backend active: {uses_bctpy()}")
    if args.with_volume_ai:
        print("Volume AI enabled (dk_nodes.mif).")
    if write_report:
        print("Clinical PDF reports enabled (reports/sub-XXX/report.pdf).")

    strength_frames: List[pd.DataFrame] = []
    ai_frames: List[pd.DataFrame] = []
    strength_intra_frames: List[pd.DataFrame] = []
    ai_intra_frames: List[pd.DataFrame] = []
    strength_inter_frames: List[pd.DataFrame] = []
    ai_inter_frames: List[pd.DataFrame] = []
    volume_frames: List[pd.DataFrame] = []
    volume_ai_frames: List[pd.DataFrame] = []
    all_warns: List[str] = []
    atlas_used: Optional[AnalysisAtlas] = None

    strength_dir = args.out / "strength"
    strength_ps = strength_dir / "per_subject"
    strength_ps.mkdir(parents=True, exist_ok=True)

    volume_dir: Optional[Path] = None
    volume_ps: Optional[Path] = None
    if args.with_volume_ai:
        volume_dir = args.out / "volume"
        volume_ps = volume_dir / "per_subject"
        volume_ps.mkdir(parents=True, exist_ok=True)

    for subj in subjects:
        sid = subj.subject_id
        prefix = subject_file_prefix(subj.folder_name)
        W = load_connectome(subj.connectome_csv)
        try:
            warns, atlas = _validate_connectome(W, sid)
        except ValueError:
            print(f"  ERROR: {sid}: unsupported connectome shape {W.shape}", file=sys.stderr)
            return 1
        atlas_used = atlas
        all_warns.extend(warns)
        for w in warns:
            print(f"  WARN: {w}")

        s_vec = _strengths_und(W)
        st = _node_table(sid, s_vec, "strength", atlas)
        ai = _pair_ai_table(sid, s_vec, "L_strength", "R_strength", atlas)

        s_intra = intrahemispheric_strengths_und(W)
        st_intra = _node_table(sid, s_intra, "strength_intra", atlas)
        ai_intra = _pair_ai_table(sid, s_intra, "L_strength_intra", "R_strength_intra", atlas)

        s_inter = interhemispheric_strengths_und(W)
        st_inter = _node_table(sid, s_inter, "strength_inter", atlas)
        ai_inter = _pair_ai_table(sid, s_inter, "L_strength_inter", "R_strength_inter", atlas)

        st.to_csv(strength_ps / f"{prefix}_strength.csv", index=False)
        ai.to_csv(strength_ps / f"{prefix}_ai.csv", index=False)
        st_intra.to_csv(strength_ps / f"{prefix}_strength_intra.csv", index=False)
        ai_intra.to_csv(strength_ps / f"{prefix}_ai_intra.csv", index=False)
        st_inter.to_csv(strength_ps / f"{prefix}_strength_inter.csv", index=False)
        ai_inter.to_csv(strength_ps / f"{prefix}_ai_inter.csv", index=False)
        strength_frames.append(st)
        ai_frames.append(ai)
        strength_intra_frames.append(st_intra)
        ai_intra_frames.append(ai_intra)
        strength_inter_frames.append(st_inter)
        ai_inter_frames.append(ai_inter)

        thal = ai[ai["roi_name"] == "Thalamus-Proper"]
        if len(thal):
            t = thal.iloc[0]
            ti = ai_intra[ai_intra["roi_name"] == "Thalamus-Proper"].iloc[0]
            te = ai_inter[ai_inter["roi_name"] == "Thalamus-Proper"].iloc[0]
            msg = (f"  {prefix}: thalamus strength L={t['L_strength']:.1f}, "
                   f"R={t['R_strength']:.1f}, side_ai={t['side_ai']:+.4f}, "
                   f"intra_ai={ti['side_ai']:+.4f}, inter_ai={te['side_ai']:+.4f}")
            if args.with_volume_ai and subj.label_mif is not None:
                try:
                    v_vec = atlas.compute_volumes_mm3(subj.label_mif)
                    vt = _pair_ai_table(sid, v_vec, "L_volume_mm3", "R_volume_mm3", atlas)
                    vrow = vt[vt["roi_name"] == "Thalamus-Proper"].iloc[0]
                    msg += (f" | volume L={vrow['L_volume_mm3']:.1f}, "
                            f"R={vrow['R_volume_mm3']:.1f}, "
                            f"side_ai={vrow['side_ai']:+.4f}")
                except Exception:
                    pass
            print(msg)

        if args.with_volume_ai:
            if subj.label_mif is None:
                w = f"{sid}: label MIF not found — skipping volume AI"
                all_warns.append(w)
                print(f"  WARN: {w}")
                continue
            try:
                v_vec = atlas.compute_volumes_mm3(subj.label_mif)
            except Exception as exc:
                w = f"{sid}: failed to read label MIF: {exc}"
                all_warns.append(w)
                print(f"  WARN: {w}")
                continue

            vol = _node_table(sid, v_vec, "volume_mm3", atlas)
            vai = _pair_ai_table(sid, v_vec, "L_volume_mm3", "R_volume_mm3", atlas)
            vol.to_csv(volume_ps / f"{prefix}_volume.csv", index=False)
            vai.to_csv(volume_ps / f"{prefix}_volume_ai.csv", index=False)
            volume_frames.append(vol)
            volume_ai_frames.append(vai)

    cohort_strength = pd.concat(strength_frames, ignore_index=True)
    cohort_ai = pd.concat(ai_frames, ignore_index=True)
    cohort_strength_intra = pd.concat(strength_intra_frames, ignore_index=True)
    cohort_ai_intra = pd.concat(ai_intra_frames, ignore_index=True)
    cohort_strength_inter = pd.concat(strength_inter_frames, ignore_index=True)
    cohort_ai_inter = pd.concat(ai_inter_frames, ignore_index=True)
    cohort_strength.to_csv(strength_dir / "node_strength_cohort.csv", index=False)
    cohort_ai.to_csv(strength_dir / "asymmetry_index_cohort.csv", index=False)
    cohort_strength_intra.to_csv(strength_dir / "node_strength_intra_cohort.csv", index=False)
    cohort_ai_intra.to_csv(strength_dir / "asymmetry_index_intra_cohort.csv", index=False)
    cohort_strength_inter.to_csv(strength_dir / "node_strength_inter_cohort.csv", index=False)
    cohort_ai_inter.to_csv(strength_dir / "asymmetry_index_inter_cohort.csv", index=False)
    _ai_summary(cohort_ai, strength_dir / "cohort_summary.csv")
    _ai_summary(cohort_ai_intra, strength_dir / "cohort_intra_summary.csv")
    _ai_summary(cohort_ai_inter, strength_dir / "cohort_inter_summary.csv")

    clinical_model_path = _write_clinical_derivatives(
        args.out,
        subjects,
        cohort_strength,
        cohort_ai,
        participants_path=args.participants,
        normative_model_path=args.normative_model,
        control_group=args.control_group,
    )

    manifest = {
        "connectome_root": str(args.root),
        "fs_root": str(args.fs_root) if args.fs_root else None,
        "subjects": [s.folder_name for s in subjects],
        "n_subjects": len(subjects),
        "bct_backend": uses_bctpy(),
        **analysis_manifest_fields(),
        "atlas": (
            f"Desikan-Killiany-Tourville (MRtrix3 {atlas_used.atlas})"
            if atlas_used else "auto-detected per subject"
        ),
        "connectome_shape": [atlas_used.n_nodes, atlas_used.n_nodes] if atlas_used else None,
        "analysis_connectome_file": "dkt_connectome.csv",
        "layout": {
            "strength": "strength/ — per-subject strength + strength AI and cohort tables",
            "volume": "volume/ — per-subject volume + volume AI (with --with-volume-ai)",
            "compare": "compare/ — cross-modality tables (with --with-volume-ai)",
            "reports": "reports/ — clinical PDF + full figure gallery per subject (default)",
        },
        "ai_formulas": {
            "side_ai": "(L - R) / (L + R)",
            "log_ai":  "ln(L / R)",
            "intrahemispheric_strength": "row sum of connectome edges within the same hemisphere only",
            "interhemispheric_strength": "row sum of connectome edges across hemispheres only (L↔R)",
        },
        "volume_ai_enabled": args.with_volume_ai,
        "caveats": [
            "DK does NOT subdivide the thalamus into AV/CM/MDPf/PUL nuclei.",
            "Whole-thalamus AI here is L vs R of the single Thalamus-Proper node.",
            "For per-nucleus AI as in Piper et al. 2026, add a THOMAS step on top.",
        ],
        "warnings": all_warns,
    }
    if args.participants:
        manifest["participants"] = str(args.participants)
        manifest["control_group"] = args.control_group
    if clinical_model_path is not None:
        manifest["normative_strength_model"] = str(
            clinical_model_path.relative_to(args.out))

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

    if write_report:
        from nodestrength.clinical_report import SubjectReportInput, generate_cohort_reports
        report_paths = generate_cohort_reports(
            args.out,
            [
                SubjectReportInput(
                    folder_name=s.folder_name,
                    connectome_csv=s.connectome_csv,
                    subject_dir=s.subject_dir,
                    fs_subject_dir=s.fs_subject_dir,
                )
                for s in subjects
            ],
        )
        manifest["clinical_reports"] = [str(p.relative_to(args.out)) for p in report_paths]
        manifest["n_clinical_reports"] = len(report_paths)
        (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2))
        for p in report_paths:
            print(f"  report: {p}")

    _write_readme(args.out, len(subjects), all_warns, args.with_volume_ai, write_report)
    print(f"\nWrote results to {args.out}")
    return 0


def _write_readme(out_dir: Path, n_subjects: int, warnings: List[str],
                  with_volume_ai: bool, with_report: bool = False) -> None:
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

    report_section = ""
    if with_report:
        report_section = """
## Clinical reports (`reports/`)

| File | Contents |
|------|----------|
| `reports/sub-XXX/report.pdf` | Lean clinical summary (tables + two key figures) |
| `reports/sub-XXX/figures/` | Full PNG gallery (cortical map, subcortical panels, seed profiles, etc.) |

"""

    text = f"""# node_strength_results — node strength + asymmetry index

Generated by `dkt-ai-cohort` (from the `nodestrength` package / container image).

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
{report_section}
Shared docs (`README.md`, `manifest.json`, `nodestrength.md`, …) live at the
root of this folder.

## Documentation

| File | Description |
|------|-------------|
| **`nodestrength.docx`** | Full pipeline documentation (regenerate locally from `nodestrength.md`). |
| **`paper.md`** | Summary of Piper et al. 2026 — question, findings, key ideas |
| **`BCT.md`** | Brain Connectivity Toolbox — node strength and `strengths_und` |
| This `README.md` | Short summary of inputs, outputs, and caveats for this results folder |

Per-subject file definitions, sources, and limitations: **§12** in `nodestrength.docx`
(or `nodestrength.md` in the source repo).

## Input

- Parcellation: **DKT analysis** — MRtrix3 ``fs_default`` 84-node grid from ``dkt_connectome.csv``.
- ENIGMA figures use **DK aparc** on fsaverage5 (see ``viz_*`` fields in ``manifest.json``).
- Connectome file: **`dkt_connectome.csv`** per subject (84×84, SIFT2-weighted).
- Connectome matrix: 84×84, SIFT2-weighted streamline counts from
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

- **`_ai.csv` is raw asymmetry** — normative z-scores are in `_strength_z.csv`
  when `--participants` includes controls (or `--normative-model` is supplied).
- **DK whole thalamus** — not THOMAS nuclei (AV/CM/MDPf/PUL). See Piper 2026.
- **SOZ AI** — written to `_soz_ai.csv` when SOZ side is in `--participants`.
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
