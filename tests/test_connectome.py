"""Connectome strength / volume tests on hand-checkable synthetic data."""

from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
import pytest

from nodestrength import atlases
from nodestrength.atlases import ANALYZED_NUCLEI, LEFT_LABELS, ThalamicROI
from nodestrength.connectome import (
    StrengthConfig,
    compute_nucleus_strength,
    compute_nucleus_volume_mm3,
    dk_intrahemispheric_edge_mask,
    dk_interhemispheric_edge_mask,
    interhemispheric_strengths_und,
    intrahemispheric_strengths_und,
    load_connectome,
    load_node_lookup,
    mean_brain_strength,
    per_subject_record,
)
from nodestrength.dk_atlas import build_dk_nodes


def test_strength_matches_manual_sum(tiny_connectome, tiny_lookup):
    cfg = StrengthConfig(exclude_self=True, exclude_inter_thalamic=False)
    s = compute_nucleus_strength(tiny_connectome, tiny_lookup, config=cfg)
    # L.AV row, minus diagonal.
    mapping = {row["name"]: int(row["index"]) - 1
               for _, row in tiny_lookup.iterrows()}
    row_av = mapping["L.AV"]
    expected = tiny_connectome[row_av].sum() - tiny_connectome[row_av, row_av]
    assert s["L.AV"] == pytest.approx(expected)


def test_inter_thalamic_exclusion_drops_thalamic_edges(tiny_connectome, tiny_lookup):
    cfg_with = StrengthConfig(exclude_self=True, exclude_inter_thalamic=False)
    cfg_without = StrengthConfig(exclude_self=True, exclude_inter_thalamic=True)
    s_with = compute_nucleus_strength(tiny_connectome, tiny_lookup, config=cfg_with)
    s_without = compute_nucleus_strength(tiny_connectome, tiny_lookup, config=cfg_without)
    # Excluding inter-thalamic must reduce (or equal) every nucleus's strength.
    for key in s_with.index:
        assert s_without[key] <= s_with[key] + 1e-9


def test_mean_brain_strength_sane(tiny_connectome):
    val = mean_brain_strength(tiny_connectome)
    n = tiny_connectome.shape[0]
    total = tiny_connectome.sum()           # diag is zero already
    assert val == pytest.approx(total / n)


def test_load_round_trip(tmp_path: Path, tiny_connectome, tiny_lookup):
    cpath = tmp_path / "C.csv"
    np.savetxt(cpath, tiny_connectome, delimiter=" ")
    loaded = load_connectome(cpath)
    assert loaded.shape == tiny_connectome.shape
    np.testing.assert_allclose(loaded, tiny_connectome, atol=1e-10)

    lpath = tmp_path / "lookup.txt"
    tiny_lookup.to_csv(lpath, sep=" ", index=False, header=False)
    lut = load_node_lookup(lpath)
    assert "name" in lut.columns and "index" in lut.columns
    assert (lut["name"] == tiny_lookup["name"]).all()


def test_volume_from_label_image(tmp_path: Path):
    # Build a 10x10x10 volume with two voxel-counts known a priori.
    data = np.zeros((10, 10, 10), dtype=np.int32)
    data[0:3, 0:1, 0:1] = LEFT_LABELS["AV"]     # 3 voxels
    data[5:9, 0:2, 0:1] = LEFT_LABELS["CM"]     # 8 voxels
    affine = np.diag([1.5, 1.5, 1.5, 1.0])      # voxel volume = 1.5^3 = 3.375
    nib.save(nib.Nifti1Image(data, affine), tmp_path / "labels.nii.gz")

    vols = compute_nucleus_volume_mm3(tmp_path / "labels.nii.gz",
                                      rois=[
                                          ThalamicROI("AV", "L", LEFT_LABELS["AV"]),
                                          ThalamicROI("CM", "L", LEFT_LABELS["CM"]),
                                      ])
    assert vols["L.AV"] == pytest.approx(3 * 3.375)
    assert vols["L.CM"] == pytest.approx(8 * 3.375)


def test_per_subject_record_shape(tiny_connectome, tiny_lookup):
    df = per_subject_record("S0", tiny_connectome, tiny_lookup, label_image_path=None)
    # 4 nuclei × 2 sides = 8 rows
    assert len(df) == 8
    assert set(df["nucleus"]) == set(ANALYZED_NUCLEI)
    assert set(df["side"]) == {"L", "R"}
    assert (df["mean_brain_strength"] > 0).all()


def test_intrahemispheric_strength_excludes_cross_hemisphere_edges() -> None:
    """Intrahemispheric strength sums only same-hemisphere edges."""
    n = 84
    W = np.zeros((n, n))
    nodes = build_dk_nodes()
    left_idx = [i for i, node in enumerate(nodes) if node.side == "L"]
    right_idx = [i for i, node in enumerate(nodes) if node.side == "R"]
    W[left_idx[0], left_idx[1]] = 10.0
    W[left_idx[1], left_idx[0]] = 10.0
    W[right_idx[0], right_idx[1]] = 20.0
    W[right_idx[1], right_idx[0]] = 20.0
    W[left_idx[0], right_idx[0]] = 100.0
    W[right_idx[0], left_idx[0]] = 100.0

    mask = dk_intrahemispheric_edge_mask(n)
    assert not mask[left_idx[0], right_idx[0]]
    assert mask[left_idx[0], left_idx[1]]

    intra = intrahemispheric_strengths_und(W)
    assert intra[left_idx[0]] == pytest.approx(10.0)
    assert intra[right_idx[0]] == pytest.approx(20.0)
    assert intra[left_idx[0]] < W[left_idx[0]].sum()


