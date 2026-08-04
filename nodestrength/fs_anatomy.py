"""FreeSurfer anatomy helpers for clinical report figures."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

import nibabel as nib
import numpy as np
import pandas as pd

# FreeSurfer aseg label IDs for DK subcortical structures (L, R).
_FS_SUBCORTICAL: Dict[str, Tuple[int, int]] = {
    "Thalamus-Proper": (10, 49),
    "Caudate": (11, 50),
    "Putamen": (12, 51),
    "Pallidum": (13, 52),
    "Hippocampus": (17, 53),
    "Amygdala": (18, 54),
    "Accumbens-area": (26, 58),
}

_APARC_CANDIDATES: Tuple[str, ...] = (
    "aparc+aseg_in_dwi.nii.gz",
    "aparc+aseg.nii.gz",
    "aparc+aseg_in_t1w.nii.gz",
    "aparc+aseg_in_rawavg.nii.gz",
)


def find_aparc_seg(subject_dir: Path) -> Optional[Path]:
    """Return the first available FreeSurfer ``aparc+aseg`` volume under a subject folder."""
    for name in _APARC_CANDIDATES:
        path = subject_dir / name
        if path.is_file():
            return path
    return None


def fs_subcortical_volumes_mm3(aparc_path: Path) -> pd.DataFrame:
    """Compute subcortical ROI volumes from a FreeSurfer ``aparc+aseg`` image."""
    img = nib.load(str(aparc_path))
    data = np.asarray(img.dataobj, dtype=np.int32)
    zooms = img.header.get_zooms()[:3]
    voxel_mm3 = float(np.abs(np.prod(zooms)))

    rows = []
    for roi_name, (l_id, r_id) in _FS_SUBCORTICAL.items():
        l_count = int((data == l_id).sum())
        r_count = int((data == r_id).sum())
        rows.append({
            "roi_name": roi_name,
            "L_volume_mm3": l_count * voxel_mm3,
            "R_volume_mm3": r_count * voxel_mm3,
            "source": aparc_path.name,
        })
    return pd.DataFrame(rows)
