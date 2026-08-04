"""ENIGMA-style clinical figures from nodestrength CSV outputs."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from nodestrength.connectome import load_connectome
from nodestrength.dk_atlas import _CORTEX, lr_pair_table
from nodestrength.dk_inputs import subject_file_prefix
from nodestrength.fs_anatomy import find_aparc_seg, fs_subcortical_volumes_mm3

logger = logging.getLogger(__name__)

_APARC_FSA5_PATH = (
    Path(__file__).resolve().parent / "data" / "parcellations" / "aparc_fsa5.csv"
)
_FSA5_VERTS_PER_HEMI = 10242

# ENIGMA subcortical viewer order (L then R; ventricles omitted).
_ENIGMA_SCTX_NAMES: Tuple[str, ...] = (
    "Accumbens-area",
    "Amygdala",
    "Caudate",
    "Hippocampus",
    "Pallidum",
    "Putamen",
    "Thalamus-Proper",
)

# fs_default 1-based indices for seed-based connectivity profiles.
_SEED_INDICES: Dict[str, Tuple[int, int]] = {
    "thalamus": (36, 43),
    "hippocampus": (40, 47),
    "amygdala": (41, 48),
}

_SEED_TITLES: Dict[str, str] = {
    "thalamus": "Thalamocortical connectivity (top targets)",
    "hippocampus": "Hippocampal cortical connectivity (top targets)",
    "amygdala": "Amygdalar cortical connectivity (top targets)",
}


def _short_label(name: str, max_len: int = 22) -> str:
    label = name.replace("-Proper", "").replace("-area", "")
    if len(label) > max_len:
        return label[: max_len - 1] + "…"
    return label


def _load_strength(results_dir: Path, prefix: str) -> pd.DataFrame:
    path = results_dir / "strength" / "per_subject" / f"{prefix}_strength.csv"
    return pd.read_csv(path)


def _load_strength_ai(results_dir: Path, prefix: str) -> pd.DataFrame:
    path = results_dir / "strength" / "per_subject" / f"{prefix}_ai.csv"
    return pd.read_csv(path)


def _load_volume_ai(results_dir: Path, prefix: str) -> Optional[pd.DataFrame]:
    path = results_dir / "volume" / "per_subject" / f"{prefix}_volume_ai.csv"
    return pd.read_csv(path) if path.is_file() else None


def _load_strength_intra(results_dir: Path, prefix: str) -> Optional[pd.DataFrame]:
    path = results_dir / "strength" / "per_subject" / f"{prefix}_strength_intra.csv"
    return pd.read_csv(path) if path.is_file() else None


def _load_intra_ai(results_dir: Path, prefix: str) -> Optional[pd.DataFrame]:
    path = results_dir / "strength" / "per_subject" / f"{prefix}_ai_intra.csv"
    return pd.read_csv(path) if path.is_file() else None


def _cortical_strength_by_side(strength: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    labels = list(_CORTEX)
    left = np.array([
        float(strength.loc[strength["name"] == f"L.{n}", "strength"].iloc[0])
        for n in labels
    ])
    right = np.array([
        float(strength.loc[strength["name"] == f"R.{n}", "strength"].iloc[0])
        for n in labels
    ])
    return left, right, labels


def _subcortical_vectors(
    strength: pd.DataFrame,
    ai: pd.DataFrame,
    *,
    value_col: str = "strength",
) -> pd.DataFrame:
    rows = []
    for name in _ENIGMA_SCTX_NAMES:
        pair = ai.loc[ai["roi_name"] == name].iloc[0]
        l_col = "L_strength_intra" if value_col == "strength_intra" else "L_strength"
        r_col = "R_strength_intra" if value_col == "strength_intra" else "R_strength"
        if l_col not in pair.index:
            l_col, r_col = "L_strength", "R_strength"
        l_val = float(strength.loc[strength["name"] == f"L.{name}", value_col].iloc[0])
        r_val = float(strength.loc[strength["name"] == f"R.{name}", value_col].iloc[0])
        rows.append({
            "roi_name": name,
            "L_strength": l_val,
            "R_strength": r_val,
            "side_ai": float(pair["side_ai"]),
        })
    return pd.DataFrame(rows)


def _save_fig(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    return path


def plot_cortical_strength_map(
    strength: pd.DataFrame,
    out_path: Path,
    *,
    title: str = "Cortical node strength (L vs R)",
) -> Path:
    """Grouped horizontal bars for 34 DK cortical regions."""
    left, right, labels = _cortical_strength_by_side(strength)
    y = np.arange(len(labels))
    height = 0.38
    fig, ax = plt.subplots(figsize=(8.5, 10))
    ax.barh(y - height / 2, left, height=height, label="Left", color="#4C72B0")
    ax.barh(y + height / 2, right, height=height, label="Right", color="#DD8452")
    ax.set_yticks(y)
    ax.set_yticklabels([_short_label(n) for n in labels], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("Node strength (SIFT2-weighted)")
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(axis="x", alpha=0.25)
    return _save_fig(out_path)


def plot_cortical_ai_map(
    ai: pd.DataFrame,
    out_path: Path,
    *,
    title: str = "Cortical strength asymmetry (side AI)",
) -> Path:
    """Signed asymmetry index for cortical L/R pairs."""
    cortex = ai.loc[ai["region_type"] == "cortex"].copy()
    cortex = cortex.sort_values("side_ai", key=lambda s: s.abs(), ascending=False)
    y = np.arange(len(cortex))
    colors = ["#C44E52" if v > 0 else "#4C72B0" for v in cortex["side_ai"]]
    fig, ax = plt.subplots(figsize=(8.5, 10))
    ax.barh(y, cortex["side_ai"], color=colors, alpha=0.85)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels([_short_label(str(n)) for n in cortex["roi_name"]], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlim(-1, 1)
    ax.set_xlabel("side_ai = (L − R) / (L + R)")
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.grid(axis="x", alpha=0.25)
    return _save_fig(out_path)


def plot_absolute_asymmetry_top(
    ai: pd.DataFrame,
    out_path: Path,
    *,
    top_n: int = 15,
    title: str = "Top absolute strength asymmetry (all regions)",
) -> Path:
    """Largest |side_ai| across cortical and subcortical pairs."""
    df = ai.copy()
    df["abs_ai"] = df["side_ai"].abs()
    df = df.nlargest(top_n, "abs_ai").sort_values("abs_ai", ascending=True)
    colors = ["#C44E52" if v > 0 else "#4C72B0" for v in df["side_ai"]]
    y = np.arange(len(df))
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.barh(y, df["side_ai"], color=colors, alpha=0.85)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels([
        _short_label(f"{r.roi_name} ({r.region_type[:4]})")
        for r in df.itertuples()
    ], fontsize=8)
    ax.set_xlim(-1, 1)
    ax.set_xlabel("side_ai = (L − R) / (L + R)")
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.grid(axis="x", alpha=0.25)
    return _save_fig(out_path)


def plot_hub_strength_top(
    strength: pd.DataFrame,
    out_path: Path,
    *,
    top_n: int = 15,
) -> Path:
    """Highest node-strength regions (connectivity hubs)."""
    df = strength.copy()
    df = df.nlargest(top_n, "strength").sort_values("strength", ascending=True)
    y = np.arange(len(df))
    colors = ["#4C72B0" if s == "L" else "#DD8452" for s in df["side"]]
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.barh(y, df["strength"], color=colors, alpha=0.85)
    ax.set_yticks(y)
    ax.set_yticklabels([_short_label(str(n.name)) for n in df.itertuples()], fontsize=8)
    ax.set_xlabel("Node strength (SIFT2-weighted)")
    ax.set_title("Top connectivity hubs", fontsize=11, fontweight="bold")
    ax.grid(axis="x", alpha=0.25)
    return _save_fig(out_path)


def plot_subcortical_panel(
    strength: pd.DataFrame,
    ai: pd.DataFrame,
    out_path: Path,
) -> Path:
    """Subcortical strength L/R and asymmetry — ENIGMA-style panel."""
    df = _subcortical_vectors(strength, ai)
    x = np.arange(len(df))
    width = 0.35
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))

    ax0 = axes[0]
    ax0.bar(x - width / 2, df["L_strength"], width, label="Left", color="#4C72B0")
    ax0.bar(x + width / 2, df["R_strength"], width, label="Right", color="#DD8452")
    ax0.set_xticks(x)
    ax0.set_xticklabels([_short_label(n, 12) for n in df["roi_name"]], rotation=35, ha="right")
    ax0.set_ylabel("Node strength")
    ax0.set_title("Subcortical strength", fontweight="bold")
    ax0.legend(fontsize=8)
    ax0.grid(axis="y", alpha=0.25)

    ax1 = axes[1]
    colors = ["#C44E52" if v > 0 else "#4C72B0" for v in df["side_ai"]]
    ax1.bar(x, df["side_ai"], color=colors, alpha=0.85)
    ax1.axhline(0, color="black", linewidth=0.8)
    ax1.set_xticks(x)
    ax1.set_xticklabels([_short_label(n, 12) for n in df["roi_name"]], rotation=35, ha="right")
    ax1.set_ylim(-1, 1)
    ax1.set_ylabel("side_ai")
    ax1.set_title("Subcortical asymmetry", fontweight="bold")
    ax1.grid(axis="y", alpha=0.25)

    fig.suptitle("Subcortical structures (Desikan–Killiany)", fontsize=11, y=1.02)
    return _save_fig(out_path)


def plot_subcortical_intra_panel(
    strength_intra: pd.DataFrame,
    ai_intra: pd.DataFrame,
    out_path: Path,
) -> Path:
    """Subcortical intrahemispheric strength L/R and asymmetry."""
    df = _subcortical_vectors(strength_intra, ai_intra, value_col="strength_intra")
    x = np.arange(len(df))
    width = 0.35
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))

    ax0 = axes[0]
    ax0.bar(x - width / 2, df["L_strength"], width, label="Left", color="#4C72B0")
    ax0.bar(x + width / 2, df["R_strength"], width, label="Right", color="#DD8452")
    ax0.set_xticks(x)
    ax0.set_xticklabels([_short_label(n, 12) for n in df["roi_name"]], rotation=35, ha="right")
    ax0.set_ylabel("Intrahemispheric strength")
    ax0.set_title("Subcortical strength", fontweight="bold")
    ax0.legend(fontsize=8)
    ax0.grid(axis="y", alpha=0.25)

    ax1 = axes[1]
    colors = ["#C44E52" if v > 0 else "#4C72B0" for v in df["side_ai"]]
    ax1.bar(x, df["side_ai"], color=colors, alpha=0.85)
    ax1.axhline(0, color="black", linewidth=0.8)
    ax1.set_xticks(x)
    ax1.set_xticklabels([_short_label(n, 12) for n in df["roi_name"]], rotation=35, ha="right")
    ax1.set_ylim(-1, 1)
    ax1.set_ylabel("side_ai")
    ax1.set_title("Intrahemispheric asymmetry", fontweight="bold")
    ax1.grid(axis="y", alpha=0.25)

    fig.suptitle("Subcortical — intrahemispheric connections only", fontsize=11, y=1.02)
    return _save_fig(out_path)


def plot_standard_vs_intra_ai(
    strength_ai: pd.DataFrame,
    intra_ai: pd.DataFrame,
    out_path: Path,
) -> Path:
    """Compare all-edge vs intrahemispheric-only strength asymmetry."""
    merged = strength_ai.merge(
        intra_ai[["roi_name", "region_type", "side_ai"]],
        on=["roi_name", "region_type"],
        suffixes=("_all", "_intra"),
    )
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    palette = {"cortex": "#55A868", "subcortical": "#C44E52", "cerebellum": "#8172B3"}
    for rtype, grp in merged.groupby("region_type"):
        ax.scatter(
            grp["side_ai_all"],
            grp["side_ai_intra"],
            label=str(rtype),
            alpha=0.75,
            s=45,
            c=palette.get(str(rtype), "#333333"),
        )
    ax.axhline(0, color="grey", linewidth=0.6)
    ax.axvline(0, color="grey", linewidth=0.6)
    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.set_xlabel("Strength AI (all edges)")
    ax.set_ylabel("Strength AI (intrahemispheric only)")
    ax.set_title("Standard vs intrahemispheric asymmetry", fontweight="bold")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)

    for _, row in merged.iterrows():
        if row["roi_name"] in {"Thalamus-Proper", "Hippocampus", "Amygdala", "insula"}:
            ax.annotate(
                _short_label(str(row["roi_name"]), 10),
                (row["side_ai_all"], row["side_ai_intra"]),
                fontsize=6,
                alpha=0.9,
                xytext=(4, 4),
                textcoords="offset points",
            )
    return _save_fig(out_path)


def _seed_cortical_targets(W: np.ndarray, seed_index: int) -> pd.DataFrame:
    """Connectivity from one seed node to all cortical DK regions."""
    row = W[seed_index - 1]
    rows = []
    for i, name in enumerate(_CORTEX, start=1):
        rows.append({"region": name, "side": "L", "weight": float(row[i - 1])})
    for i, name in enumerate(_CORTEX, start=50):
        rows.append({"region": name, "side": "R", "weight": float(row[i - 1])})
    return pd.DataFrame(rows)


def plot_seed_profile(
    connectome_csv: Path,
    out_path: Path,
    seed_key: str,
    *,
    top_n: int = 12,
) -> Path:
    """Top cortical targets from L/R seed nodes (thalamus, hippocampus, amygdala)."""
    l_idx, r_idx = _SEED_INDICES[seed_key]
    W = load_connectome(connectome_csv)
    l_df = _seed_cortical_targets(W, l_idx)
    r_df = _seed_cortical_targets(W, r_idx)

    def _top(df: pd.DataFrame) -> pd.DataFrame:
        return df.nlargest(top_n, "weight").sort_values("weight")

    l_top = _top(l_df)
    r_top = _top(r_df)
    left_label = seed_key.capitalize()
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    axes[0].barh(range(len(l_top)), l_top["weight"], color="#4C72B0", alpha=0.85)
    axes[0].set_yticks(range(len(l_top)))
    axes[0].set_yticklabels(
        [_short_label(f"{r.region} ({r.side})") for r in l_top.itertuples()], fontsize=7)
    axes[0].invert_yaxis()
    axes[0].set_title(f"Left {left_label} → cortex", fontweight="bold")
    axes[0].set_xlabel("SIFT2 edge weight")
    axes[0].grid(axis="x", alpha=0.25)

    axes[1].barh(range(len(r_top)), r_top["weight"], color="#DD8452", alpha=0.85)
    axes[1].set_yticks(range(len(r_top)))
    axes[1].set_yticklabels(
        [_short_label(f"{r.region} ({r.side})") for r in r_top.itertuples()], fontsize=7)
    axes[1].invert_yaxis()
    axes[1].set_title(f"Right {left_label} → cortex", fontweight="bold")
    axes[1].set_xlabel("SIFT2 edge weight")
    axes[1].grid(axis="x", alpha=0.25)

    fig.suptitle(_SEED_TITLES[seed_key], fontsize=11, y=1.02)
    return _save_fig(out_path)


def plot_thalamus_seed_profile(connectome_csv: Path, out_path: Path, **kwargs) -> Path:
    return plot_seed_profile(connectome_csv, out_path, "thalamus", **kwargs)


def plot_homotopic_interhemispheric(
    connectome_csv: Path,
    out_path: Path,
    *,
    top_n: int = 15,
) -> Path:
    """Homotopic L↔R cortical edge weights (interhemispheric callosal proxies)."""
    W = load_connectome(connectome_csv)
    pairs = lr_pair_table()
    cortex_pairs = pairs.loc[pairs["region_type"] == "cortex"].copy()
    weights = []
    for row in cortex_pairs.itertuples():
        l_idx = int(row.L_index) - 1
        r_idx = int(row.R_index) - 1
        w = float(W[l_idx, r_idx])
        weights.append({"roi_name": row.roi_name, "weight": w})
    df = pd.DataFrame(weights).nlargest(top_n, "weight").sort_values("weight")
    y = np.arange(len(df))
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.barh(y, df["weight"], color="#8172B3", alpha=0.85)
    ax.set_yticks(y)
    ax.set_yticklabels([_short_label(str(n)) for n in df["roi_name"]], fontsize=8)
    ax.set_xlabel("SIFT2 edge weight (L ↔ R homotopic)")
    ax.set_title("Top homotopic interhemispheric edges", fontweight="bold")
    ax.grid(axis="x", alpha=0.25)
    return _save_fig(out_path)


def plot_fs_subcortical_volumes(
    fs_volumes: pd.DataFrame,
    out_path: Path,
) -> Path:
    """FreeSurfer subcortical volumes from aparc+aseg — ENIGMA-style anatomy panel."""
    df = fs_volumes.copy()
    x = np.arange(len(df))
    width = 0.35
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(x - width / 2, df["L_volume_mm3"], width, label="Left", color="#4C72B0")
    ax.bar(x + width / 2, df["R_volume_mm3"], width, label="Right", color="#DD8452")
    ax.set_xticks(x)
    ax.set_xticklabels([_short_label(n, 12) for n in df["roi_name"]], rotation=35, ha="right")
    ax.set_ylabel("Volume (mm³)")
    src = df["source"].iloc[0] if "source" in df.columns else "aparc+aseg"
    ax.set_title(f"FreeSurfer subcortical volumes ({src})", fontweight="bold")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    return _save_fig(out_path)


def plot_strength_vs_volume_scatter(
    strength_ai: pd.DataFrame,
    volume_ai: Optional[pd.DataFrame],
    out_path: Path,
) -> Optional[Path]:
    """Strength AI vs volume AI per ROI — divergence panel."""
    if volume_ai is None or volume_ai.empty:
        return None
    merged = strength_ai.merge(
        volume_ai[["roi_name", "region_type", "side_ai"]],
        on=["roi_name", "region_type"],
        suffixes=("_strength", "_volume"),
    )
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    palette = {"cortex": "#55A868", "subcortical": "#C44E52", "cerebellum": "#8172B3"}
    for rtype, grp in merged.groupby("region_type"):
        ax.scatter(
            grp["side_ai_strength"],
            grp["side_ai_volume"],
            label=str(rtype),
            alpha=0.75,
            s=45,
            c=palette.get(str(rtype), "#333333"),
        )
    ax.axhline(0, color="grey", linewidth=0.6)
    ax.axvline(0, color="grey", linewidth=0.6)
    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.set_xlabel("Strength side_ai")
    ax.set_ylabel("Volume side_ai")
    ax.set_title("Strength vs volume asymmetry", fontweight="bold")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)

    for _, row in merged.iterrows():
        if row["roi_name"] in {"Thalamus-Proper", "Hippocampus", "Amygdala", "insula"}:
            ax.annotate(
                _short_label(str(row["roi_name"]), 10),
                (row["side_ai_strength"], row["side_ai_volume"]),
                fontsize=6,
                alpha=0.9,
                xytext=(4, 4),
                textcoords="offset points",
            )
    return _save_fig(out_path)


def plot_connectome_heatmap(
    connectome_csv: Path,
    out_path: Path,
) -> Path:
    """Cortical 34×34 block heatmap (left hemisphere) from connectome."""
    W = load_connectome(connectome_csv)
    block = W[0:34, 0:34]
    labels = [_short_label(n, 10) for n in _CORTEX]
    fig, ax = plt.subplots(figsize=(9, 8))
    vmax = float(np.percentile(block[block > 0], 95)) if np.any(block > 0) else 1.0
    im = ax.imshow(block, cmap="Blues", vmin=0, vmax=max(vmax, 1e-6))
    ax.set_xticks(range(34))
    ax.set_yticks(range(34))
    ax.set_xticklabels(labels, rotation=90, fontsize=5)
    ax.set_yticklabels(labels, fontsize=5)
    ax.set_title("Left cortical connectome (34×34)", fontweight="bold")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="SIFT2 weight")
    return _save_fig(out_path)


def _dk_bilateral_cortical(values_by_region: List[float]) -> np.ndarray:
    """68-element DK cortical vector (LH then RH) for fsaverage5 parcellation."""
    return np.asarray(values_by_region + values_by_region, dtype=float)


def _parcel_to_fsa5_vertices(source_val: np.ndarray) -> np.ndarray:
    """Map Desikan–Killiany parcel values to fsaverage5 vertex arrays."""
    target_lab = np.loadtxt(_APARC_FSA5_PATH, dtype=int)
    source_val = np.asarray(source_val, dtype=float)
    if source_val.size == 68 and np.unique(target_lab).size == 71:
        a_idx = list(range(1, 4)) + list(range(5, 39)) + list(range(40, 71))
        ddk = np.zeros(71, dtype=float)
        ddk[a_idx] = source_val
        source_val = ddk
    _, idx_tl = np.unique(target_lab, return_inverse=True)
    return source_val[idx_tl]


def _subcortical_enigma_vector(values_by_side: List[float]) -> np.ndarray:
    """14-element subcortical vector (7 LH + 7 RH) for ENIGMA subcortical plots."""
    return np.asarray(values_by_side, dtype=float)


def _plot_cortical_surface_nilearn(
    vertex_data: np.ndarray,
    out_path: Path,
    *,
    title: str,
    cmap: str = "YlOrRd",
    symmetric: bool = False,
) -> Path:
    """Inflated fsaverage5 cortical map — ENIGMA-style four-panel layout."""
    from nilearn import datasets, plotting

    fs = datasets.fetch_surf_fsaverage(mesh="fsaverage5")
    lh = vertex_data[:_FSA5_VERTS_PER_HEMI]
    rh = vertex_data[_FSA5_VERTS_PER_HEMI:]
    fig, axes = plt.subplots(2, 2, figsize=(10, 8), subplot_kw={"projection": "3d"})
    panels = (
        (fs["infl_left"], lh, fs["sulc_left"], "left", "lateral", axes[0, 0], "Left lateral"),
        (fs["infl_left"], lh, fs["sulc_left"], "left", "medial", axes[0, 1], "Left medial"),
        (fs["infl_right"], rh, fs["sulc_right"], "right", "lateral", axes[1, 0], "Right lateral"),
        (fs["infl_right"], rh, fs["sulc_right"], "right", "medial", axes[1, 1], "Right medial"),
    )
    for mesh, data, bg, hemi, view, ax, subtitle in panels:
        plotting.plot_surf(
            mesh,
            surf_map=data,
            hemi=hemi,
            view=view,
            axes=ax,
            colorbar=False,
            bg_map=bg,
            bg_on_data=True,
            cmap=cmap,
            title=subtitle,
        )
    fig.suptitle(title, fontsize=11, fontweight="bold")
    return _save_fig(out_path)


def _ensure_enigma_matplotlib_compat() -> None:
    """ENIGMA Toolbox still calls matplotlib.cm.get_cmap (removed in matplotlib 3.9+)."""
    import matplotlib.cm as cm
    if hasattr(cm, "get_cmap"):
        return
    import matplotlib

    def _get_cmap(name: str, lut: int = 256):
        return matplotlib.colormaps[name].resampled(lut)

    cm.get_cmap = _get_cmap  # type: ignore[attr-defined]


def _try_enigma_subcortical_surface(
    values: np.ndarray,
    out_path: Path,
) -> bool:
    """Render subcortical 3D surface when ENIGMA Toolbox + compatible VTK are installed."""
    try:
        _ensure_enigma_matplotlib_compat()
        from enigmatoolbox.plotting import plot_subcortical
    except Exception as exc:
        logger.debug("ENIGMA subcortical import unavailable: %s", exc)
        return False
    if values.size != 14:
        return False
    try:
        plot_subcortical(
            array_name=values,
            ventricles=False,
            size=(800, 400),
            interactive=False,
            screenshot=True,
        )
        plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close()
        return out_path.is_file() and out_path.stat().st_size > 1000
    except Exception as exc:
        logger.debug("ENIGMA subcortical surface unavailable: %s", exc)
        plt.close("all")
        return False


def _plot_cortical_abs_ai_surface(ai: pd.DataFrame, fig_dir: Path) -> Optional[Path]:
    """Inflated cortical surface map of |side AI| (nilearn + fsaverage5)."""
    ai_ctx = ai.loc[ai["region_type"] == "cortex"]
    try:
        abs_vals = []
        for n in _CORTEX:
            rows = ai_ctx.loc[ai_ctx["roi_name"] == n]
            abs_vals.append(float(rows.iloc[0]["side_ai"]) if len(rows) else 0.0)
        abs_vals = [abs(v) for v in abs_vals]
        abs_vert = _parcel_to_fsa5_vertices(_dk_bilateral_cortical(abs_vals))
        out = fig_dir / "enigma_cortical_abs_ai.png"
        return _plot_cortical_surface_nilearn(
            abs_vert,
            out,
            title="Cortical strength asymmetry (|side AI|)",
            cmap="YlOrRd",
        )
    except Exception as exc:
        logger.warning("Cortical surface map failed: %s", exc)
        plt.close("all")
        return None


def _try_brain_surface_maps(
    strength: pd.DataFrame,
    ai: pd.DataFrame,
    fig_dir: Path,
    fs_volumes: Optional[pd.DataFrame] = None,
) -> List[Path]:
    """ENIGMA-style 3D brain surfaces (research / extended figure set)."""
    saved: List[Path] = []
    cortical = _plot_cortical_abs_ai_surface(ai, fig_dir)
    if cortical is not None:
        saved.append(cortical)

    sctx_strength = _subcortical_enigma_vector([
        float(strength.loc[strength["name"] == f"{side}.{name}", "strength"].iloc[0])
        for side in ("L", "R")
        for name in _ENIGMA_SCTX_NAMES
    ])
    out = fig_dir / "enigma_subcortical_strength.png"
    if _try_enigma_subcortical_surface(sctx_strength, out):
        saved.append(out)

    if fs_volumes is not None:
        fs_vals = _subcortical_enigma_vector([
            float(fs_volumes.loc[fs_volumes["roi_name"] == name, f"{side}_volume_mm3"].iloc[0])
            if len(fs_volumes.loc[fs_volumes["roi_name"] == name])
            else 0.0
            for side in ("L", "R")
            for name in _ENIGMA_SCTX_NAMES
        ])
        out = fig_dir / "enigma_fs_subcortical_volume.png"
        if _try_enigma_subcortical_surface(fs_vals, out):
            saved.append(out)

    return saved


def _append_figure(paths: List[Path], result: Optional[Path]) -> None:
    if result is not None and result.is_file():
        paths.append(result)


def _fs_lookup_dir(
    subject_dir: Optional[Path],
    fs_subject_dir: Optional[Path],
) -> Optional[Path]:
    if fs_subject_dir is not None and fs_subject_dir.is_dir():
        return fs_subject_dir
    if subject_dir is not None and subject_dir.is_dir():
        return subject_dir
    return None


def generate_all_subject_figures(
    results_dir: Path,
    folder_name: str,
    *,
    connectome_csv: Optional[Path] = None,
    subject_dir: Optional[Path] = None,
    fs_subject_dir: Optional[Path] = None,
    use_enigma_surfaces: bool = True,
) -> List[Path]:
    """Build the full PNG figure set for one subject under ``reports/<subject>/figures/``."""
    prefix = subject_file_prefix(folder_name)
    fig_dir = results_dir / "reports" / prefix / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    for stale in fig_dir.glob("*.png"):
        stale.unlink(missing_ok=True)

    strength = _load_strength(results_dir, prefix)
    strength_ai = _load_strength_ai(results_dir, prefix)
    volume_ai = _load_volume_ai(results_dir, prefix)
    strength_intra = _load_strength_intra(results_dir, prefix)
    intra_ai = _load_intra_ai(results_dir, prefix)

    paths: List[Path] = []
    paths.append(plot_subcortical_panel(strength, strength_ai, fig_dir / "subcortical_panel.png"))

    if strength_intra is not None and intra_ai is not None:
        paths.append(plot_subcortical_intra_panel(
            strength_intra, intra_ai, fig_dir / "subcortical_intra_panel.png"))
        paths.append(plot_standard_vs_intra_ai(
            strength_ai, intra_ai, fig_dir / "standard_vs_intra_ai.png"))

    paths.append(plot_hub_strength_top(strength, fig_dir / "hub_strength_top.png"))

    if use_enigma_surfaces:
        cortical = _plot_cortical_abs_ai_surface(strength_ai, fig_dir)
        if cortical is not None:
            paths.append(cortical)

    if not (fig_dir / "enigma_cortical_abs_ai.png").is_file():
        paths.append(plot_absolute_asymmetry_top(
            strength_ai, fig_dir / "absolute_asymmetry_top.png"))

    fs_volumes: Optional[pd.DataFrame] = None
    fs_dir = _fs_lookup_dir(subject_dir, fs_subject_dir)
    if fs_dir is not None:
        aparc = find_aparc_seg(fs_dir)
        if aparc is not None:
            try:
                fs_volumes = fs_subcortical_volumes_mm3(aparc)
                paths.append(plot_fs_subcortical_volumes(
                    fs_volumes, fig_dir / "fs_subcortical_volumes.png"))
            except Exception as exc:
                logger.warning("FreeSurfer subcortical volume plot failed: %s", exc)
                plt.close("all")

    if use_enigma_surfaces:
        for extra in _try_brain_surface_maps(strength, strength_ai, fig_dir, fs_volumes):
            if extra.is_file() and extra not in paths:
                paths.append(extra)

    if volume_ai is not None:
        _append_figure(
            paths,
            plot_strength_vs_volume_scatter(
                strength_ai, volume_ai, fig_dir / "strength_vs_volume_ai.png"),
        )

    if connectome_csv is not None and connectome_csv.is_file():
        for seed_key in _SEED_INDICES:
            try:
                paths.append(plot_seed_profile(
                    connectome_csv, fig_dir / f"{seed_key}_seed_profile.png", seed_key))
            except Exception as exc:
                logger.warning("%s seed profile failed: %s", seed_key, exc)
                plt.close("all")
        try:
            paths.append(plot_homotopic_interhemispheric(
                connectome_csv, fig_dir / "homotopic_interhemispheric.png"))
        except Exception as exc:
            logger.warning("Homotopic plot failed: %s", exc)
            plt.close("all")
        try:
            paths.append(plot_connectome_heatmap(
                connectome_csv, fig_dir / "connectome_heatmap.png"))
        except Exception as exc:
            logger.warning("Connectome heatmap failed: %s", exc)
            plt.close("all")

    return paths


def generate_report_figures(
    results_dir: Path,
    folder_name: str,
    *,
    connectome_csv: Optional[Path] = None,
    subject_dir: Optional[Path] = None,
    fs_subject_dir: Optional[Path] = None,
    use_enigma_surfaces: bool = True,
) -> List[Path]:
    """Build all report PNG figures (full set written to ``reports/<subject>/figures/``)."""
    return generate_all_subject_figures(
        results_dir,
        folder_name,
        connectome_csv=connectome_csv,
        subject_dir=subject_dir,
        fs_subject_dir=fs_subject_dir,
        use_enigma_surfaces=use_enigma_surfaces,
    )