def test_interhemispheric_strength_uses_cross_hemisphere_edges_only() -> None:
    """Interhemispheric strength sums only L↔R edges."""
    n = 84
    W = np.zeros((n, n))
    nodes = build_dk_nodes()
    left_idx = [i for i, node in enumerate(nodes) if node.side == "L"]
    right_idx = [i for i, node in enumerate(nodes) if node.side == "R"]
    W[left_idx[0], left_idx[1]] = 10.0
    W[left_idx[1], left_idx[0]] = 10.0
    W[left_idx[0], right_idx[0]] = 100.0
    W[right_idx[0], left_idx[0]] = 100.0

    mask = dk_interhemispheric_edge_mask(n)
    assert mask[left_idx[0], right_idx[0]]
    assert not mask[left_idx[0], left_idx[1]]

    inter = interhemispheric_strengths_und(W)
    assert inter[left_idx[0]] == pytest.approx(100.0)
    assert inter[left_idx[0]] < W[left_idx[0]].sum()


# ---------------------------------------------------------------------------
# BCT backend parity
# ---------------------------------------------------------------------------

def test_bct_backend_parity_with_numpy(tiny_connectome):
    """``_strengths_und`` should match a hand-coded row sum on any symmetric W."""
    from nodestrength.connectome import _strengths_und
    expected = tiny_connectome.sum(axis=0)
    got = _strengths_und(tiny_connectome)
    np.testing.assert_allclose(got, expected, atol=1e-10)


def test_bct_backend_matches_strengths_und_definition():
    """If bctpy is installed, _strengths_und must equal bct.strengths_und exactly."""
    bct = pytest.importorskip("bct")
    rng = np.random.default_rng(0)
    W = rng.uniform(0.1, 1.0, size=(20, 20))
    W = (W + W.T) / 2
    np.fill_diagonal(W, 0.0)

    from nodestrength.connectome import _strengths_und, uses_bctpy
    assert uses_bctpy(), "bctpy is installed but the backend isn't using it"
    np.testing.assert_allclose(_strengths_und(W), bct.strengths_und(W), atol=1e-10)


@pytest.mark.parametrize("lookup_name", [
    "L.AV",          # canonical
    "Left-AV",       # FreeSurfer hyphenated
    "Left_AV",       # underscored
    "lh.AV",         # surface-style
    "lh_AV",
    "L_AV",
    "L-AV",
    "AV-L",          # reversed
    "AV_L",
    "thal-L-AV",
    "thal_L_AV",
    "Left-Thalamus-AV",
    "Left_Thalamus_AV",
    "left-av",       # case-insensitive
    "LEFT-AV",
])
def test_roi_resolver_accepts_common_naming_variants(lookup_name):
    """The thalamic ROI resolver tolerates the naming conventions seen
    across THOMAS/FreeSurfer/MRtrix3 releases — case-insensitive."""
    from nodestrength.atlases import LEFT_LABELS, ThalamicROI
    from nodestrength.connectome import _name_to_row, _roi_row

    lookup = pd.DataFrame([
        {"index": 1, "name": "ctx-lh-PG1"},
        {"index": 2, "name": lookup_name},
    ])
    mapping = _name_to_row(lookup)
    roi = ThalamicROI("AV", "L", LEFT_LABELS["AV"])
    assert _roi_row(roi, mapping) == 1


def test_roi_resolver_reports_clearly_when_missing():
    from nodestrength.atlases import LEFT_LABELS, ThalamicROI
    from nodestrength.connectome import _name_to_row, _roi_row

    lookup = pd.DataFrame([
        {"index": 1, "name": "ctx-lh-PG1"},
        {"index": 2, "name": "ctx-lh-PG2"},
    ])
    roi = ThalamicROI("AV", "L", LEFT_LABELS["AV"])
    with pytest.raises(KeyError, match="Could not find ROI L.AV"):
        _roi_row(roi, _name_to_row(lookup))


def test_strength_via_bct_matches_naive_implementation(tiny_connectome, tiny_lookup):
    """End-to-end: BCT-backed strength == hand-written masked row sum."""
    from nodestrength.atlases import ANALYZED_NUCLEI, all_rois
    from nodestrength.connectome import (
        StrengthConfig, _name_to_row, _roi_row, compute_nucleus_strength,
    )

    rois = [r for r in all_rois() if r.name in ANALYZED_NUCLEI]
    mapping = _name_to_row(tiny_lookup)
    roi_rows = {roi.key: _roi_row(roi, mapping) for roi in rois}
    thalamic = list(roi_rows.values())

    keep = np.ones_like(tiny_connectome, dtype=bool)
    np.fill_diagonal(keep, False)
    keep[np.ix_(thalamic, thalamic)] = False
    masked = np.where(keep, tiny_connectome, 0.0)
    naive = {key: float(masked[row].sum()) for key, row in roi_rows.items()}

    bct_strength = compute_nucleus_strength(
        tiny_connectome, tiny_lookup,
        config=StrengthConfig(exclude_self=True, exclude_inter_thalamic=True),
    )
    for key, expected in naive.items():
        assert bct_strength[key] == pytest.approx(expected, abs=1e-10)
