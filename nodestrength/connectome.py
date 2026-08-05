"""Read MRtrix3 connectomes and compute per-nucleus strength and volume.

The paper's "connectivity strength" (Section 2.6) is the sum of SIFT2-weighted
edges between a thalamic nucleus and every other brain region, with two
exclusions:

* self-connections (diagonal of the adjacency matrix);
* inter-thalamic-nuclei connections — see Figure 2 caption ("Discounting the
  inter-thalamic nuclei connections...").

This module implements that calculation, plus per-nucleus volume from a label
NIfTI (Section 2.4).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

from .atlases import ANALYZED_NUCLEI, ThalamicROI, all_rois


try:                                                       # pragma: no cover
    import bct as _bct
    _HAS_BCT = True
except ImportError:                                        # pragma: no cover
    _bct = None
    _HAS_BCT = False


def _strengths_und(W: np.ndarray) -> np.ndarray:
    """Undirected weighted node strength.

    Identical to BCT's ``strengths_und`` (which is ``np.sum(CIJ, axis=0)``).
    Uses ``bctpy`` if installed (auditable to the canonical source), otherwise
    the equivalent pure-numpy expression. Returns a 1-D array of length N.
    """
    if _HAS_BCT:
        return np.asarray(_bct.strengths_und(W))
    return W.sum(axis=0)


def dk_intrahemispheric_edge_mask(n: int = 84) -> np.ndarray:
    """Boolean mask: True for same-hemisphere off-diagonal edges (78×78 or 84×84)."""
    from nodestrength.analysis_atlas import resolve_analysis_atlas

    atlas = resolve_analysis_atlas(n)
    sides = atlas.sides()
    same = sides[:, None] == sides[None, :]
    np.fill_diagonal(same, False)
    return same


def intrahemispheric_strengths_und(W: np.ndarray) -> np.ndarray:
    """Node strength using only within-hemisphere edges (L↔L and R↔R)."""
    if W.shape[0] != W.shape[1]:
        raise ValueError("Connectome must be square")
    keep = dk_intrahemispheric_edge_mask(W.shape[0])
    masked = np.where(keep, W, 0.0)
    return _strengths_und(masked)


def uses_bctpy() -> bool:
    """Whether ``bctpy`` is being used for node-strength computation."""
    return _HAS_BCT


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_connectome(path: str | Path) -> np.ndarray:
    """Load a square connectome matrix produced by ``tck2connectome``.

    MRtrix3 writes whitespace- or comma-separated matrices depending on
    pipeline conventions. This loader tries comma first (most ``.csv``
    outputs), falls back to whitespace, and asserts a square shape.
    """
    text = Path(path).read_text()
    last_err: Exception | None = None
    for delim in (",", None):    # comma first, then any-whitespace
        try:
            from io import StringIO
            arr = np.loadtxt(StringIO(text), delimiter=delim)
            break
        except Exception as exc:
            last_err = exc
    else:
        raise last_err  # type: ignore[misc]

    if arr.ndim != 2 or arr.shape[0] != arr.shape[1]:
        raise ValueError(f"Connectome at {path} is not square: shape={arr.shape}")
    # Force symmetry (MRtrix can emit upper- or lower-triangular under some flags).
    return 0.5 * (arr + arr.T)


def load_node_lookup(path: str | Path) -> pd.DataFrame:
    """Load an MRtrix3 / FreeSurfer node-lookup table.

    Expected columns: ``index, name`` (1-based index matching connectome rows).
    Extra columns are preserved. Lines beginning with ``#`` are skipped.
    """
    df = pd.read_csv(
        str(path),
        sep=r"\s+",
        comment="#",
        header=None,
        engine="python",
    )
    if df.shape[1] < 2:
        raise ValueError(f"Node lookup at {path} must have at least 2 columns")
    df = df.rename(columns={0: "index", 1: "name"})
    df["index"] = df["index"].astype(int)
    df["name"] = df["name"].astype(str)
    return df


# ---------------------------------------------------------------------------
# Strength
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StrengthConfig:
    """How to compute nucleus strength.

    Parameters
    ----------
    exclude_self : bool
        Drop the diagonal entry of the adjacency matrix.
    exclude_inter_thalamic : bool
        Drop edges between any pair of THOMAS thalamic ROIs (Figure 2
        convention). Recommended for the paper's "connectivity strength".
    """
    exclude_self: bool = True
    exclude_inter_thalamic: bool = True


def _name_to_row(node_lookup: pd.DataFrame) -> Dict[str, int]:
    """Map node name -> 0-based row index for the connectome array."""
    return {row["name"]: int(row["index"]) - 1 for _, row in node_lookup.iterrows()}


def _roi_candidate_names(roi: ThalamicROI) -> list[str]:
    """Generate the set of node-lookup names this thalamic ROI may appear under.

    THOMAS releases and post-processing pipelines name thalamic nuclei in many
    ways. The candidates cover the conventions we have seen in the wild:

    * ``L.AV`` / ``R.AV``                — this package's canonical form
    * ``Left-AV`` / ``Right-AV``         — FreeSurfer-style hyphenated
    * ``Left_AV`` / ``Right_AV``         — underscored
    * ``lh.AV`` / ``rh.AV``              — Freesurfer surface-style
    * ``L_AV`` / ``R_AV``                — short underscored
    * ``L-AV`` / ``R-AV``                — short hyphenated
    * ``AV-L`` / ``AV-R``                — reversed order
    * ``thal-L-AV`` / ``thal-R-AV``      — THOMAS prefix
    * ``Left-Thalamus-AV``               — full long form
    * THOMAS canonical IDs like ``1-AV`` (or other integer prefix)
    * THOMAS label id as a string         — last resort
    """
    name, side = roi.name, roi.side
    long_side = "Left" if side == "L" else "Right"
    fs_side = "lh" if side == "L" else "rh"
    return [
        roi.key,                                       # L.AV
        f"{long_side}-{name}",                         # Left-AV
        f"{long_side}_{name}",                         # Left_AV
        f"{fs_side}.{name}",                           # lh.AV
        f"{fs_side}_{name}",                           # lh_AV
        f"{side}_{name}",                              # L_AV
        f"{side}-{name}",                              # L-AV
        f"{name}-{side}",                              # AV-L
        f"{name}_{side}",                              # AV_L
        f"thal-{side}-{name}",                         # thal-L-AV
        f"thal_{side}_{name}",                         # thal_L_AV
        f"{long_side}-Thalamus-{name}",                # Left-Thalamus-AV
        f"{long_side}_Thalamus_{name}",                # Left_Thalamus_AV
        f"Thal-{name}-{side}",                         # Thal-AV-L
        str(roi.label_id),                             # raw integer label
    ]


def _roi_row(roi: ThalamicROI, mapping: Mapping[str, int]) -> int:
    """Resolve a thalamic ROI to its row in the connectome.

    Tries every name variant in ``_roi_candidate_names`` against the
    node-lookup, **case-insensitively**. Raises ``KeyError`` with the
    full candidate list and a short sample of available names so failures
    are debuggable.
    """
    # Lower-case the mapping once for case-insensitive lookup.
    lc_map = {k.lower(): v for k, v in mapping.items()}

    for candidate in _roi_candidate_names(roi):
        if candidate in mapping:
            return mapping[candidate]
        lc = candidate.lower()
        if lc in lc_map:
            return lc_map[lc]
    raise KeyError(
        f"Could not find ROI {roi.key} in node lookup. "
        f"Tried: {_roi_candidate_names(roi)[:5]}... ({len(_roi_candidate_names(roi))} variants). "
        f"Available (first 8): {list(mapping)[:8]}"
    )


def compute_nucleus_strength(
    connectome: np.ndarray,
    node_lookup: pd.DataFrame,
    rois: Optional[Sequence[ThalamicROI]] = None,
    config: StrengthConfig = StrengthConfig(),
) -> pd.Series:
    """Sum of SIFT2-weighted edges between each thalamic ROI and the rest of the brain.

    Returns
    -------
    pd.Series
        Indexed by ROI key (e.g. ``"L.AV"``), values are the strength.
    """
    if rois is None:
        rois = [r for r in all_rois() if r.name in ANALYZED_NUCLEI]

    mapping = _name_to_row(node_lookup)
    roi_rows = {roi.key: _roi_row(roi, mapping) for roi in rois}

    # Mask: True for edges we *keep*.
    n = connectome.shape[0]
    keep = np.ones_like(connectome, dtype=bool)
    if config.exclude_self:
        np.fill_diagonal(keep, False)
    if config.exclude_inter_thalamic:
        thalamic_rows = list(roi_rows.values())
        keep[np.ix_(thalamic_rows, thalamic_rows)] = False

    masked = np.where(keep, connectome, 0.0)
    # Delegate the row sum to BCT's strengths_und (or its numpy equivalent).
    # The mask zeroes any edges we want to drop, so strengths_und(masked)[i]
    # is precisely ∑_{j∈keep_set(i)} W_ij — the formula in the paper.
    strengths_vec = _strengths_und(masked)
    out = {key: float(strengths_vec[row]) for key, row in roi_rows.items()}
    return pd.Series(out, name="strength")


def mean_brain_strength(
    connectome: np.ndarray,
    config: StrengthConfig = StrengthConfig(exclude_self=True, exclude_inter_thalamic=False),
) -> float:
    """Mean of per-ROI strengths across the whole-brain parcellation.

    Used as a global-connectivity covariate in the normative model
    (Section 2.6: "the mean ROI strength was entered into the GLM").
    """
    keep = np.ones_like(connectome, dtype=bool)
    if config.exclude_self:
        np.fill_diagonal(keep, False)
    masked = np.where(keep, connectome, 0.0)
    return float(_strengths_und(masked).mean())


# ---------------------------------------------------------------------------
# Volume
# ---------------------------------------------------------------------------

def compute_nucleus_volume_mm3(
    label_image_path: str | Path,
    rois: Optional[Sequence[ThalamicROI]] = None,
) -> pd.Series:
    """Per-nucleus volume in mm³ from a merged Lausanne+THOMAS label NIfTI.

    Loads via nibabel, sums voxels per label, multiplies by the voxel volume
    derived from the image affine.
    """
    import nibabel as nib  # local import keeps unit tests dep-light

    if rois is None:
        rois = [r for r in all_rois() if r.name in ANALYZED_NUCLEI]

    img = nib.load(str(label_image_path))
    data = np.asarray(img.dataobj)
    voxel_volume = float(abs(np.linalg.det(img.affine[:3, :3])))

    out: Dict[str, float] = {}
    for roi in rois:
        count = int((data == roi.label_id).sum())
        out[roi.key] = count * voxel_volume
    return pd.Series(out, name="volume_mm3")


# ---------------------------------------------------------------------------
# Per-subject record
# ---------------------------------------------------------------------------

def per_subject_record(
    subject_id: str,
    connectome: np.ndarray,
    node_lookup: pd.DataFrame,
    label_image_path: Optional[str | Path] = None,
    rois: Optional[Sequence[ThalamicROI]] = None,
    config: StrengthConfig = StrengthConfig(),
) -> pd.DataFrame:
    """Return a long-form dataframe of (subject, nucleus, side, strength, volume)."""
    if rois is None:
        rois = [r for r in all_rois() if r.name in ANALYZED_NUCLEI]

    strength = compute_nucleus_strength(connectome, node_lookup, rois=rois, config=config)
    if label_image_path is not None:
        volume = compute_nucleus_volume_mm3(label_image_path, rois=rois)
    else:
        volume = pd.Series({roi.key: np.nan for roi in rois}, name="volume_mm3")

    rows = []
    for roi in rois:
        rows.append({
            "subject": subject_id,
            "nucleus": roi.name,
            "side": roi.side,
            "strength": strength[roi.key],
            "volume_mm3": volume[roi.key],
        })
    df = pd.DataFrame(rows)
    df["mean_brain_strength"] = mean_brain_strength(connectome)
    return df


def stack_cohort(records: Iterable[pd.DataFrame]) -> pd.DataFrame:
    """Concatenate per-subject records into a single long-form cohort dataframe."""
    return pd.concat(list(records), ignore_index=True)
