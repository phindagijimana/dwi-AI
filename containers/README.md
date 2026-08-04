# nodestrength — standalone analysis container

Independent Apptainer/Singularity image for **DK node strength**, **strength
interhemispheric AI**, **volume AI**, and **compare/** tables. Works like lab
imaging containers (`freesurfer_7.4.1.sif`, `qsiprep.sif`): copy or bind-mount
the `.sif`, mount data paths, run — **no repo checkout or Python env required**.

| Artifact | Purpose |
|---|---|
| `nodestrength_0.1.0.sif` | Versioned image (canonical name) |
| `run.sh` | Standalone launcher (copy beside the `.sif`) |
| `dwi-ai-analysis.sif` | Symlink to versioned name (backward compatible) |

**Default run:** strength + volume + compare + clinical PDF with ENIGMA-style brain maps.
Cortical inflated surfaces render via nilearn; subcortical 3D surfaces need ENIGMA Toolbox
(included in the container build). Use `--strength-only` to skip volume.

---

## Quick start (any user with Apptainer)

Provide **only** paths on your system — no lab- or repo-specific defaults.

```bash
SIF=/path/to/nodestrength_0.1.0.sif
CONNECT=/path/to/connectomes     # one folder per subject
OUT=/path/to/results             # writable
FS=/path/to/freesurfer/subjects  # optional — if dk_nodes.mif lives under FS

apptainer run --cleanenv \
  -B "$CONNECT:$CONNECT:ro" \
  -B "$OUT:$OUT" \
  ${FS:+-B "$FS:$FS:ro"} \
  "$SIF" \
  "$CONNECT" "$OUT" ${FS:+"$FS"}
```

Or use the bundled launcher (copy `run.sh` next to the `.sif`):

```bash
./run.sh /path/to/connectomes /path/to/results
./run.sh /path/to/connectomes /path/to/results /path/to/freesurfer/subjects
```

Help (no bind mounts needed):

```bash
apptainer run nodestrength_0.1.0.sif --help
```

---

## Inputs and outputs

**Per subject** — any folder name under `CONNECT/` (BIDS `sub-XXX` or other IDs):

| File | Required | Role |
|---|---|---|
| `dkt_connectome.csv` | yes | 84×84 symmetric SIFT2 connectome |
| `dk_nodes.mif` | for volume AI | MRtrix label grid — in connectome folder **or** `FS/<subject>/` |

Legacy connectome filenames (`dk_connectome.csv`, `connectome.csv`) are still
accepted. The CLI alias `dk-ai-cohort` remains available.

**Output** under `OUT/`:

```
strength/per_subject/sub-XXX_strength.csv
strength/per_subject/sub-XXX_ai.csv
volume/per_subject/sub-XXX_volume.csv      # default on
volume/per_subject/sub-XXX_volume_ai.csv
compare/strength_vs_volume_ai.csv
reports/sub-XXX/report.pdf                 # default on — tables + brain-map figures
reports/sub-XXX/figures/                 # PNG plots (also embedded in PDF)
manifest.json
README.md
```

---

## Options

| Flag | Effect |
|---|---|
| `--strength-only` | Skip `volume/` and `compare/` |
| `--no-report` | Skip `reports/` PDF summaries |
| `--include SUB ...` | Process only listed subject IDs |
| `--root DIR --out DIR [--fs-root DIR]` | Flag form instead of positional paths |

Environment defaults (optional):

```bash
export CONNECTOME_ROOT=/path/to/connectomes
export OUTPUT_DIR=/path/to/results
export FS_ROOT=/path/to/freesurfer/subjects   # optional
apptainer run ... nodestrength_0.1.0.sif
```

---

## Build

### From repo checkout (HPC / cluster)

`/tmp` is often **noexec** — use the build script:

```bash
bash containers/build.sh
# → containers/nodestrength_0.1.0.sif
```

### From GitHub only (no checkout)

Requires network during build:

```bash
mkdir -p .build-tmp && export APPTAINER_TMPDIR=$PWD/.build-tmp
apptainer build --force nodestrength_0.1.0.sif containers/nodestrength-remote.def
```

### Docker

```bash
docker build -t nodestrength:0.1.0 .
docker run --rm nodestrength:0.1.0 --help
```

---

## Slurm example

```bash
#!/bin/bash
#SBATCH --job-name=nodestrength
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00

SIF=/path/to/nodestrength_0.1.0.sif
CONNECT=/path/to/dkt_connectomes
OUT=/path/to/node_strength_results

apptainer run --cleanenv \
  -B "$CONNECT:$CONNECT:ro" \
  -B "$OUT:$OUT" \
  "$SIF" \
  "$CONNECT" "$OUT"
```

---

## What's inside

- Python 3.11, `numpy`, `pandas`, `scipy`, `nibabel`, `bctpy`
- Installed CLIs: **`dkt-ai-cohort`**, **`nodestrength`** (`dk-ai-cohort` is a legacy alias)
- **Not included:** FreeSurfer, MRtrix3, QSIPrep, QSIRecon (upstream imaging only)

---

## Publishing to Docker Hub

Image: **[`phindagijimana321/nodestrength`](https://hub.docker.com/r/phindagijimana321/nodestrength)**

### From this cluster (Apptainer ORAS push — no Docker build needed)

Uses the existing `nodestrength_0.1.0.sif`:

```bash
# 1. Create repo on hub.docker.com: phindagijimana321/nodestrength
# 2. Create access token: Account Settings → Security → New Access Token

export DOCKERHUB_TOKEN=your_token_here
bash containers/push-dockerhub.sh
```

Or login interactively first:

```bash
podman login docker.io -u phindagijimana321
bash containers/push-dockerhub.sh
```

### From GitHub Actions (recommended for releases)

Add repo secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`, then:

- Push tag `v0.1.0`, or
- Run workflow **Publish Docker Hub** manually (Actions tab)

### Pull after publish

```bash
# Apptainer (SIF artifact stored via ORAS)
apptainer pull nodestrength_0.1.0.sif oras://index.docker.io/phindagijimana321/nodestrength:0.1.0
apptainer run nodestrength_0.1.0.sif /connectomes /output
```

For standard `docker pull` / Docker runtime, use the GitHub Actions workflow below.

### GitHub Container Registry (alternative)

```bash
docker tag nodestrength:0.1.0 ghcr.io/phindagijimana/nodestrength:0.1.0
docker push ghcr.io/phindagijimana/nodestrength:0.1.0
apptainer build nodestrength_0.1.0.sif docker://ghcr.io/phindagijimana/nodestrength:0.1.0
```
