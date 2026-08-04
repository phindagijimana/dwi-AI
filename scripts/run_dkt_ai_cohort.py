"""Run DK node-strength + asymmetry index on a directory of DKT connectomes.

Each subject folder must contain ``dkt_connectome.csv`` (84×84 SIFT2 connectome).
Legacy ``dk_connectome.csv`` / ``connectome.csv`` are also accepted.

Prefer ``dkt-ai-cohort`` or the container image for production runs.
"""

from __future__ import annotations

import sys

from nodestrength.dk_cohort import main

if __name__ == "__main__":
    raise SystemExit(main())
