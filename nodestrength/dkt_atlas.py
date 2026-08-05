"""MRtrix3 fs_dkt Desikan–Killiany–Tourville 78-node ordering.

The dwi_pipeline Step 4 connectome uses ``fs_dkt.txt``: fs_default with
bankssts, frontal pole and temporal pole removed bilaterally, renumbered
contiguously (see ``dwi_pipeline/containers/connectome/mrtrix_lut/fs_dkt.txt``).

Layout (78 rows):

    1..31    ctx-lh-<region>           (31 cortical; DKT protocol)
    32       Left-Cerebellum-Cortex
    33..39   Left subcortical
    40..46   Right subcortical
    47..77   ctx-rh-<region>
    78       Right-Cerebellum-Cortex

L/R pairings: L cortex ``k`` (1..31) ↔ R cortex ``k+46`` (47..77);
L subcortical ``k`` (33..39) ↔ R subcortical ``k+7`` (40..46);
L cerebellum 32 ↔ R cerebellum 78.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from nodestrength.dk_atlas import _CORTEX, _SUBCORTICAL

_DKT_EXCLUDED = frozenset({"bankssts", "frontalpole", "temporalpole"})
_DKT_CORTEX = tuple(n for n in _CORTEX if n not in _DKT_EXCLUDED)
assert len(_DKT_CORTEX) == 31

_DKT_N_NODES = 78


@dataclass(frozen=True)
class DktNode:
    index: int                   # 1..78 — MRtrix3 fs_dkt.txt row
    name: str                    # canonical L.<roi> / R.<roi>
    side: str                    # "L", "R", or ""
    region_type: str             # "cortex" / "subcortical" / "cerebellum"


def build_dkt_nodes() -> List[DktNode]:
    """Return all 78 DKT nodes in fs_dkt order."""
    nodes: List[DktNode] = []
    idx = 1
    for name in _DKT_CORTEX:
        nodes.append(DktNode(index=idx, name=f"L.{name}", side="L", region_type="cortex"))
        idx += 1
    nodes.append(DktNode(index=idx, name="L.Cerebellum-Cortex",
                         side="L", region_type="cerebellum"))
    idx += 1
    for name in _SUBCORTICAL:
        nodes.append(DktNode(index=idx, name=f"L.{name}", side="L", region_type="subcortical"))
        idx += 1
    for name in _SUBCORTICAL:
        nodes.append(DktNode(index=idx, name=f"R.{name}", side="R", region_type="subcortical"))
        idx += 1
    for name in _DKT_CORTEX:
        nodes.append(DktNode(index=idx, name=f"R.{name}", side="R", region_type="cortex"))
        idx += 1
    nodes.append(DktNode(index=idx, name="R.Cerebellum-Cortex",
                         side="R", region_type="cerebellum"))
    idx += 1
    assert len(nodes) == _DKT_N_NODES, len(nodes)
    return nodes


def build_node_lookup() -> pd.DataFrame:
    nodes = build_dkt_nodes()
    return pd.DataFrame([
        {"index": n.index, "name": n.name, "side": n.side, "region_type": n.region_type}
        for n in nodes
    ])


def dkt_volumes_from_label_data(data: np.ndarray, voxel_volume_mm3: float) -> np.ndarray:
    """Per-node volume (mm³) from a DKT label array with values 1..78."""
    flat = np.asarray(data).ravel()
    counts = np.array([(flat == label).sum() for label in range(1, _DKT_N_NODES + 1)],
                      dtype=float)
    return counts * float(voxel_volume_mm3)


def compute_dkt_volumes_mm3(label_mif_path: str | Path) -> np.ndarray:
    """Load ``nodes.mif`` / ``dk_nodes.mif`` and return length-78 volumes in mm³."""
    from nodestrength.mif import read_mif

    img = read_mif(Path(label_mif_path))
    voxel_volume = float(np.abs(np.prod(img.vox[:3])))
    return dkt_volumes_from_label_data(np.asarray(img.data), voxel_volume)


def lr_pair_table() -> pd.DataFrame:
    """One row per matched L/R DKT ROI (31 cortical + 7 subcortical + 1 cerebellum = 39)."""
    nodes = build_dkt_nodes()
    by_side_name: dict[Tuple[str, str], DktNode] = {}
    for n in nodes:
        if n.side in ("L", "R"):
            base = n.name.split(".", 1)[1]
            by_side_name[(n.side, base)] = n

    rows = []
    for base in sorted({k[1] for k in by_side_name}):
        left = by_side_name.get(("L", base))
        right = by_side_name.get(("R", base))
        if left and right:
            rows.append({
                "roi_name": base,
                "L_index": left.index,
                "R_index": right.index,
                "region_type": left.region_type,
            })
    return pd.DataFrame(rows)


def seed_indices() -> Dict[str, Tuple[int, int]]:
    """L/R 1-based node indices for thalamus, hippocampus, amygdala."""
    return {
        "thalamus": (33, 40),
        "hippocampus": (37, 44),
        "amygdala": (38, 45),
    }


def left_cortex_indices() -> List[Tuple[int, str]]:
    """(1-based index, region name) for left cortical nodes in fs_dkt order."""
    return [
        (n.index, n.name.split(".", 1)[1])
        for n in build_dkt_nodes()
        if n.region_type == "cortex" and n.side == "L"
    ]


def right_cortex_indices() -> List[Tuple[int, str]]:
    return [
        (n.index, n.name.split(".", 1)[1])
        for n in build_dkt_nodes()
        if n.region_type == "cortex" and n.side == "R"
    ]
