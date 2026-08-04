"""Tests for ENIGMA-style report visualizations."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from nodestrength.clinical_report import generate_clinical_report
from nodestrength.dk_atlas import build_dk_nodes
from nodestrength.report_viz import (
    _parcel_to_fsa5_vertices,
    _dk_bilateral_cortical,
    generate_report_figures,
    plot_absolute_asymmetry_top,
    plot_cortical_strength_map,
    plot_homotopic_interhemispheric,
    plot_hub_strength_top,
    plot_seed_profile,
    plot_subcortical_panel,
    plot_subcortical_intra_panel,
    plot_standard_vs_intra_ai,
    plot_thalamus_seed_profile,
)


def _write_full_strength(out: Path, subject: str = "001") -> None:
    strength_ps = out / "strength" / "per_subject"
    strength_ps.mkdir(parents=True, exist_ok=True)
    rows = []
    for n in build_dk_nodes():
        val = float(n.fs_default_index) * 1000.0
        rows.append({
            "subject": subject,
            "fs_default_index": n.fs_default_index,
            "name": n.name,
            "side": n.side,
            "region_type": n.region_type,
            "strength": val,
        })
    pd.DataFrame(rows).to_csv(strength_ps / f"sub-{subject}_strength.csv", index=False)


def _write_minimal_ai(out: Path, subject: str = "001") -> None:
    strength_ps = out / "strength" / "per_subject"
    strength_ps.mkdir(parents=True, exist_ok=True)
    ai_rows = [
        {"subject": subject, "roi_name": "Thalamus-Proper", "region_type": "subcortical",
         "L_index": 36, "R_index": 43, "L_strength": 100.0, "R_strength": 90.0,
         "side_ai": 0.05, "log_ai": 0.1},
        {"subject": subject, "roi_name": "Hippocampus", "region_type": "subcortical",
         "L_index": 40, "R_index": 47, "L_strength": 50.0, "R_strength": 48.0,
         "side_ai": 0.02, "log_ai": 0.04},
        {"subject": subject, "roi_name": "Amygdala", "region_type": "subcortical",
         "L_index": 41, "R_index": 48, "L_strength": 30.0, "R_strength": 35.0,
         "side_ai": -0.08, "log_ai": -0.16},
        {"subject": subject, "roi_name": "Caudate", "region_type": "subcortical",
         "L_index": 37, "R_index": 44, "L_strength": 40.0, "R_strength": 42.0,
         "side_ai": -0.02, "log_ai": -0.04},
        {"subject": subject, "roi_name": "Putamen", "region_type": "subcortical",
         "L_index": 38, "R_index": 45, "L_strength": 45.0, "R_strength": 44.0,
         "side_ai": 0.01, "log_ai": 0.02},
        {"subject": subject, "roi_name": "Pallidum", "region_type": "subcortical",
         "L_index": 39, "R_index": 46, "L_strength": 20.0, "R_strength": 21.0,
         "side_ai": -0.02, "log_ai": -0.04},
        {"subject": subject, "roi_name": "Accumbens-area", "region_type": "subcortical",
         "L_index": 42, "R_index": 49, "L_strength": 10.0, "R_strength": 11.0,
         "side_ai": -0.05, "log_ai": -0.10},
        {"subject": subject, "roi_name": "insula", "region_type": "cortex",
         "L_index": 34, "R_index": 83, "L_strength": 60.0, "R_strength": 62.0,
         "side_ai": -0.02, "log_ai": -0.04},
        {"subject": subject, "roi_name": "temporalpole", "region_type": "cortex",
         "L_index": 32, "R_index": 81, "L_strength": 20.0, "R_strength": 10.0,
         "side_ai": 0.33, "log_ai": 0.66},
    ]
    pd.DataFrame(ai_rows).to_csv(strength_ps / f"sub-{subject}_ai.csv", index=False)


def _write_minimal_intra(out: Path, subject: str = "001") -> None:
    """Intrahemispheric strength + AI fixtures (subset mirrors _write_minimal_ai)."""
    strength_ps = out / "strength" / "per_subject"
    strength_ps.mkdir(parents=True, exist_ok=True)
    rows = []
    for n in build_dk_nodes():
        val = float(n.fs_default_index) * 800.0
        rows.append({
            "subject": subject,
            "fs_default_index": n.fs_default_index,
            "name": n.name,
            "side": n.side,
            "region_type": n.region_type,
            "strength_intra": val,
        })
    pd.DataFrame(rows).to_csv(strength_ps / f"sub-{subject}_strength_intra.csv", index=False)

    ai_rows = [
        {"subject": subject, "roi_name": "Thalamus-Proper", "region_type": "subcortical",
         "L_index": 36, "R_index": 43, "L_strength_intra": 80.0, "R_strength_intra": 85.0,
         "side_ai": -0.03, "log_ai": -0.06},
        {"subject": subject, "roi_name": "Hippocampus", "region_type": "subcortical",
         "L_index": 40, "R_index": 47, "L_strength_intra": 40.0, "R_strength_intra": 38.0,
         "side_ai": 0.03, "log_ai": 0.06},
        {"subject": subject, "roi_name": "Amygdala", "region_type": "subcortical",
         "L_index": 41, "R_index": 48, "L_strength_intra": 25.0, "R_strength_intra": 28.0,
         "side_ai": -0.06, "log_ai": -0.12},
        {"subject": subject, "roi_name": "Caudate", "region_type": "subcortical",
         "L_index": 37, "R_index": 44, "L_strength_intra": 35.0, "R_strength_intra": 36.0,
         "side_ai": -0.01, "log_ai": -0.02},
        {"subject": subject, "roi_name": "Putamen", "region_type": "subcortical",
         "L_index": 38, "R_index": 45, "L_strength_intra": 40.0, "R_strength_intra": 39.0,
         "side_ai": 0.01, "log_ai": 0.02},
        {"subject": subject, "roi_name": "Pallidum", "region_type": "subcortical",
         "L_index": 39, "R_index": 46, "L_strength_intra": 18.0, "R_strength_intra": 19.0,
         "side_ai": -0.03, "log_ai": -0.06},
        {"subject": subject, "roi_name": "Accumbens-area", "region_type": "subcortical",
         "L_index": 42, "R_index": 49, "L_strength_intra": 8.0, "R_strength_intra": 9.0,
         "side_ai": -0.06, "log_ai": -0.12},
        {"subject": subject, "roi_name": "insula", "region_type": "cortex",
         "L_index": 34, "R_index": 83, "L_strength_intra": 55.0, "R_strength_intra": 58.0,
         "side_ai": -0.03, "log_ai": -0.06},
        {"subject": subject, "roi_name": "temporalpole", "region_type": "cortex",
         "L_index": 32, "R_index": 81, "L_strength_intra": 18.0, "R_strength_intra": 9.0,
         "side_ai": 0.33, "log_ai": 0.66},
    ]
    pd.DataFrame(ai_rows).to_csv(strength_ps / f"sub-{subject}_ai_intra.csv", index=False)


def _write_connectome(path: Path) -> None:
    rng = np.random.default_rng(0)
    W = rng.random((84, 84))
    W = (W + W.T) / 2
    np.fill_diagonal(W, 0)
    W[35, 0:34] = np.linspace(100, 500, 34)
    W[42, 49:83] = np.linspace(120, 520, 34)
    pd.DataFrame(W).to_csv(path, index=False, header=False)


def test_plot_subcortical_panel(tmp_path: Path) -> None:
    _write_full_strength(tmp_path)
    _write_minimal_ai(tmp_path)
    strength = pd.read_csv(tmp_path / "strength" / "per_subject" / "sub-001_strength.csv")
    ai = pd.read_csv(tmp_path / "strength" / "per_subject" / "sub-001_ai.csv")
    out = plot_subcortical_panel(strength, ai, tmp_path / "subcortical.png")
    assert out.is_file()
    assert out.stat().st_size > 1000


def test_plot_subcortical_intra_panel(tmp_path: Path) -> None:
    _write_minimal_intra(tmp_path)
    strength_intra = pd.read_csv(
        tmp_path / "strength" / "per_subject" / "sub-001_strength_intra.csv")
    ai_intra = pd.read_csv(tmp_path / "strength" / "per_subject" / "sub-001_ai_intra.csv")
    out = plot_subcortical_intra_panel(strength_intra, ai_intra, tmp_path / "intra_panel.png")
    assert out.is_file()
    assert out.stat().st_size > 1000


def test_plot_standard_vs_intra_ai(tmp_path: Path) -> None:
    _write_minimal_ai(tmp_path)
    _write_minimal_intra(tmp_path)
    strength_ai = pd.read_csv(tmp_path / "strength" / "per_subject" / "sub-001_ai.csv")
    ai_intra = pd.read_csv(tmp_path / "strength" / "per_subject" / "sub-001_ai_intra.csv")
    out = plot_standard_vs_intra_ai(strength_ai, ai_intra, tmp_path / "compare.png")
    assert out.is_file()


def test_plot_cortical_strength_map(tmp_path: Path) -> None:
    _write_full_strength(tmp_path)
    strength = pd.read_csv(tmp_path / "strength" / "per_subject" / "sub-001_strength.csv")
    out = plot_cortical_strength_map(strength, tmp_path / "cortical.png")
    assert out.is_file()


def test_thalamus_seed_profile(tmp_path: Path) -> None:
    conn = tmp_path / "dkt_connectome.csv"
    _write_connectome(conn)
    out = plot_thalamus_seed_profile(conn, tmp_path / "thalamus.png")
    assert out.is_file()


def test_hippocampus_and_amygdala_seed_profiles(tmp_path: Path) -> None:
    conn = tmp_path / "dkt_connectome.csv"
    _write_connectome(conn)
    for key in ("hippocampus", "amygdala"):
        out = plot_seed_profile(conn, tmp_path / f"{key}.png", key)
        assert out.is_file()


def test_homotopic_and_hub_plots(tmp_path: Path) -> None:
    _write_full_strength(tmp_path)
    _write_minimal_ai(tmp_path)
    strength = pd.read_csv(tmp_path / "strength" / "per_subject" / "sub-001_strength.csv")
    ai = pd.read_csv(tmp_path / "strength" / "per_subject" / "sub-001_ai.csv")
    assert plot_absolute_asymmetry_top(ai, tmp_path / "abs_ai.png").is_file()
    assert plot_hub_strength_top(strength, tmp_path / "hubs.png").is_file()
    conn = tmp_path / "dkt_connectome.csv"
    _write_connectome(conn)
    assert plot_homotopic_interhemispheric(conn, tmp_path / "homo.png").is_file()


def test_parcel_to_fsa5_vertices() -> None:
    vals = _dk_bilateral_cortical([float(i) for i in range(34)])
    vert = _parcel_to_fsa5_vertices(vals)
    assert vert.shape == (20484,)
    assert vert.max() == 33.0


def test_generate_report_figures(tmp_path: Path) -> None:
    _write_full_strength(tmp_path)
    _write_minimal_ai(tmp_path)
    paths = generate_report_figures(tmp_path, "sub-001", use_enigma_surfaces=True)
    assert len(paths) == 2
    assert all(p.is_file() for p in paths)
    names = {p.name for p in paths}
    assert names == {"subcortical_panel.png", "enigma_cortical_abs_ai.png"}


def test_generate_report_figures_bar_fallback(tmp_path: Path) -> None:
    _write_full_strength(tmp_path)
    _write_minimal_ai(tmp_path)
    paths = generate_report_figures(tmp_path, "sub-001", use_enigma_surfaces=False)
    names = {p.name for p in paths}
    assert names == {"subcortical_panel.png", "absolute_asymmetry_top.png"}


def test_clinical_report_with_figures(tmp_path: Path) -> None:
    _write_full_strength(tmp_path)
    _write_minimal_ai(tmp_path)
    pdf = generate_clinical_report(tmp_path, "sub-001")
    assert pdf.is_file()
    assert pdf.stat().st_size > 5000
    fig_dir = tmp_path / "reports" / "sub-001" / "figures"
    assert (fig_dir / "subcortical_panel.png").is_file()
    assert (fig_dir / "enigma_cortical_abs_ai.png").is_file()
    assert not (fig_dir / "thalamus_seed_profile.png").exists()
    assert not (fig_dir / "subcortical_intra_panel.png").exists()
