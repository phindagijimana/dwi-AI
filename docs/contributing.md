# Contributing and GitHub

The canonical repository is **[github.com/phindagijimana/dwi-AI](https://github.com/phindagijimana/dwi-AI)**.

This documentation site is the `docs/` tree in that repo, built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) and published to GitHub Pages:

```text
https://phindagijimana.github.io/dwi-AI/
```

## Issues and pull requests

Open issues and PRs on GitHub. Useful PR types:

- CLI help text and exit codes
- Atlas pairing tables
- Tests under `tests/`
- Documentation (especially science pages and citations)

Please do **not** open PRs that add:

- Identified clinical CSVs, Figshare dumps, or `Mahi_Project/` trees
- Secrets, tokens, or institutional paths
- Exploit-style “attack” notebooks

## Local docs preview

```bash
pip install mkdocs-material
mkdocs serve
# http://127.0.0.1:8000
```

Pages live in `docs/`; navigation is `mkdocs.yml`. After merge to `main`, the `docs` GitHub Action runs `mkdocs gh-deploy`.

## Development install

```bash
git clone https://github.com/phindagijimana/dwi-AI.git
cd dwi-AI
pip install -e ".[dev,bct]"
pytest
```

## Code layout

| Path | Role |
|---|---|
| `nodestrength/cli.py` | `nodestrength` subcommands |
| `nodestrength/dk_cohort.py` | `dkt-ai-cohort` |
| `nodestrength/*.py` | strength, AI, ingest, reports |
| `docs/` | this site |
| `research/` | study-specific runners (not the public API) |

## Contact

**Philbert Ndagijimana** — [phindagijimana@gmail.com](mailto:phindagijimana@gmail.com)

Use that address or [GitHub issues](https://github.com/phindagijimana/dwi-AI/issues) for the software, documentation, and containers. For the Piper et al. 2026 clinical study, cite the paper rather than filing dataset requests here. How to cite: [Citing and contact](citing.md).
