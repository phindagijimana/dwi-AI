"""Tests for FreeSurfer anatomy helpers."""

from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np

from nodestrength.fs_anatomy import find_aparc_seg, fs_subcortical_volumes_mm3


def test_find_aparc_seg(tmp_path: Path) -> None:
    sub = tmp_path / "sub-001"
    sub.mkdir()
    aparc = sub / "aparc+aseg_in_dwi.nii.gz"
    data = np.zeros((4, 4, 4), dtype=np.int16)
    data[0, 0, 0] = 10   # L thalamus
    data[1, 0, 0] = 49   # R thalamus
    nib.save(nib.Nifti1Image(data, np.eye(4)), str(aparc))
    assert find_aparc_seg(sub) == aparc


def test_fs_subcortical_volumes_mm3(tmp_path: Path) -> None:
    aparc = tmp_path / "aparc.nii.gz"
    data = np.zeros((2, 2, 2), dtype=np.int16)
    data[0, 0, 0] = 17   # L hippocampus — 1 voxel
    data[0, 0, 1] = 53   # R hippocampus — 1 voxel
    affine = np.diag([1.0, 1.0, 1.0, 1.0])
    nib.save(nib.Nifti1Image(data, affine), str(aparc))
    df = fs_subcortical_volumes_mm3(aparc)
    hip = df.loc[df["roi_name"] == "Hippocampus"].iloc[0]
    assert hip["L_volume_mm3"] == 1.0
    assert hip["R_volume_mm3"] == 1.0
