"""Parcellation roles: DKT for connectome analysis, DK for ENIGMA visualization.

Analysis (DKT)
--------------
Per-subject connectomes are read from ``dkt_connectome.csv`` (legacy names
``dk_connectome.csv``, ``connectome.csv`` still accepted). The default
78×78 matrix follows MRtrix3 ``fs_dkt`` (Desikan–Killiany–Tourville). Legacy
84×84 ``fs_default`` connectomes are still accepted (see ``nodestrength.analysis_atlas``).

Visualization (DK / ENIGMA)
---------------------------
Report figures map the same ROI *names* onto standard FreeSurfer Desikan–Killiany
**aparc** on fsaverage5 (``data/parcellations/aparc_fsa5.csv``) and ENIGMA
Toolbox subcortical surfaces. When analysis and ENIGMA layouts diverge in the
future, mapping functions in ``nodestrength.report_viz`` remain the single
DK-side adapter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

# --- Analysis: DKT connectome / fs_dkt grid (78 nodes; 84 legacy) ---------------

ANALYSIS_SCHEME = "dkt"
ANALYSIS_ATLAS = "fs_dkt"
ANALYSIS_N_NODES = 78

ANALYSIS_CONNECTOME_FILENAMES: Tuple[str, ...] = (
    "dkt_connectome.csv",
    "dk_connectome.csv",  # legacy fs_default 84-node export
    "connectome.csv",
)

ANALYSIS_LABEL_MIF_NAMES: Tuple[str, ...] = ("nodes.mif", "dk_nodes.mif")
ANALYSIS_LABEL_MIF = ANALYSIS_LABEL_MIF_NAMES[0]

# --- Visualization: FreeSurfer DK aparc + ENIGMA surfaces ---------------------

VIZ_SCHEME = "dk"
VIZ_CORTICAL_PARCELLATION = "aparc_fsa5"
VIZ_SURFACE = "fsaverage5"
VIZ_FSA5_VERTS_PER_HEMI = 10242

APARC_FSA5_PATH = (
    Path(__file__).resolve().parent / "data" / "parcellations" / "aparc_fsa5.csv"
)

# ENIGMA subcortical viewer order (L then R; ventricles omitted).
DK_ENIGMA_SUBCORTICAL_ORDER: Tuple[str, ...] = (
    "Accumbens-area",
    "Amygdala",
    "Caudate",
    "Hippocampus",
    "Pallidum",
    "Putamen",
    "Thalamus-Proper",
)


def analysis_manifest_fields() -> dict[str, str | int]:
    """Standard manifest keys for cohort outputs."""
    return {
        "analysis_scheme": ANALYSIS_SCHEME,
        "analysis_atlas": ANALYSIS_ATLAS,
        "analysis_n_nodes": ANALYSIS_N_NODES,
        "viz_scheme": VIZ_SCHEME,
        "viz_cortical_parcellation": VIZ_CORTICAL_PARCELLATION,
        "viz_surface": VIZ_SURFACE,
    }
