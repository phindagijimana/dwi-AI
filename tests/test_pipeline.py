"""Pipeline-wrapper argument-construction tests (no external tools required)."""

from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

from nodestrength import pipeline as pipe
from nodestrength.atlases import LEFT_LABELS, RIGHT_LABELS


def test_recon_all_cmd_shape():
    cmd = pipe.recon_all_cmd("S001", Path("/data/t1.nii.gz"), Path("/scratch/fs"))
    assert cmd[0] == "recon-all"
    assert "-s" in cmd and "S001" in cmd
    assert "-all" in cmd


def test_dwi_preproc_cmds_order():
    cmds = pipe.dwi_preproc_cmds(
        dwi=Path("/d/dwi.nii.gz"), bvec=Path("/d/x.bvec"),
        bval=Path("/d/x.bval"), rpe_b0=Path("/d/rpe.nii.gz"),
        out_dir=Path("/out"))
    binaries = [c[0] for c in cmds]
    assert binaries == ["mrconvert", "dwidenoise", "dwifslpreproc", "dwibiascorrect"]


def test_tractography_uses_5M_streamlines_by_default():
    cmds = pipe.tractography_cmds(
        dwi=Path("/d/d.mif"), t1=Path("/d/t1.nii.gz"), out_dir=Path("/out"))
    tckgen = [c for c in cmds if c[0] == "tckgen"][0]
    assert "-select" in tckgen
    sel_idx = tckgen.index("-select")
    assert int(tckgen[sel_idx + 1]) == 5_000_000


def test_dry_run_returns_command_without_executing():
    res = pipe.run_recon_all("S001", Path("/x/t1.nii.gz"),
                             Path("/scratch/fs"), dry_run=True)
    assert res.returncode == 0
    assert "recon-all" in res.stdout


def test_missing_tool_raises():
    """Demanded binaries are surely absent here -- exercise the error path."""
    with pytest.raises(pipe.ToolUnavailableError):
        pipe.run_recon_all("S001", Path("/x/t1.nii.gz"),
                           Path("/scratch/fs"), dry_run=False)


def test_merge_thomas_into_lausanne(tmp_path: Path):
    affine = np.diag([1.0, 1.0, 1.0, 1.0])

    # Lausanne label image: 10x10x10, thalamus (id 10) at L hemisphere voxels,
    # thalamus (id 49) at R hemisphere voxels.
    lab = np.zeros((10, 10, 10), dtype=np.int32)
    lab[0:5, :, :] = 10            # left thalamus
    lab[5:10, :, :] = 49           # right thalamus
    lab_path = tmp_path / "lausanne.nii.gz"
    nib.save(nib.Nifti1Image(lab, affine), lab_path)

    # THOMAS per-nucleus masks: place AV in a corner of each hemisphere.
    thomas_dir = tmp_path / "thomas"
    (thomas_dir / "left").mkdir(parents=True)
    (thomas_dir / "right").mkdir(parents=True)

    left_av = np.zeros_like(lab, dtype=np.int16)
    left_av[0:1, 0:1, 0:1] = 1
    nib.save(nib.Nifti1Image(left_av, affine), thomas_dir / "left" / "AV.nii.gz")

    right_av = np.zeros_like(lab, dtype=np.int16)
    right_av[9:10, 0:1, 0:1] = 1
    nib.save(nib.Nifti1Image(right_av, affine), thomas_dir / "right" / "AV.nii.gz")

    merged = tmp_path / "merged.nii.gz"
    pipe.merge_thomas_into_lausanne(lab_path, thomas_dir, merged)

    out = nib.load(str(merged)).get_fdata().astype(np.int32)
    assert out[0, 0, 0] == LEFT_LABELS["AV"]
    assert out[9, 0, 0] == RIGHT_LABELS["AV"]
    # Old thalamus voxels not covered by a THOMAS mask must be reset to 0.
    assert out[2, 2, 2] == 0
