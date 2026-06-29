"""THOMAS thalamic atlas labels and the four-nucleus subset used in Piper et al. 2026.

THOMAS produces eight bilateral thalamic nuclei. The paper restricts analysis to
four: AV (anteroventral), CM (centromedian), MDPf (mediodorsal-parafascicular)
and PUL (pulvinar). Geniculates are dropped (not relevant); habenular and
mammillothalamic tracts are dropped (too small to seed tractography).

The label IDs below match the canonical THOMAS T1w output. THOMAS itself
writes each nucleus to its own NIfTI file, so the ``LABEL_IDS`` mapping
is the convention this package adopts when those files are later merged
into a single label image (see ``nodestrength.pipeline.thomas.merge_labels``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

# Canonical THOMAS nucleus filenames -> integer labels assigned by this package
# when merging the individual masks into one volume.
THOMAS_NUCLEI: Tuple[str, ...] = (
    "AV",     # anteroventral
    "VA",     # ventral anterior
    "VLa",    # ventral lateral anterior
    "VLP",    # ventral lateral posterior
    "VPL",    # ventral posterolateral
    "PUL",    # pulvinar
    "CM",     # centromedian
    "MDPf",   # mediodorsal-parafascicular
)

# The four nuclei analyzed in the paper (Section 2.6).
ANALYZED_NUCLEI: Tuple[str, ...] = ("AV", "CM", "MDPf", "PUL")


def _label_ids(offset: int) -> Dict[str, int]:
    return {name: offset + i for i, name in enumerate(THOMAS_NUCLEI)}


LEFT_LABEL_OFFSET = 8100
RIGHT_LABEL_OFFSET = 8200

LEFT_LABELS: Dict[str, int] = _label_ids(LEFT_LABEL_OFFSET)
RIGHT_LABELS: Dict[str, int] = _label_ids(RIGHT_LABEL_OFFSET)


@dataclass(frozen=True)
class ThalamicROI:
    name: str           # e.g. "AV"
    side: str           # "L" or "R"
    label_id: int       # integer label in the merged Lausanne+THOMAS image

    @property
    def key(self) -> str:
        return f"{self.side}.{self.name}"


def all_rois() -> List[ThalamicROI]:
    """All 16 THOMAS ROIs (8 nuclei × 2 sides) as ``ThalamicROI`` records."""
    rois: List[ThalamicROI] = []
    for name in THOMAS_NUCLEI:
        rois.append(ThalamicROI(name=name, side="L", label_id=LEFT_LABELS[name]))
        rois.append(ThalamicROI(name=name, side="R", label_id=RIGHT_LABELS[name]))
    return rois


def analyzed_rois() -> List[ThalamicROI]:
    """The 8 ROIs analyzed in the paper (4 nuclei × 2 sides)."""
    return [r for r in all_rois() if r.name in ANALYZED_NUCLEI]
