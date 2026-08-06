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
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from nodestrength.dk_inputs import subject_file_prefix

# --- Dark navy palette -------------------------------------------------------
NAVY = colors.HexColor("#0B1F3A")
NAVY_MID = colors.HexColor("#163556")
NAVY_LIGHT = colors.HexColor("#E8EEF5")
NAVY_MUTED = colors.HexColor("#5A6F8A")
WHITE = colors.white
ROW_ALT = colors.HexColor("#F3F6FA")
CAVEAT_BG = colors.HexColor("#EEF3F9")

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
    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
    ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("GRID", (0, 0), (-1, -1), 0.4, NAVY_MID),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("ALIGN", (1, 1), (-1, -1), "LEFT"),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, ROW_ALT]),
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
        pages.append(("Cortical Asymmetry", tuple(cortical)))
    if (fig_dir / "subcortical_panel.png").is_file():
        pages.append(("Subcortical Summary", ("subcortical_panel.png",)))
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
    "Intra AI uses within-hemisphere edges only; Inter AI uses cross-hemisphere (callosal) edges only. "
    "Interpret alongside clinical history and MRI. "
    "These results are for research use; anyone who uses them should take full responsibility."
)

_REPORT_TITLE = "Node Strength and Asymmetry Index Summary"

# One-line definitions shown under each AI column in the Key Structures table.
_AI_COLUMN_DEFINITIONS: Dict[str, str] = {
    "Str AI": "Left–right asymmetry in total node strength (all connectome edges).",
    "Intra AI": "Asymmetry in strength from within-hemisphere edges only (L↔L, R↔R).",
    "Inter AI": "Asymmetry in strength from cross-hemisphere edges only (L↔R).",
    "Vol AI": "Left–right asymmetry in ROI volume on the tractography grid.",
}


