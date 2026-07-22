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

**Default run:** strength + volume + compare. Use `--strength-only` to skip volume.

---

## Quick start (any user with Apptainer)

```bash
SIF=/path/to/nodestrength_0.1.0.sif
CONNECT=/path/to/dk_connectomes      # parent of sub-*/
OUT=/path/to/node_strength_results   # writable

apptainer run --cleanenv \
  -B "$CONNECT:$CONNECT:ro" \
  -B "$OUT:$OUT" \
  "$SIF" \
  "$CONNECT" "$OUT"
```

Or use the bundled launcher (copy `run.sh` next to the `.sif`):

```bash
./run.sh /path/to/dk_connectomes /path/to/node_strength_results
```

Help (no bind mounts needed):

```bash
apptainer run nodestrength_0.1.0.sif --help
```

---

## Inputs and outputs

**Per subject** under `CONNECT/sub-XXX/`:

| File | Required | Role |
|---|---|---|
| `dk_connectome.csv` | yes | 84×84 symmetric SIFT2 connectome |
| `dk_nodes.mif` | for volume AI | MRtrix label grid (read in pure Python) |

**Output** under `OUT/`:

```
strength/per_subject/sub-XXX_strength.csv
strength/per_subject/sub-XXX_ai.csv
volume/per_subject/sub-XXX_volume.csv      # default on
volume/per_subject/sub-XXX_volume_ai.csv
compare/strength_vs_volume_ai.csv
manifest.json
README.md
```

---

## Options

| Flag | Effect |
|---|---|
| `--strength-only` | Skip `volume/` and `compare/` |
| `--include SUB ...` | Process only listed subject IDs |
| `--root DIR --out DIR` | Flag form instead of positional paths |

Environment defaults (optional):

```bash
export CONNECTOME_ROOT=/path/to/dk_connectomes
export OUTPUT_DIR=/path/to/node_strength_results
apptainer run ... nodestrength_0.1.0.sif
```

---

## Gugger Lab shared copy

```
/mnt/nfs/Gugger_Lab/Workflows/DWI-AI/containers/
├── nodestrength_0.1.0.sif
├── run.sh
├── README.md
└── VERSION
```

```bash
bash /mnt/nfs/Gugger_Lab/Workflows/DWI-AI/containers/run.sh \
  /mnt/nfs/Gugger_Lab/NIR/dwi_test2/dk_connectomes \
  /mnt/nfs/Gugger_Lab/NIR/dwi_test2/node_strength_results
```

SMB: `smb://smdnas/gugger_lab/Workflows/DWI-AI/containers/`

---

## Build

### From repo checkout (URMC / HPC)

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

SIF=/mnt/nfs/Gugger_Lab/Workflows/DWI-AI/containers/nodestrength_0.1.0.sif
CONNECT=/path/to/dk_connectomes
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
- Installed CLIs: **`dk-ai-cohort`**, **`nodestrength`**
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
