"""Minimal clinical PDF report from nodestrength CSV outputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from nodestrength.dk_inputs import subject_file_prefix

KEY_ROIS: Tuple[Tuple[str, str], ...] = (
    ("Thalamus-Proper", "Thalamus"),
    ("Hippocampus", "Hippocampus"),
    ("Amygdala", "Amygdala"),
    ("insula", "Insula"),
)

_FIGURE_CAPTIONS: Dict[str, str] = {
    "subcortical_panel.png": "Subcortical node strength and interhemispheric asymmetry.",
    "absolute_asymmetry_top.png": "Regions with largest absolute strength asymmetry (|side_ai|).",
    "enigma_cortical_abs_ai.png": "Cortical strength asymmetry (|side AI|) on inflated surfaces.",
}

_TABLE_STYLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ("TOPPADDING", (0, 0), (-1, -1), 3),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
])


def _essential_report_figures(fig_dir: Path) -> Tuple[Tuple[str, Tuple[str, ...]], ...]:
    """Clinical PDF figures: cortical brain map + subcortical panel only."""
    pages: List[Tuple[str, Tuple[str, ...]]] = []
    cortical: List[str] = []
    if (fig_dir / "enigma_cortical_abs_ai.png").is_file():
        cortical.append("enigma_cortical_abs_ai.png")
    elif (fig_dir / "absolute_asymmetry_top.png").is_file():
        cortical.append("absolute_asymmetry_top.png")
    if cortical:
        pages.append(("Cortical asymmetry", tuple(cortical)))
    if (fig_dir / "subcortical_panel.png").is_file():
        pages.append(("Subcortical summary", ("subcortical_panel.png",)))
    return tuple(pages)


@dataclass(frozen=True)
class SubjectReportInput:
    folder_name: str
    connectome_csv: Optional[Path] = None
    subject_dir: Optional[Path] = None
    fs_subject_dir: Optional[Path] = None


def _fmt_ai(value: float) -> str:
    if not np.isfinite(value):
        return "—"
    direction = "L > R" if value > 0 else ("R > L" if value < 0 else "symmetric")
    return f"{value:+.3f} ({direction})"


_CLINICAL_CAVEAT = (
    "<b>Note:</b> Strength AI values are raw asymmetry indices (not normative z-scores). "
    "Whole thalamus only (not THOMAS nuclei). "
    "Intra AI uses within-hemisphere edges only (excludes callosal connections). "
    "Interpret alongside clinical history and MRI."
)


def _load_report_tables(
    results_dir: Path,
    folder_name: str,
) -> Tuple[pd.DataFrame, Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Load CSV tables used by the lean clinical PDF (no SOZ / normative z)."""
    prefix = subject_file_prefix(folder_name)
    per_subject = results_dir / "strength" / "per_subject"
    strength_ai = pd.read_csv(per_subject / f"{prefix}_ai.csv")

    intra_path = per_subject / f"{prefix}_ai_intra.csv"
    intra_ai = pd.read_csv(intra_path) if intra_path.is_file() else None

    volume_path = results_dir / "volume" / "per_subject" / f"{prefix}_volume_ai.csv"
    volume_ai = pd.read_csv(volume_path) if volume_path.is_file() else None

    return strength_ai, intra_ai, volume_ai


def _top_asymmetry(ai: pd.DataFrame, n: int = 5, value_col: str = "side_ai") -> pd.DataFrame:
    df = ai.copy()
    df["abs_ai"] = df[value_col].abs()
    return df.sort_values("abs_ai", ascending=False).head(n)