def _load_report_tables(
    results_dir: Path,
    folder_name: str,
) -> Tuple[pd.DataFrame, Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Load CSV tables used by the lean clinical PDF (no SOZ / normative z)."""
    prefix = subject_file_prefix(folder_name)
    per_subject = results_dir / "strength" / "per_subject"
    strength_ai = pd.read_csv(per_subject / f"{prefix}_ai.csv")

    intra_path = per_subject / f"{prefix}_ai_intra.csv"
    intra_ai = pd.read_csv(intra_path) if intra_path.is_file() else None

    inter_path = per_subject / f"{prefix}_ai_inter.csv"
    inter_ai = pd.read_csv(inter_path) if inter_path.is_file() else None

    volume_path = results_dir / "volume" / "per_subject" / f"{prefix}_volume_ai.csv"
    volume_ai = pd.read_csv(volume_path) if volume_path.is_file() else None

    return strength_ai, intra_ai, inter_ai, volume_ai


def _top_asymmetry(ai: pd.DataFrame, n: int = 5, value_col: str = "side_ai") -> pd.DataFrame:
    df = ai.copy()
    df["abs_ai"] = df[value_col].abs()
    return df.sort_values("abs_ai", ascending=False).head(n)


def _key_metrics(
    strength_ai: pd.DataFrame,
    volume_ai: Optional[pd.DataFrame],
    intra_ai: Optional[pd.DataFrame],
    inter_ai: Optional[pd.DataFrame],
) -> Tuple[List[Dict[str, str]], List[str]]:
    """Build key-structure rows for the clinical PDF."""
    headers = ["Structure", "Str AI", "Intra AI", "Inter AI", "Vol AI"]

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
        if inter_ai is not None and roi_key in set(inter_ai["roi_name"]):
            erow = inter_ai.loc[inter_ai["roi_name"] == roi_key].iloc[0]
            entry["inter_ai"] = _fmt_ai(float(erow["side_ai"]))
        else:
            entry["inter_ai"] = "—"
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
        "Inter AI": "inter_ai",
        "Vol AI": "volume_ai",
    }
    return [[m[key_map[h]] for h in headers] for m in metrics]


def _key_structures_table(
    headers: List[str],
    metrics: List[Dict[str, str]],
    *,
    def_style: ParagraphStyle,
) -> Table:
    """Key Structures table with a one-sentence definition row under each AI column."""
    def_row: List[Union[str, Paragraph]] = [""]
    for h in headers[1:]:
        text = _AI_COLUMN_DEFINITIONS.get(h, "")
        def_row.append(Paragraph(text, def_style) if text else "")
    data: List[List[Union[str, Paragraph]]] = [
        headers,
        def_row,
        *_metrics_table_rows(metrics, headers),
    ]
    col_width = 7.3 * inch / len(headers)
    table = Table(data, colWidths=[col_width] * len(headers))
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (-1, 1), NAVY_LIGHT),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Oblique"),
        ("FONTSIZE", (0, 1), (-1, 1), 7),
        ("TEXTCOLOR", (0, 1), (-1, 1), NAVY_MUTED),
        ("FONTNAME", (0, 2), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 2), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, NAVY_MID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 2), (-1, -1), "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 2), (-1, -1), [WHITE, ROW_ALT]),
    ]))
    return table


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
            "FigCaption", parent=body_style, fontSize=8, textColor=NAVY_MUTED,
        )),
        Spacer(1, 0.12 * inch),
    ]


def _draw_page_chrome(canv: pdfcanvas.Canvas, doc: SimpleDocTemplate) -> None:
    """Navy header bar + footer line on every page."""
    page_w, page_h = letter
    canv.saveState()

    # Top navy band
    header_h = 0.55 * inch
    canv.setFillColor(NAVY)
    canv.rect(0, page_h - header_h, page_w, header_h, fill=1, stroke=0)

    # Accent rule under header
    canv.setStrokeColor(NAVY_MID)
    canv.setLineWidth(2)
    canv.line(0.6 * inch, 0.55 * inch, page_w - 0.6 * inch, 0.55 * inch)

    canv.setFillColor(NAVY_MUTED)
    canv.setFont("Helvetica", 8)
    canv.drawString(0.6 * inch, 0.35 * inch, "Research use only")
    canv.drawRightString(page_w - 0.6 * inch, 0.35 * inch, f"Page {doc.page}")

    canv.restoreState()


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
    strength_ai, intra_ai, inter_ai, volume_ai = _load_report_tables(results_dir, folder_name)

    prefix = subject_file_prefix(folder_name)
    metrics, key_headers = _key_metrics(strength_ai, volume_ai, intra_ai, inter_ai)
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
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=NAVY,
        spaceAfter=4,
        spaceBefore=4,
        leading=22,
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontSize=9,
        textColor=NAVY_MUTED,
        leading=12,
        spaceAfter=8,
    )
    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=NAVY,
        spaceBefore=12,
        spaceAfter=6,
        borderPadding=0,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=13,
        textColor=NAVY,
    )
    caveat_style = ParagraphStyle(
        "Caveat",
        parent=body_style,
        fontSize=9,
        leading=12,
        textColor=NAVY,
        backColor=CAVEAT_BG,
        borderColor=NAVY_MID,
        borderWidth=1,
        borderPadding=8,
        spaceBefore=4,
        spaceAfter=12,
    )
    ai_def_style = ParagraphStyle(
        "AiDef",
        parent=body_style,
        fontSize=7,
        leading=9,
        textColor=NAVY_MUTED,
    )

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.85 * inch,
        bottomMargin=0.75 * inch,
        title=_REPORT_TITLE,
        author="nodestrength",
    )

    story = [
        Paragraph(_REPORT_TITLE, title_style),
        Paragraph(
            f"<b>{prefix}</b>  ·  Generated {generated}  ·  "
            f"nodestrength {version}  ·  DKT / DK ENIGMA maps",
            meta_style,
        ),
        Paragraph(_CLINICAL_CAVEAT, caveat_style),
        Paragraph("Key Structures", section_style),
    ]

    key_table = _key_structures_table(
        key_headers, metrics, def_style=ai_def_style,
    )
    story.extend([key_table, Spacer(1, 0.15 * inch)])

    story.append(Paragraph("Top 5 Strength Asymmetry", section_style))
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
        story.append(Paragraph("Top 5 Intrahemispheric Asymmetry", section_style))
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
                block = [Paragraph(section_title, section_style)]
                for fig_path in section_figs:
                    block.extend(_figure_story(
                        fig_path,
                        _FIGURE_CAPTIONS.get(fig_path.name, fig_path.name),
                        body_style,
                    ))
                story.append(KeepTogether(block))

    story.append(Paragraph(
        "All AI columns use side_ai = (L−R)/(L+R) on the measure named in the column header.",
        ParagraphStyle("FooterNote", parent=meta_style, fontSize=8, spaceBefore=10),
    ))

    doc.build(story, onFirstPage=_draw_page_chrome, onLaterPages=_draw_page_chrome)
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
