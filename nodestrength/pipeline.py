"""Subprocess wrappers for the FreeSurfer / THOMAS / MRtrix3 pipeline.

Mirrors Section 2.4–2.6 of Piper et al. 2026, step by step:

1. ``recon_all``                   — FreeSurfer cortical/subcortical parcellation.
2. ``lausanne_aparc60``            — convert FreeSurfer aparc to Lausanne aparc60.
3. ``thomas``                      — THOMAS T1w segmentation of 8 thalamic nuclei.
4. ``merge_thomas_into_lausanne``  — replace Lausanne thalamus with THOMAS nuclei.
5. ``dwi_preproc``                 — dwidenoise + dwifslpreproc + dwibiascorrect.
6. ``tractography``                — dhollander response, msmt-csd FOD, 5 M streamlines, SIFT2.
7. ``build_connectome``            — tck2connectome with combined labels.

All functions accept input paths, an output directory, and (optionally) a
``dry_run`` flag that prints the command without executing it. Tool absence
raises ``ToolUnavailableError`` with the offending binary named.

Nothing in this module makes a network or scanner call; everything is a thin
shell wrapper. Tests cover argument-construction only.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from .atlases import LEFT_LABELS, RIGHT_LABELS, THOMAS_NUCLEI


class ToolUnavailableError(RuntimeError):
    """Raised when a required external binary is missing from PATH."""


def _require(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        raise ToolUnavailableError(
            f"Required tool '{tool}' was not found on PATH. "
            f"Install the parent toolkit (FreeSurfer / FSL / MRtrix3 / THOMAS) "
            f"and make sure '{tool}' is on PATH."
        )
    return path


@dataclass(frozen=True)
class CommandResult:
    cmd: List[str]
    returncode: int
    stdout: str
    stderr: str


def _run(cmd: Sequence[str], dry_run: bool = False) -> CommandResult:
    if dry_run:
        return CommandResult(list(cmd), 0, " ".join(map(str, cmd)), "")
    proc = subprocess.run(list(map(str, cmd)), check=True,
                          capture_output=True, text=True)
    return CommandResult(list(cmd), proc.returncode, proc.stdout, proc.stderr)


# ---------------------------------------------------------------------------
# 1. FreeSurfer recon-all (Section 2.4)
# ---------------------------------------------------------------------------

def recon_all_cmd(subject_id: str, t1: Path, subjects_dir: Path) -> List[str]:
    """Standard recon-all -all invocation."""
    return [
        "recon-all",
        "-s", subject_id,
        "-i", str(t1),
        "-sd", str(subjects_dir),
        "-all",
    ]


def run_recon_all(subject_id: str, t1: Path, subjects_dir: Path,
                  dry_run: bool = False) -> CommandResult:
    if not dry_run:
        _require("recon-all")
    return _run(recon_all_cmd(subject_id, t1, subjects_dir), dry_run=dry_run)


# ---------------------------------------------------------------------------
# 2. Lausanne aparc60 (Section 2.4)
# ---------------------------------------------------------------------------

def lausanne_aparc60_cmd(subject_id: str, subjects_dir: Path, out_dir: Path) -> List[str]:
    """Run the CMTK Lausanne parcellator at the 'scale 2' (aparc60) level.

    Assumes ``cmtklib``'s ``parcellate.py`` or the standalone
    ``mne_lausanne2008.py`` is on PATH. Users can replace this with their
    locally preferred Lausanne tool.
    """
    return [
        "lausanne_parcellator",        # placeholder script name
        "--subject", subject_id,
        "--subjects-dir", str(subjects_dir),
        "--scale", "aparc60",
        "--out", str(out_dir),
    ]


def run_lausanne_aparc60(subject_id: str, subjects_dir: Path, out_dir: Path,
                         dry_run: bool = False) -> CommandResult:
    if not dry_run:
        _require("lausanne_parcellator")
    return _run(lausanne_aparc60_cmd(subject_id, subjects_dir, out_dir),
                dry_run=dry_run)


# ---------------------------------------------------------------------------
# 3. THOMAS (Section 2.4)
# ---------------------------------------------------------------------------

def thomas_cmd(t1: Path, out_dir: Path) -> List[str]:
    """THOMAS T1w segmentation command (containerized release accepts these flags)."""
    return [
        "thomas",
        "-i", str(t1),
        "-o", str(out_dir),
        "-t", "T1",
    ]


def run_thomas(t1: Path, out_dir: Path, dry_run: bool = False) -> CommandResult:
    if not dry_run:
        _require("thomas")
    return _run(thomas_cmd(t1, out_dir), dry_run=dry_run)


def thomas_label_paths(thomas_out: Path) -> dict[str, Path]:
    """Map ``{side, nucleus} -> NIfTI path`` for the per-nucleus THOMAS masks.

    THOMAS writes one file per nucleus per side (e.g. ``left/1-thalamus.nii.gz``).
    The exact filenames vary slightly between THOMAS versions; this returns the
    canonical layout used by the open-source ``thomas_new`` release.
    """
    out: dict[str, Path] = {}
    for nucleus in THOMAS_NUCLEI:
        out[f"L.{nucleus}"] = thomas_out / "left" / f"{nucleus}.nii.gz"
        out[f"R.{nucleus}"] = thomas_out / "right" / f"{nucleus}.nii.gz"
    return out


# ---------------------------------------------------------------------------
# 4. Merge Lausanne + THOMAS into a single label volume (Section 2.4)
# ---------------------------------------------------------------------------

def merge_thomas_into_lausanne(
    lausanne_labels: Path,
    thomas_out: Path,
    merged_out: Path,
    thalamus_lausanne_ids: Iterable[int] = (10, 49),   # FreeSurfer Left/Right Thalamus
) -> Path:
    """Replace the Lausanne thalamus parcels with per-nucleus THOMAS labels.

    Operates in voxel space (no resampling — both atlases are assumed already
    on the same grid via FreeSurfer's native-space convention).
    """
    import nibabel as nib
    import numpy as np

    lab_img = nib.load(str(lausanne_labels))
    lab = np.asarray(lab_img.dataobj).copy()

    for tid in thalamus_lausanne_ids:
        lab[lab == tid] = 0

    for nucleus in THOMAS_NUCLEI:
        for side, label_map in (("L", LEFT_LABELS), ("R", RIGHT_LABELS)):
            mask_path = thomas_out / ("left" if side == "L" else "right") / f"{nucleus}.nii.gz"
            if not mask_path.exists():
                continue
            mask = np.asarray(nib.load(str(mask_path)).dataobj) > 0
            lab[mask] = label_map[nucleus]

    out_img = nib.Nifti1Image(lab.astype("int32"), lab_img.affine, lab_img.header)
    merged_out.parent.mkdir(parents=True, exist_ok=True)
    nib.save(out_img, str(merged_out))
    return merged_out


# ---------------------------------------------------------------------------
# 5. dMRI preprocessing (Section 2.5)
# ---------------------------------------------------------------------------

def dwi_preproc_cmds(dwi: Path, bvec: Path, bval: Path, rpe_b0: Path,
                     out_dir: Path) -> List[List[str]]:
    """Return the ordered MRtrix3 / FSL preprocessing commands."""
    denoised = out_dir / "dwi_den.mif"
    preproc = out_dir / "dwi_preproc.mif"
    biascorr = out_dir / "dwi_biascorr.mif"
    return [
        ["mrconvert", str(dwi), str(denoised.with_suffix(".raw.mif")),
         "-fslgrad", str(bvec), str(bval)],
        ["dwidenoise", str(denoised.with_suffix(".raw.mif")), str(denoised)],
        ["dwifslpreproc", str(denoised), str(preproc),
         "-rpe_pair", "-se_epi", str(rpe_b0),
         "-pe_dir", "AP", "-eddy_options", " --slm=linear"],
        ["dwibiascorrect", "fsl", str(preproc), str(biascorr)],
    ]


def run_dwi_preproc(dwi: Path, bvec: Path, bval: Path, rpe_b0: Path,
                    out_dir: Path, dry_run: bool = False) -> List[CommandResult]:
    if not dry_run:
        for tool in ("mrconvert", "dwidenoise", "dwifslpreproc", "dwibiascorrect"):
            _require(tool)
    out_dir.mkdir(parents=True, exist_ok=True)
    return [_run(c, dry_run=dry_run)
            for c in dwi_preproc_cmds(dwi, bvec, bval, rpe_b0, out_dir)]


# ---------------------------------------------------------------------------
# 6. Tractography (Section 2.5)
# ---------------------------------------------------------------------------

def tractography_cmds(dwi: Path, t1: Path, out_dir: Path,
                      n_streamlines: int = 5_000_000) -> List[List[str]]:
    """5M-streamline ACT tractography with SIFT2 weights."""
    wm = out_dir / "wm.txt"
    gm = out_dir / "gm.txt"
    csf = out_dir / "csf.txt"
    fod = out_dir / "wmfod.mif"
    seg5tt = out_dir / "5tt.mif"
    tracts = out_dir / "tracks_5M.tck"
    weights = out_dir / "sift2_weights.txt"
    return [
        ["dwi2response", "dhollander", str(dwi), str(wm), str(gm), str(csf)],
        ["dwi2fod", "msmt_csd", str(dwi), str(wm), str(fod), str(gm),
         str(out_dir / "gmfod.mif"), str(csf), str(out_dir / "csffod.mif")],
        ["5ttgen", "fsl", str(t1), str(seg5tt)],
        ["tckgen", "-act", str(seg5tt),
         "-backtrack", "-crop_at_gmwmi", "-seed_dynamic", str(fod),
         "-select", str(n_streamlines), str(fod), str(tracts)],
        ["tcksift2", str(tracts), str(fod), str(weights)],
    ]


def run_tractography(dwi: Path, t1: Path, out_dir: Path,
                     n_streamlines: int = 5_000_000,
                     dry_run: bool = False) -> List[CommandResult]:
    if not dry_run:
        for tool in ("dwi2response", "dwi2fod", "5ttgen", "tckgen", "tcksift2"):
            _require(tool)
    out_dir.mkdir(parents=True, exist_ok=True)
    return [_run(c, dry_run=dry_run)
            for c in tractography_cmds(dwi, t1, out_dir, n_streamlines)]


# ---------------------------------------------------------------------------
# 7. Connectome construction (Section 2.6)
# ---------------------------------------------------------------------------

def build_connectome_cmd(tracts: Path, weights: Path, labels: Path,
                         out_csv: Path, lookup: Optional[Path] = None) -> List[str]:
    cmd = [
        "tck2connectome",
        str(tracts), str(labels), str(out_csv),
        "-tck_weights_in", str(weights),
        "-symmetric", "-zero_diagonal",
    ]
    if lookup is not None:
        cmd += ["-lookup_ordering", str(lookup)]
    return cmd


def run_build_connectome(tracts: Path, weights: Path, labels: Path,
                         out_csv: Path, lookup: Optional[Path] = None,
                         dry_run: bool = False) -> CommandResult:
    if not dry_run:
        _require("tck2connectome")
    return _run(build_connectome_cmd(tracts, weights, labels, out_csv, lookup),
                dry_run=dry_run)


# ---------------------------------------------------------------------------
# 8. End-to-end orchestration (one subject)
# ---------------------------------------------------------------------------

def run_subject(
    subject_id: str,
    t1: Path,
    dwi: Path,
    bvec: Path,
    bval: Path,
    rpe_b0: Path,
    subjects_dir: Path,
    out_dir: Path,
    dry_run: bool = False,
) -> dict:
    """Run the full per-subject pipeline and return a summary of artefacts."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    run_recon_all(subject_id, t1, subjects_dir, dry_run=dry_run)
    run_lausanne_aparc60(subject_id, subjects_dir, out_dir / "lausanne",
                         dry_run=dry_run)
    run_thomas(t1, out_dir / "thomas", dry_run=dry_run)

    merged_labels = out_dir / "labels_combined.nii.gz"
    if not dry_run:
        merge_thomas_into_lausanne(
            lausanne_labels=out_dir / "lausanne" / "aparc60.nii.gz",
            thomas_out=out_dir / "thomas",
            merged_out=merged_labels,
        )

    run_dwi_preproc(dwi, bvec, bval, rpe_b0, out_dir / "dwi", dry_run=dry_run)
    run_tractography(out_dir / "dwi" / "dwi_biascorr.mif", t1,
                     out_dir / "tracto", dry_run=dry_run)
    run_build_connectome(
        tracts=out_dir / "tracto" / "tracks_5M.tck",
        weights=out_dir / "tracto" / "sift2_weights.txt",
        labels=merged_labels,
        out_csv=out_dir / "connectome.csv",
        dry_run=dry_run,
    )
    return {
        "subject": subject_id,
        "labels": str(merged_labels),
        "connectome": str(out_dir / "connectome.csv"),
        "tracto_dir": str(out_dir / "tracto"),
    }
