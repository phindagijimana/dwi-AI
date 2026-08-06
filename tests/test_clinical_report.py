"""Tests for minimal clinical PDF reports."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from nodestrength.clinical_report import (
    _AI_COLUMN_DEFINITIONS,
    _key_metrics,
    _load_report_tables,
    _top_asymmetry,
    generate_clinical_report,
)
from nodestrength.dk_clinical import load_subject_clinical_tables
from tests.test_report_viz import _write_full_strength, _write_minimal_ai, _write_minimal_intra, _write_minimal_inter


def _write_minimal_volume_ai(out: Path, subject: str = "001") -> None:
    volume_ps = out / "volume" / "per_subject"
    volume_ps.mkdir(parents=True)
    vol_rows = [
        {"subject": subject, "roi_name": "Thalamus-Proper", "region_type": "subcortical",
         "L_index": 36, "R_index": 43, "L_volume_mm3": 8000.0, "R_volume_mm3": 8200.0,
         "side_ai": -0.01, "log_ai": -0.02},
        {"subject": subject, "roi_name": "Hippocampus", "region_type": "subcortical",
         "L_index": 40, "R_index": 47, "L_volume_mm3": 5000.0, "R_volume_mm3": 5200.0,
         "side_ai": -0.02, "log_ai": -0.04},
        {"subject": subject, "roi_name": "Amygdala", "region_type": "subcortical",
         "L_index": 41, "R_index": 48, "L_volume_mm3": 1800.0, "R_volume_mm3": 2200.0,
         "side_ai": -0.10, "log_ai": -0.20},
        {"subject": subject, "roi_name": "insula", "region_type": "cortex",
         "L_index": 34, "R_index": 83, "L_volume_mm3": 6000.0, "R_volume_mm3": 6100.0,
         "side_ai": -0.01, "log_ai": -0.02},
    ]
    pd.DataFrame(vol_rows).to_csv(volume_ps / f"sub-{subject}_volume_ai.csv", index=False)


def test_generate_clinical_report_pdf(tmp_path: Path) -> None:
    _write_full_strength(tmp_path)
    _write_minimal_ai(tmp_path)
    _write_minimal_intra(tmp_path)
    _write_minimal_inter(tmp_path)
    _write_minimal_volume_ai(tmp_path)
    pdf = generate_clinical_report(tmp_path, "sub-001", with_figures=False)
    assert pdf.name == "report.pdf"
    assert pdf.is_file()
    assert pdf.stat().st_size > 500


def test_ai_column_definitions_cover_table_headers() -> None:
    headers = ["Structure", "Str AI", "Intra AI", "Inter AI", "Vol AI"]
    for h in headers[1:]:
        assert h in _AI_COLUMN_DEFINITIONS
        assert _AI_COLUMN_DEFINITIONS[h].endswith(".")


def test_inter_ai_in_key_metrics_table(tmp_path: Path) -> None:
    _write_minimal_ai(tmp_path)
    _write_minimal_intra(tmp_path)
    _write_minimal_inter(tmp_path)
    strength_ai, intra_ai, inter_ai, volume_ai = _load_report_tables(tmp_path, "sub-001")
    metrics, headers = _key_metrics(strength_ai, volume_ai, intra_ai, inter_ai)
    assert headers == ["Structure", "Str AI", "Intra AI", "Inter AI", "Vol AI"]
    thalamus = next(m for m in metrics if m["label"] == "Thalamus")
    assert "−0.090" in thalamus["inter_ai"] or "-0.090" in thalamus["inter_ai"]


def test_intra_ai_loaded_for_report_tables(tmp_path: Path) -> None:
    _write_full_strength(tmp_path)
    _write_minimal_ai(tmp_path)
    _write_minimal_intra(tmp_path)
    tables = load_subject_clinical_tables(tmp_path, "sub-001")
    intra_ai = tables[1]
    assert intra_ai is not None
    top5_intra = _top_asymmetry(intra_ai, n=5)
    assert len(top5_intra) == 5
    assert "side_ai" in top5_intra.columns
