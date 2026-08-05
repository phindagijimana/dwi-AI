"""Lock in the 78-node fs_dkt ordering used by dwi_pipeline Step 4."""

from __future__ import annotations

import numpy as np
import pytest

from nodestrength.analysis_atlas import DKT_ATLAS, resolve_analysis_atlas
from nodestrength.asymmetry import side_ai
from nodestrength.connectome import dk_intrahemispheric_edge_mask
from nodestrength.dkt_atlas import (
    build_dkt_nodes,
    dkt_volumes_from_label_data,
    lr_pair_table,
    seed_indices,
)


def test_dkt_node_count():
    assert len(build_dkt_nodes()) == 78
    assert resolve_analysis_atlas(78) is DKT_ATLAS


def test_dkt_excluded_regions_absent():
    names = [n.name for n in build_dkt_nodes()]
    for bad in ("L.bankssts", "R.bankssts", "L.frontalpole", "R.temporalpole"):
        assert bad not in names


@pytest.mark.parametrize("index,expected_name", [
    (1, "L.caudalanteriorcingulate"),
    (5, "L.fusiform"),
    (32, "L.Cerebellum-Cortex"),
    (33, "L.Thalamus-Proper"),
    (40, "R.Thalamus-Proper"),
    (51, "R.fusiform"),
    (78, "R.Cerebellum-Cortex"),
])
def test_dkt_specific_indices(index, expected_name):
    by_idx = {n.index: n.name for n in build_dkt_nodes()}
    assert by_idx[index] == expected_name


def test_dkt_lr_pairs():
    pairs = lr_pair_table()
    assert len(pairs) == 39  # 31 cortical + 7 subcortical + 1 cerebellum
    row = pairs.set_index("roi_name").loc["fusiform"]
    assert int(row["L_index"]) == 5
    assert int(row["R_index"]) == 51


def test_dkt_seed_indices():
    assert seed_indices()["thalamus"] == (33, 40)


def test_intrahemispheric_mask_78():
    mask = dk_intrahemispheric_edge_mask(78)
    assert mask.shape == (78, 78)
    assert not mask.diagonal().any()


def test_dkt_volume_ai_formula():
    vols = np.zeros(78)
    vols[31] = 1000.0   # L cerebellum index 32
    vols[77] = 800.0    # R cerebellum index 78
    pairs = lr_pair_table().set_index("roi_name")
    row = pairs.loc["Cerebellum-Cortex"]
    L = vols[int(row["L_index"]) - 1]
    R = vols[int(row["R_index"]) - 1]
    assert side_ai(L, R) == pytest.approx((L - R) / (L + R))


def test_dkt_volumes_from_label_data():
    data = np.zeros((2, 2, 2), dtype=np.uint8)
    data[0, 0, 0] = 33
    vols = dkt_volumes_from_label_data(data, voxel_volume_mm3=2.0)
    assert vols.shape == (78,)
    assert vols[32] == 2.0
