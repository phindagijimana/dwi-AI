"""Tests for site-agnostic DK input discovery."""

from pathlib import Path

from nodestrength.dk_inputs import (
    discover_subjects,
    filter_subjects,
    subject_file_prefix,
    subject_id_from_folder,
)


def test_subject_id_from_folder():
    assert subject_id_from_folder("sub-001") == "001"
    assert subject_id_from_folder("patient01") == "patient01"
    assert subject_file_prefix("sub-001") == "sub-001"
    assert subject_file_prefix("patient01") == "sub-patient01"


def test_discover_subjects_any_folder_name(tmp_path: Path):
    for name in ("sub-001", "patient02"):
        d = tmp_path / name
        d.mkdir()
        (d / "dkt_connectome.csv").write_text("0,1\n1,0\n")
    found = discover_subjects(tmp_path)
    assert [s.folder_name for s in found] == ["patient02", "sub-001"]


def test_discover_legacy_dk_connectome_csv(tmp_path: Path):
    d = tmp_path / "sub-legacy"
    d.mkdir()
    (d / "dk_connectome.csv").write_text("0,1\n1,0\n")
    found = discover_subjects(tmp_path)
    assert len(found) == 1
    assert found[0].connectome_csv.name == "dk_connectome.csv"


def test_discover_connectome_csv_alternate_name(tmp_path: Path):
    d = tmp_path / "sub-003"
    d.mkdir()
    (d / "connectome.csv").write_text("0,1\n1,0\n")
    found = discover_subjects(tmp_path)
    assert len(found) == 1
    assert found[0].connectome_csv.name == "connectome.csv"


def test_discover_dkt_connectome_csv(tmp_path: Path):
    d = tmp_path / "sub-005"
    d.mkdir()
    (d / "dkt_connectome.csv").write_text("0,1\n1,0\n")
    found = discover_subjects(tmp_path)
    assert len(found) == 1
    assert found[0].connectome_csv.name == "dkt_connectome.csv"


def test_dkt_connectome_preferred_over_legacy_name(tmp_path: Path):
    d = tmp_path / "sub-006"
    d.mkdir()
    (d / "dkt_connectome.csv").write_text("dkt\n")
    (d / "dk_connectome.csv").write_text("dk\n")
    found = discover_subjects(tmp_path)
    assert len(found) == 1
    assert found[0].connectome_csv.name == "dkt_connectome.csv"


def test_label_mif_from_fs_root(tmp_path: Path):
    connect = tmp_path / "connectomes"
    fs = tmp_path / "freesurfer"
    sub = connect / "sub-004"
    sub.mkdir(parents=True)
    (sub / "dkt_connectome.csv").write_text("0\n")
    fs_sub = fs / "sub-004"
    fs_sub.mkdir(parents=True)
    mif = fs_sub / "dk_nodes.mif"
    mif.write_text("mif")
    found = discover_subjects(connect, fs)
    assert found[0].label_mif == mif
    assert found[0].fs_subject_dir == fs_sub


def test_filter_subjects(tmp_path: Path):
    for name in ("sub-001", "sub-002"):
        d = tmp_path / name
        d.mkdir()
        (d / "dkt_connectome.csv").write_text("0\n")
    all_subs = discover_subjects(tmp_path)
    filtered = filter_subjects(all_subs, ["001"])
    assert [s.folder_name for s in filtered] == ["sub-001"]
