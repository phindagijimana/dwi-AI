import subprocess
import sys
from pathlib import Path

import numpy as np

from nodestrength.atlases import all_rois


def write_connectome(path: Path, mat):
    with path.open("w") as fh:
        for row in mat:
            fh.write(",".join(str(float(x)) for x in row) + "\n")


def write_lookup(path: Path, names):
    with path.open("w") as fh:
        for i, n in enumerate(names, start=1):
            fh.write(f"{i}\t{n}\n")


def test_score_connectomes_script(tmp_path):
    root = tmp_path / "derivatives"
    root.mkdir()
    sub = root / "sub-TEST"
    sub.mkdir()

    names = [r.key for r in all_rois()]
    n = len(names)
    rng = np.random.default_rng(0)
    mat = rng.uniform(0.1, 1.0, size=(n, n))
    mat = (mat + mat.T) / 2.0
    np.fill_diagonal(mat, 0.0)
    write_connectome(sub / "connectome.csv", mat.tolist())
    write_lookup(sub / "node_lookup.tsv", names)

    out = tmp_path / "out"
    cmd = [sys.executable, "scripts/score_connectomes.py", "--root", str(root), "--out", str(out)]
    r = subprocess.run(cmd, cwd=Path.cwd())
    assert r.returncode == 0
    per = out / "per_subject"
    assert per.exists()
    files = list(per.iterdir())
    assert any(f.name.endswith("per_subject_record.csv") for f in files)
