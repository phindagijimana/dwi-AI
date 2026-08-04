"""Backward-compatible wrapper — prefer ``run_dkt_ai_cohort.py`` or ``dkt-ai-cohort``."""

from __future__ import annotations

from nodestrength.dk_cohort import main

if __name__ == "__main__":
    raise SystemExit(main())
