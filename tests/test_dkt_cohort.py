"""End-to-end dkt-ai-cohort on a real 78-node connectome when available."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from nodestrength.connectome import load_connectome
from nodestrength.dk_cohort import main as cohort_main

_DKT_CONNECTOME = Path(
    "/mnt/nfs/home/urmc-sh.rochester.edu/pndagiji/Documents/CIDUR_BIDS/"
    "dwi_test2_dkt/connectomes/sub-TBI011204/dkt_connectome.csv"
)


@pytest.mark.skipif(not _DKT_CONNECTOME.is_file(), reason="NFS DKT connectome not mounted")
def test_cohort_on_78_node_dkt_connectome(tmp_path):
    W = load_connectome(_DKT_CONNECTOME)
    assert W.shape == (78, 78)

    root = tmp_path / "connectomes"
    sub = root / "sub-TBI011204"
    sub.mkdir(parents=True)
    np.savetxt(sub / "dkt_connectome.csv", W, delimiter=",")

    out = tmp_path / "out"
    rc = cohort_main([
        "--root", str(root),
        "--out", str(out),
        "--include", "TBI011204",
        "--no-report",
    ])
    assert rc == 0
    strength = out / "strength" / "per_subject" / "sub-TBI011204_strength.csv"
    assert strength.is_file()
    import pandas as pd
    df = pd.read_csv(strength)
    assert len(df) == 78
    assert (out / "manifest.json").is_file()
