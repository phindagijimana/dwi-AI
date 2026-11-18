# Installation

The analysis CLI is a Python package. Most users who already have connectome CSVs only need this install. Reconstruction (FOD, tractography, `tck2connectome`) is a separate problem: use [QSIPrep](https://qsiprep.readthedocs.io/) + QSIRecon, or the analysis [container](container.md) if you already have `dkt_connectome.csv` files.

## Requirements

- Python **3.9+** (3.12 recommended)
- A POSIX environment (Linux or macOS). Windows: use WSL2.
- Optional: Apptainer/Singularity or Docker for the standalone image
- Optional: `bctpy` for the canonical Brain Connectivity Toolbox backend (otherwise a matching NumPy `strengths_und` is used)

## Python package

From a clone of the [GitHub repository](https://github.com/phindagijimana/dwi-AI):

```bash
git clone https://github.com/phindagijimana/dwi-AI.git
cd dwi-AI
python -m venv .venv
source .venv/bin/activate
pip install -e ".[bct]"
```

Runtime dependencies (installed automatically): `numpy`, `pandas`, `scipy`, `nibabel`, `reportlab`, `matplotlib`, `nilearn`.

This registers three console scripts:

| Command | Module | Typical use |
|---|---|---|
| `nodestrength` | `nodestrength.cli:main` | Subcommand CLI (inspect, ingest, asymmetry, GLM, …) |
| `dkt-ai-cohort` | `nodestrength.dk_cohort:main` | DK/DKT QSIRecon connectome folders |
| `dk-ai-cohort` | same | Legacy alias |

Confirm:

```bash
nodestrength --help
dkt-ai-cohort --help
```

## Optional extras

```bash
pip install -e ".[bct]"    # bctpy — canonical strengths_und
pip install -e ".[viz]"    # VTK + ENIGMA Toolbox surfaces for report maps
pip install -e ".[dev]"    # pytest
```

Normative z-scores use a small **OLS** implementation (no `statsmodels` required). Mixed-design GLM (Pillai’s trace, partial η²) uses NumPy/SciPy in `nodestrength.stats`.

## Documentation site (this site)

```bash
pip install mkdocs-material
mkdocs serve
```

Published at [phindagijimana.github.io/dwi-AI](https://phindagijimana.github.io/dwi-AI/). Source: `docs/` + `mkdocs.yml` in the repo.

## What you do **not** install here

`nodestrength` does **not** wrap QSIPrep. For BIDS dMRI preprocessing use [QSIPrep’s install guide](https://qsiprep.readthedocs.io/en/latest/installation.html), then QSIRecon (or MRtrix3) to write connectomes.
