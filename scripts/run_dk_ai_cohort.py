"""Backward-compatible wrapper — prefer ``dk-ai-cohort`` or the container image."""

from __future__ import annotations

import sys

from nodestrength.dk_cohort import main

if __name__ == "__main__":
    raise SystemExit(main())
