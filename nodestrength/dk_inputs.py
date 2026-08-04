"""Discover DKT connectome inputs from user-provided directories (site-agnostic)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

CONNECTOME_FILENAMES: Tuple[str, ...] = (
    "dkt_connectome.csv",
    "dk_connectome.csv",  # legacy QSIRecon naming
    "connectome.csv",
)
LABEL_FILENAMES: Tuple[str, ...] = (
    "dk_nodes.mif",
)


@dataclass(frozen=True)
class SubjectInputs:
    """Resolved on-disk inputs for one subject."""

    subject_dir: Path
    folder_name: str
    subject_id: str
    connectome_csv: Path
    label_mif: Optional[Path] = None
    fs_subject_dir: Optional[Path] = None


def subject_id_from_folder(folder_name: str) -> str:
    """Normalize folder name to a subject id (strip BIDS ``sub-`` when present)."""
    return folder_name[4:] if folder_name.startswith("sub-") else folder_name


def subject_file_prefix(folder_name: str) -> str:
    """Prefix used in output filenames (``sub-XXX`` when folder uses BIDS naming)."""
    return folder_name if folder_name.startswith("sub-") else f"sub-{folder_name}"


def find_connectome_csv(subject_dir: Path) -> Optional[Path]:
    for name in CONNECTOME_FILENAMES:
        path = subject_dir / name
        if path.is_file():
            return path
    return None


def find_label_mif(subject_dir: Path, fs_root: Optional[Path], folder_name: str) -> Optional[Path]:
    for name in LABEL_FILENAMES:
        path = subject_dir / name
        if path.is_file():
            return path
    if fs_root is None:
        return None
    fs_subject = fs_root / folder_name
    if not fs_subject.is_dir():
        alt = fs_root / subject_id_from_folder(folder_name)
        if alt.is_dir():
            fs_subject = alt
        else:
            return None
    for name in LABEL_FILENAMES:
        path = fs_subject / name
        if path.is_file():
            return path
    return None


def find_fs_subject_dir(fs_root: Optional[Path], folder_name: str) -> Optional[Path]:
    if fs_root is None:
        return None
    direct = fs_root / folder_name
    if direct.is_dir():
        return direct
    alt = fs_root / subject_id_from_folder(folder_name)
    if alt.is_dir():
        return alt
    return None


def discover_subjects(root: Path, fs_root: Optional[Path] = None) -> List[SubjectInputs]:
    """Return subjects with a connectome CSV under ``root`` (any folder name).

    Expected layout (per site):

        CONNECTOME_ROOT/<subject>/dkt_connectome.csv
        CONNECTOME_ROOT/<subject>/dk_nodes.mif          # optional here
        FS_ROOT/<subject>/                              # optional cross-check

    Folder names may be BIDS ``sub-XXX`` or any other subject identifier.
    """
    if not root.is_dir():
        return []

    subjects: List[SubjectInputs] = []
    for subject_dir in sorted(root.iterdir()):
        if not subject_dir.is_dir() or subject_dir.name.startswith("."):
            continue
        connectome = find_connectome_csv(subject_dir)
        if connectome is None:
            continue
        folder = subject_dir.name
        subjects.append(SubjectInputs(
            subject_dir=subject_dir,
            folder_name=folder,
            subject_id=subject_id_from_folder(folder),
            connectome_csv=connectome,
            label_mif=find_label_mif(subject_dir, fs_root, folder),
            fs_subject_dir=find_fs_subject_dir(fs_root, folder),
        ))
    return subjects


def filter_subjects(subjects: Sequence[SubjectInputs],
                    include: Optional[Sequence[str]]) -> List[SubjectInputs]:
    if not include:
        return list(subjects)
    wanted = {s.lstrip("sub-") for s in include}
    return [
        s for s in subjects
        if s.subject_id in wanted or s.folder_name in wanted
    ]
