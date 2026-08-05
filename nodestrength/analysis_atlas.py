"""Resolve analysis atlas from connectome size (78-node DKT or 84-node DK legacy)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Tuple

import numpy as np
import pandas as pd

from nodestrength import dkt_atlas, dk_atlas
from nodestrength.connectome import load_connectome

_DKT_N = dkt_atlas._DKT_N_NODES
_DK_N = 84


@dataclass(frozen=True)
class AnalysisAtlas:
    scheme: str
    atlas: str
    n_nodes: int
    build_nodes: Callable[[], list]
    lr_pair_table: Callable[[], pd.DataFrame]
    seed_indices: Dict[str, Tuple[int, int]]
    left_cortex_indices: Callable[[], List[Tuple[int, str]]]
    right_cortex_indices: Callable[[], List[Tuple[int, str]]]
    compute_volumes_mm3: Callable[[str | Path], np.ndarray]
    index_attr: str = "index"

    def sides(self) -> np.ndarray:
        return np.array([n.side for n in self.build_nodes()])


DKT_ATLAS = AnalysisAtlas(
    scheme="dkt",
    atlas="fs_dkt",
    n_nodes=_DKT_N,
    build_nodes=dkt_atlas.build_dkt_nodes,
    lr_pair_table=dkt_atlas.lr_pair_table,
    seed_indices=dkt_atlas.seed_indices(),
    left_cortex_indices=dkt_atlas.left_cortex_indices,
    right_cortex_indices=dkt_atlas.right_cortex_indices,
    compute_volumes_mm3=dkt_atlas.compute_dkt_volumes_mm3,
    index_attr="index",
)

DK_LEGACY_ATLAS = AnalysisAtlas(
    scheme="dk",
    atlas="fs_default",
    n_nodes=_DK_N,
    build_nodes=dk_atlas.build_dk_nodes,
    lr_pair_table=dk_atlas.lr_pair_table,
    seed_indices={
        "thalamus": (36, 43),
        "hippocampus": (40, 47),
        "amygdala": (41, 48),
    },
    left_cortex_indices=lambda: [(i, n) for i, n in enumerate(dk_atlas._CORTEX, start=1)],
    right_cortex_indices=lambda: [(i, n) for i, n in enumerate(dk_atlas._CORTEX, start=50)],
    compute_volumes_mm3=dk_atlas.compute_dk_volumes_mm3,
    index_attr="fs_default_index",
)


def resolve_analysis_atlas(n_nodes: int) -> AnalysisAtlas:
    if n_nodes == _DKT_N:
        return DKT_ATLAS
    if n_nodes == _DK_N:
        return DK_LEGACY_ATLAS
    raise ValueError(
        f"Unsupported connectome size {n_nodes}×{n_nodes}; "
        f"expected {_DKT_N} (fs_dkt / dkt_connectome.csv) or {_DK_N} (fs_default / dk_connectome.csv)"
    )


def atlas_for_connectome(path: str | Path) -> AnalysisAtlas:
    W = load_connectome(path)
    return resolve_analysis_atlas(W.shape[0])


def node_index(node) -> int:
    """1-based atlas index from a DktNode or DkNode."""
    return getattr(node, "index", None) or node.fs_default_index
