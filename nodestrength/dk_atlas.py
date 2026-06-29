"""MRtrix3 fs_default Desikan–Killiany 84-node ordering.

When a connectome is built via the standard

    labelconvert  aparc+aseg.nii.gz  FreeSurferColorLUT.txt  fs_default.txt  dk_nodes.mif

the resulting label image carries the 1..84 node IDs in this fixed order. This
module encodes the ordering empirically verified against
``MRtrix3 v3.0.4 fs_default.txt`` by overlaying a real ``dk_nodes.mif`` on
its source ``aparc+aseg`` (see ``scripts/verify_dk_labels.py``).

Layout (84 rows):

    1..34    ctx-lh-<region>           (Desikan–Killiany cortical, alphabetical)
    35       Left-Cerebellum-Cortex
    36..42   Left subcortical          (Thalamus-Proper, Caudate, Putamen,
                                        Pallidum, Hippocampus, Amygdala,
                                        Accumbens-area)
    43..49   Right subcortical         (same ordering as left)
    50..83   ctx-rh-<region>           (same cortical ordering as lh)
    84       Right-Cerebellum-Cortex

Note: ``Brain-Stem`` (FreeSurfer label 16) is **not** present in the
84 nodes — labelconvert drops it. Earlier nodestrength releases assumed
Brain-Stem at index 42; that assumption was wrong and produced
mis-paired L/R asymmetry indices for every cortical region. The current
ordering pairs L cortex node ``k`` (1..34) with R cortex node ``k + 49``
(50..83), and L subcortical ``k`` (36..42) with R subcortical ``k + 7``
(43..49).

Use :func:`build_node_lookup` to get a ``pd.DataFrame`` whose ``name``
column follows nodestrength's canonical ``L.<roi>`` / ``R.<roi>``
convention so the same connectome loader works for DK and Lausanne+THOMAS
data.
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
    region_type: str             # "cortex" / "subcortical" / "cerebellum"


def build_dk_nodes() -> List[DkNode]:
    """Return all 84 DK nodes in fs_default order (empirically verified).

    Cross-check on two real subjects (sub-001 and sub-TBI011011 from the
    Gugger_Lab dwi_test2 cohort) showed full agreement with this ordering.
    """
    nodes: List[DkNode] = []
    idx = 1
    # 1..34 -- left cortex
    for name in _CORTEX:
        nodes.append(DkNode(fs_default_index=idx, name=f"L.{name}",
                            side="L", region_type="cortex"))
        idx += 1
    # 35 -- left cerebellum cortex
    nodes.append(DkNode(fs_default_index=idx, name="L.Cerebellum-Cortex",
                        side="L", region_type="cerebellum"))
    idx += 1
    # 36..42 -- left subcortical
    for name in _SUBCORTICAL:
        nodes.append(DkNode(fs_default_index=idx, name=f"L.{name}",
                            side="L", region_type="subcortical"))
        idx += 1
    # 43..49 -- right subcortical
    for name in _SUBCORTICAL:
        nodes.append(DkNode(fs_default_index=idx, name=f"R.{name}",
                            side="R", region_type="subcortical"))
        idx += 1
    # 50..83 -- right cortex
    for name in _CORTEX:
        nodes.append(DkNode(fs_default_index=idx, name=f"R.{name}",
                            side="R", region_type="cortex"))
        idx += 1
    # 84 -- right cerebellum cortex
    nodes.append(DkNode(fs_default_index=idx, name="R.Cerebellum-Cortex",
                        side="R", region_type="cerebellum"))
    idx += 1
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
