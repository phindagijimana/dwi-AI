"""Empirically verify the dk_nodes.mif label ordering against FreeSurfer's.

Approach
--------
Both ``aparc+aseg_in_dwi.nii.gz`` and ``dk_nodes.mif`` are in the same
DWI grid. For each fs_default label ``k in 1..84`` in dk_nodes, find the
mode (most common) FreeSurfer label at the same voxel locations. That
mapping IS the labelconvert table that MRtrix3 applied — no need to ship
``fs_default.txt`` around.

We then convert each FreeSurfer integer to its canonical name via the
hardcoded FreeSurfer color-LUT subset (only the labels that appear in DK
connectomes), and produce a CSV ``empirical_lut.csv`` ready to drop into
``nodestrength.dk_atlas``.

Run:

    python scripts/verify_dk_labels.py \
        --subject /path/to/connectomes/sub-001 \
        --out /path/to/out/empirical_lut.csv
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Dict

import nibabel as nib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nodestrength.mif import read_mif


# ---------------------------------------------------------------------------
# Minimal FreeSurfer color-LUT subset (DK cortex + aseg subcortical).
# These are the only labels that survive labelconvert into fs_default.txt.
# Reference: $FREESURFER_HOME/FreeSurferColorLUT.txt
# ---------------------------------------------------------------------------

_FS_LUT: Dict[int, str] = {
    # Cortical LH (1001..1035 = ctx-lh-*)
    1001: "ctx-lh-bankssts",
    1002: "ctx-lh-caudalanteriorcingulate",
    1003: "ctx-lh-caudalmiddlefrontal",
    1005: "ctx-lh-cuneus",
    1006: "ctx-lh-entorhinal",
    1007: "ctx-lh-fusiform",
    1008: "ctx-lh-inferiorparietal",
    1009: "ctx-lh-inferiortemporal",
    1010: "ctx-lh-isthmuscingulate",
    1011: "ctx-lh-lateraloccipital",
    1012: "ctx-lh-lateralorbitofrontal",
    1013: "ctx-lh-lingual",
    1014: "ctx-lh-medialorbitofrontal",
    1015: "ctx-lh-middletemporal",
    1016: "ctx-lh-parahippocampal",
    1017: "ctx-lh-paracentral",
    1018: "ctx-lh-parsopercularis",
    1019: "ctx-lh-parsorbitalis",
    1020: "ctx-lh-parstriangularis",
    1021: "ctx-lh-pericalcarine",
    1022: "ctx-lh-postcentral",
    1023: "ctx-lh-posteriorcingulate",
    1024: "ctx-lh-precentral",
    1025: "ctx-lh-precuneus",
    1026: "ctx-lh-rostralanteriorcingulate",
    1027: "ctx-lh-rostralmiddlefrontal",
    1028: "ctx-lh-superiorfrontal",
    1029: "ctx-lh-superiorparietal",
    1030: "ctx-lh-superiortemporal",
    1031: "ctx-lh-supramarginal",
    1032: "ctx-lh-frontalpole",
    1033: "ctx-lh-temporalpole",
    1034: "ctx-lh-transversetemporal",
    1035: "ctx-lh-insula",
    # Cortical RH (2001..2035)
    2001: "ctx-rh-bankssts",
    2002: "ctx-rh-caudalanteriorcingulate",
    2003: "ctx-rh-caudalmiddlefrontal",
    2005: "ctx-rh-cuneus",
    2006: "ctx-rh-entorhinal",
    2007: "ctx-rh-fusiform",
    2008: "ctx-rh-inferiorparietal",
    2009: "ctx-rh-inferiortemporal",
    2010: "ctx-rh-isthmuscingulate",
    2011: "ctx-rh-lateraloccipital",
    2012: "ctx-rh-lateralorbitofrontal",
    2013: "ctx-rh-lingual",
    2014: "ctx-rh-medialorbitofrontal",
    2015: "ctx-rh-middletemporal",
    2016: "ctx-rh-parahippocampal",
    2017: "ctx-rh-paracentral",
    2018: "ctx-rh-parsopercularis",
    2019: "ctx-rh-parsorbitalis",
    2020: "ctx-rh-parstriangularis",
    2021: "ctx-rh-pericalcarine",
    2022: "ctx-rh-postcentral",
    2023: "ctx-rh-posteriorcingulate",
    2024: "ctx-rh-precentral",
    2025: "ctx-rh-precuneus",
    2026: "ctx-rh-rostralanteriorcingulate",
    2027: "ctx-rh-rostralmiddlefrontal",
    2028: "ctx-rh-superiorfrontal",
    2029: "ctx-rh-superiorparietal",
    2030: "ctx-rh-superiortemporal",
    2031: "ctx-rh-supramarginal",
    2032: "ctx-rh-frontalpole",
    2033: "ctx-rh-temporalpole",
    2034: "ctx-rh-transversetemporal",
    2035: "ctx-rh-insula",
    # Subcortical
    10: "Left-Thalamus-Proper",
    11: "Left-Caudate",
    12: "Left-Putamen",
    13: "Left-Pallidum",
    17: "Left-Hippocampus",
    18: "Left-Amygdala",
    26: "Left-Accumbens-area",
    49: "Right-Thalamus-Proper",
    50: "Right-Caudate",
    51: "Right-Putamen",
    52: "Right-Pallidum",
    53: "Right-Hippocampus",
    54: "Right-Amygdala",
    58: "Right-Accumbens-area",
    16: "Brain-Stem",
    # Sometimes present as a fallback when FreeSurfer ages
    8:  "Left-Cerebellum-Cortex",
    47: "Right-Cerebellum-Cortex",
}


def empirical_lut(aparc_path: Path, dk_nodes_path: Path) -> pd.DataFrame:
    """Build the per-dk-node table: fs_default index → FreeSurfer label → name."""
    fs_img = nib.load(str(aparc_path))
    fs = np.asarray(fs_img.dataobj, dtype=np.int32)
    dk = read_mif(dk_nodes_path).data.astype(np.int32)

    if fs.shape != dk.shape:
        raise ValueError(
            f"Shape mismatch: aparc+aseg {fs.shape} vs dk_nodes {dk.shape}. "
            "Cannot compare voxel-wise."
        )

    rows = []
    fs_unique_overall = set(np.unique(fs).tolist())
    for k in sorted(int(x) for x in np.unique(dk) if x != 0):
        # FS labels at the same voxels as dk_nodes == k.
        labels_here = fs[dk == k]
        if labels_here.size == 0:
            continue
        # Drop zero entries (background); take the mode of the rest.
        nonzero = labels_here[labels_here != 0]
        if nonzero.size == 0:
            mode_fs = 0
            n_voxels = labels_here.size
        else:
            mode_fs, count = Counter(nonzero.tolist()).most_common(1)[0]
            n_voxels = nonzero.size
        rows.append({
            "fs_default_index": k,
            "freesurfer_label": int(mode_fs),
            "freesurfer_name": _FS_LUT.get(int(mode_fs), f"FS-{mode_fs}"),
            "n_voxels": int(n_voxels),
        })

    fs_used = {row["freesurfer_label"] for row in rows}
    missing = sorted(fs_unique_overall - fs_used)

    df = pd.DataFrame(rows)
    df.attrs["fs_labels_not_in_dk"] = missing
    return df


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--subject", required=True, type=Path,
                   help="Subject directory with aparc+aseg_in_dwi.nii.gz and dk_nodes.mif.")
    p.add_argument("--out", required=True, type=Path,
                   help="Output CSV path for the empirical LUT.")
    args = p.parse_args(argv)

    aparc = args.subject / "aparc+aseg_in_dwi.nii.gz"
    dk_nodes = args.subject / "dk_nodes.mif"
    if not aparc.exists() or not dk_nodes.exists():
        print(f"Missing inputs under {args.subject}", file=sys.stderr)
        return 2

    df = empirical_lut(aparc, dk_nodes)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"Wrote {args.out}  ({len(df)} non-zero dk_nodes labels).")
    print()
    print(df.to_string(index=False))
    print()
    print(f"FreeSurfer labels NOT mapped into dk_nodes (dropped by labelconvert): "
          f"{df.attrs.get('fs_labels_not_in_dk', [])[:20]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
