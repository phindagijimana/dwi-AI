"""Lock in the DK / fs_default ordering verified against MRtrix3 v3.0.4.

These tests freeze the ordering empirically verified by
``scripts/verify_dk_labels.py`` on the Gugger_Lab dwi_test2 cohort. Any
future change to ``build_dk_nodes`` that breaks the verified pairings
will fail loudly here.
"""

from __future__ import annotations

import pandas as pd
import pytest

from nodestrength.dk_atlas import (
    DkNode,
    build_dk_nodes,
    build_node_lookup,
    lr_pair_table,
)


def test_total_node_count():
    assert len(build_dk_nodes()) == 84


def test_no_brain_stem_node():
    """labelconvert drops Brain-Stem (FreeSurfer 16). Make sure we agree."""
    names = [n.name for n in build_dk_nodes()]
    assert "Brain-Stem" not in names


@pytest.mark.parametrize("fs_default_index,expected_name", [
    (1,  "L.bankssts"),
    (7,  "L.inferiorparietal"),
    (35, "L.Cerebellum-Cortex"),
    (36, "L.Thalamus-Proper"),
    (42, "L.Accumbens-area"),
    (43, "R.Thalamus-Proper"),
    (49, "R.Accumbens-area"),
    (50, "R.bankssts"),
    (56, "R.inferiorparietal"),
    (83, "R.insula"),
    (84, "R.Cerebellum-Cortex"),
])
def test_specific_node_index_assignments(fs_default_index, expected_name):
    """Lock in indices that were empirically verified against the real dk_nodes.mif."""
    nodes = build_dk_nodes()
    by_idx = {n.fs_default_index: n.name for n in nodes}
    assert by_idx[fs_default_index] == expected_name


def test_lr_pair_table_has_42_pairs():
    """34 cortical + 7 subcortical + 1 cerebellum = 42 L/R pairs."""
    pairs = lr_pair_table()
    assert len(pairs) == 42


@pytest.mark.parametrize("roi_name,L_index,R_index", [
    # cortical: L index k maps to R index k+49
    ("inferiorparietal",    7, 56),
    ("precentral",         23, 72),
    ("transversetemporal", 33, 82),
    # subcortical: L index k maps to R index k+7
    ("Thalamus-Proper", 36, 43),
    ("Accumbens-area",  42, 49),
    # cerebellum
    ("Cerebellum-Cortex", 35, 84),
])
def test_lr_pair_specific_indices(roi_name, L_index, R_index):
    pairs = lr_pair_table().set_index("roi_name")
    assert int(pairs.loc[roi_name, "L_index"]) == L_index
    assert int(pairs.loc[roi_name, "R_index"]) == R_index


def test_build_node_lookup_compatible_with_connectome_loader():
    """The lookup df must match the ``index, name`` schema connectome.py expects."""
    lut = build_node_lookup()
    assert set(lut.columns) >= {"index", "name"}
    assert lut["index"].min() == 1 and lut["index"].max() == 84
    assert len(lut) == 84