def _key_metrics(
    strength_ai: pd.DataFrame,
    volume_ai: Optional[pd.DataFrame],
    intra_ai: Optional[pd.DataFrame],
) -> Tuple[List[Dict[str, str]], List[str]]:
    """Build key-structure rows for the clinical PDF."""
    headers = ["Structure", "Str AI", "Intra AI", "Vol AI"]

    rows: List[Dict[str, str]] = []
    for roi_key, label in KEY_ROIS:
        srow = strength_ai.loc[strength_ai["roi_name"] == roi_key].iloc[0]
        entry: Dict[str, str] = {
            "label": label,
            "strength_ai": _fmt_ai(float(srow["side_ai"])),
        }
        if intra_ai is not None and roi_key in set(intra_ai["roi_name"]):
            irow = intra_ai.loc[intra_ai["roi_name"] == roi_key].iloc[0]
            entry["intra_ai"] = _fmt_ai(float(irow["side_ai"]))
        else:
            entry["intra_ai"] = "—"
        if volume_ai is not None and roi_key in set(volume_ai["roi_name"]):
            vrow = volume_ai.loc[volume_ai["roi_name"] == roi_key].iloc[0]
            entry["volume_ai"] = _fmt_ai(float(vrow["side_ai"]))
        else:
            entry["volume_ai"] = "—"
        rows.append(entry)

    return rows, headers


def _metrics_table_rows(metrics: List[Dict[str, str]], headers: List[str]) -> List[List[str]]:
    key_map = {
        "Structure": "label",
        "Str AI": "strength_ai",
        "Intra AI": "intra_ai",
        "Vol AI": "volume_ai",
    }
    return [[m[key_map[h]] for h in headers] for m in metrics]


def _figure_story(fig_path: Path, caption: str, body_style: ParagraphStyle,
                  max_width: float = 6.5 * inch) -> List:
    if not fig_path.is_file():
        return []
    img = Image(str(fig_path))
    iw, ih = img.imageWidth, img.imageHeight
    if iw <= 0:
        return []
    scale = min(max_width / iw, 1.0)
    img.drawWidth = iw * scale
    img.drawHeight = ih * scale
    return [
        img,
        Spacer(1, 0.05 * inch),
        Paragraph(caption, ParagraphStyle(
            "FigCaption", parent=body_style, fontSize=8, textColor=colors.grey,
        )),
        Spacer(1, 0.12 * inch),
    ]


