"""Tests for DKT vs DK parcellation roles."""

from __future__ import annotations

from nodestrength import parcellations as p
from nodestrength.dk_inputs import CONNECTOME_FILENAMES
from nodestrength.report_viz import map_dkt_cortical_to_dk_fsa5_vertices


def test_analysis_prefers_dkt_connectome_name():
    assert CONNECTOME_FILENAMES[0] == "dkt_connectome.csv"
    assert p.ANALYSIS_SCHEME == "dkt"
    assert p.VIZ_SCHEME == "dk"


def test_manifest_fields():
    fields = p.analysis_manifest_fields()
    assert fields["analysis_scheme"] == "dkt"
    assert fields["viz_cortical_parcellation"] == "aparc_fsa5"
    assert fields["analysis_n_nodes"] == 78


def test_dkt_to_dk_fsa5_mapping_shape():
    vals = [float(i) for i in range(34)]
    vert = map_dkt_cortical_to_dk_fsa5_vertices(vals)
    assert vert.shape == (p.VIZ_FSA5_VERTS_PER_HEMI * 2,)
