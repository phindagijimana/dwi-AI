"""MRtrix3 fs_default Desikan–Killiany 84-node ordering.

When a connectome is built via the standard

    labelconvert  aparc+aseg.nii.gz  FreeSurferColorLUT.txt  fs_default.txt  dk_nodes.mif

the resulting label image carries the 1..84 node IDs in this fixed order. The
``fs_default.txt`` file ships with MRtrix3; this module encodes its content so
DK connectomes can be parsed without a copy of MRtrix3 on PATH.

Layout (84 rows):

    1..34   ctx-lh-<region>    (Desikan–Killiany cortical, alphabetical)
    35..41  Left subcortical   (Thalamus-Proper, Caudate, Putamen, Pallidum,
                                Hippocampus, Amygdala, Accumbens-area)
    42      Brain-Stem
    43..76  ctx-rh-<region>    (same cortical ordering as lh)
    77..83  Right subcortical  (same ordering as left)
    84      reserved / cerebellum-related slot in some releases

Use :func:`build_node_lookup` to get a ``pd.DataFrame`` whose ``name`` column
follows nodestrength's canonical L./R. convention (so the same connectome
loader works for DK and Lausanne+THOMAS data).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import pandas as pd


_CORTEX = (
    "bankssts",
    "caudalanteriorcingulate",
    "caudalmiddlefrontal",
    "cuneus",
    "entorhinal",
    "fusiform",
    "inferiorparietal",
    "inferiortemporal",
    "isthmuscingulate",
    "lateraloccipital",
    "lateralorbitofrontal",
    "lingual",
    "medialorbitofrontal",
    "middletemporal",
    "parahippocampal",
    "paracentral",
    "parsopercularis",
    "parsorbitalis",
    "parstriangularis",
    "pericalcarine",
    "postcentral",
    "posteriorcingulate",
    "precentral",
    "precuneus",
    "rostralanteriorcingulate",
    "rostralmiddlefrontal",
    "superiorfrontal",
    "superiorparietal",
    "superiortemporal",
    "supramarginal",
    "frontalpole",
    "temporalpole",
    "transversetemporal",
    "insula",
)
assert len(_CORTEX) == 34

_SUBCORTICAL = (
    "Thalamus-Proper",
    "Caudate",
    "Putamen",
    "Pallidum",
    "Hippocampus",
    "Amygdala",
    "Accumbens-area",
)
assert len(_SUBCORTICAL) == 7


@dataclass(frozen=True)
class DkNode:
    fs_default_index: int        # 1..84 — MRtrix3 fs_default.txt row
    name: str                    # canonical L.<roi> / R.<roi> / unpaired
    side: str                    # "L", "R", or ""
    region_type: str             # "cortex" / "subcortical" / "brainstem" / "reserved"


def build_dk_nodes() -> List[DkNode]:
    """Return all 84 DK nodes in fs_default order."""
    nodes: List[DkNode] = []
    idx = 1
    # 1..34 -- left cortex
    for name in _CORTEX:
        nodes.append(DkNode(fs_default_index=idx, name=f"L.{name}",
                            side="L", region_type="cortex"))
        idx += 1
    # 35..41 -- left subcortical
    for name in _SUBCORTICAL:
        nodes.append(DkNode(fs_default_index=idx, name=f"L.{name}",
                            side="L", region_type="subcortical"))
        idx += 1
    # 42 -- Brain-Stem
    nodes.append(DkNode(fs_default_index=idx, name="Brain-Stem",
                        side="", region_type="brainstem"))
    idx += 1
    # 43..76 -- right cortex
    for name in _CORTEX:
        nodes.append(DkNode(fs_default_index=idx, name=f"R.{name}",
                            side="R", region_type="cortex"))
        idx += 1
    # 77..83 -- right subcortical
    for name in _SUBCORTICAL:
        nodes.append(DkNode(fs_default_index=idx, name=f"R.{name}",
                            side="R", region_type="subcortical"))
        idx += 1
    # 84 -- reserved (cerebellum / unused depending on MRtrix3 release).
    # Treat as unpaired; AI computation skips it.
    nodes.append(DkNode(fs_default_index=idx, name="unassigned-84",
                        side="", region_type="reserved"))
    assert len(nodes) == 84, len(nodes)
    return nodes


def build_node_lookup() -> pd.DataFrame:
    """A ``pd.DataFrame`` shaped like the lookups in :mod:`nodestrength.connectome`."""
    nodes = build_dk_nodes()
    return pd.DataFrame([
        {"index": n.fs_default_index, "name": n.name,
         "side": n.side, "region_type": n.region_type}
        for n in nodes
    ])


def lr_pair_table() -> pd.DataFrame:
    """Return one row per matched L/R DK ROI (41 pairs).

    Columns: ``roi_name``, ``L_index``, ``R_index``, ``region_type``.
    Used for asymmetry-index computation downstream.
    """
    nodes = build_dk_nodes()
    by_side_name: dict[Tuple[str, str], DkNode] = {}
    for n in nodes:
        if n.side in ("L", "R"):
            base = n.name.split(".", 1)[1]
            by_side_name[(n.side, base)] = n

    rows = []
    bases = sorted({k[1] for k in by_side_name})
    for base in bases:
        l = by_side_name.get(("L", base))
        r = by_side_name.get(("R", base))
        if l and r:
            rows.append({
                "roi_name": base,
                "L_index": l.fs_default_index,
                "R_index": r.fs_default_index,
                "region_type": l.region_type,
            })
    return pd.DataFrame(rows)