def generate_clinical_report(
    results_dir: Path,
    folder_name: str,
    *,
    connectome_csv: Optional[Path] = None,
    subject_dir: Optional[Path] = None,
    fs_subject_dir: Optional[Path] = None,
    participants_path: Optional[Path] = None,
    normative_model_path: Optional[Path] = None,
    control_group: str = "control",
    version: str = "0.1.0",
    with_figures: bool = True,
) -> Path:
    """Write ``reports/<subject>/report.pdf`` under ``results_dir``.

    Lean clinician-facing layout: key structures + top-5 standard/intra AI tables,
    cortical |AI| map, and subcortical panel. Raw AI only (no SOZ AI or normative z).
    """
    strength_ai, intra_ai, volume_ai = _load_report_tables(results_dir, folder_name)

    prefix = subject_file_prefix(folder_name)
    metrics, key_headers = _key_metrics(strength_ai, volume_ai, intra_ai)
    top5 = _top_asymmetry(strength_ai, n=5)
    top5_intra = _top_asymmetry(intra_ai, n=5) if intra_ai is not None else None

    report_dir = results_dir / "reports" / prefix
    report_dir.mkdir(parents=True, exist_ok=True)
    out_path = report_dir / "report.pdf"

    figure_paths: List[Path] = []
    if with_figures:
        from nodestrength.report_viz import generate_report_figures
        figure_paths = generate_report_figures(
            results_dir,
            folder_name,
            connectome_csv=connectome_csv,
            subject_dir=subject_dir,
            fs_subject_dir=fs_subject_dir,
        )

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Heading1"], fontSize=16, spaceAfter=6,
    )
    section_style = ParagraphStyle(
        "Section", parent=styles["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"], fontSize=10, leading=13,
    )
    caveat_style = ParagraphStyle(
        "Caveat", parent=body_style, backColor=colors.HexColor("#fff8e1"),
        borderPadding=6, spaceBefore=6, spaceAfter=10,
    )

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    story = [
        Paragraph(f"Node strength clinical summary — {prefix}", title_style),
        Paragraph(
            f"Generated {generated} · nodestrength {version} · Desikan–Killiany (84 nodes)",
            body_style,
        ),
        Paragraph(_CLINICAL_CAVEAT, caveat_style),
        Paragraph("Key structures", section_style),
    ]

    col_width = 7.3 * inch / len(key_headers)
    key_table = Table(
        [key_headers] + _metrics_table_rows(metrics, key_headers),
        colWidths=[col_width] * len(key_headers),
    )
    key_table.setStyle(_TABLE_STYLE)
    story.extend([key_table, Spacer(1, 0.15 * inch)])

    story.append(Paragraph("Top 5 strength asymmetry", section_style))
    top_table = Table(
        [["#", "Region", "Strength AI"]]
        + [
            [str(i + 1), str(row.roi_name), f"{float(row.side_ai):+.3f}"]
            for i, row in top5.reset_index(drop=True).iterrows()
        ],
        colWidths=[0.4 * inch, 3.0 * inch, 1.2 * inch],
    )
    top_table.setStyle(_TABLE_STYLE)
    story.extend([top_table, Spacer(1, 0.12 * inch)])

    if top5_intra is not None:
        story.append(Paragraph("Top 5 intrahemispheric asymmetry", section_style))
        intra_table = Table(
            [["#", "Region", "Intra AI"]]
            + [
                [str(i + 1), str(row.roi_name), f"{float(row.side_ai):+.3f}"]
                for i, row in top5_intra.reset_index(drop=True).iterrows()
            ],
            colWidths=[0.4 * inch, 3.0 * inch, 1.2 * inch],
        )
        intra_table.setStyle(_TABLE_STYLE)
        story.extend([intra_table, Spacer(1, 0.15 * inch)])

    if with_figures and figure_paths:
        fig_dir = report_dir / "figures"
        report_pages = _essential_report_figures(fig_dir)
        if any((fig_dir / n).is_file() for _, names in report_pages for n in names):
            story.append(PageBreak())
            for section_title, names in report_pages:
                section_figs = [fig_dir / n for n in names if (fig_dir / n).is_file()]
                if not section_figs:
                    continue
                story.append(Paragraph(section_title, section_style))
                for fig_path in section_figs:
                    story.extend(_figure_story(
                        fig_path,
                        _FIGURE_CAPTIONS.get(fig_path.name, fig_path.name),
                        body_style,
                    ))

    footer = (
        "Research use · SIFT2-weighted DK connectome · "
        "side_ai = (L−R)/(L+R) · intra AI = within-hemisphere edges only"
    )
    story.append(Paragraph(
        footer,
        ParagraphStyle("Footer", parent=body_style, fontSize=8, textColor=colors.grey),
    ))

    doc.build(story)
    return out_path


def generate_cohort_reports(
    results_dir: Path,
    subjects: Union[List[str], List[SubjectReportInput]],
    *,
    participants_path: Optional[Path] = None,
    normative_model_path: Optional[Path] = None,
    control_group: str = "control",
) -> List[Path]:
    """Generate PDF reports for all listed subjects."""
    paths: List[Path] = []
    for item in subjects:
        if isinstance(item, SubjectReportInput):
            paths.append(generate_clinical_report(
                results_dir,
                item.folder_name,
                connectome_csv=item.connectome_csv,
                subject_dir=item.subject_dir,
                fs_subject_dir=item.fs_subject_dir,
                participants_path=participants_path,
                normative_model_path=normative_model_path,
                control_group=control_group,
            ))
        else:
            paths.append(generate_clinical_report(
                results_dir,
                item,
                participants_path=participants_path,
                normative_model_path=normative_model_path,
                control_group=control_group,
            ))
    return paths
