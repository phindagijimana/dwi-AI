# Containerized analysis layer

The **imaging upstream** (QSIPrep, FreeSurfer, QSIRecon, `tck2connectome`) stays
on the cluster or workstation as today. Only the **Python analysis layer** is
containerized.

**Default run:** node strength, strength interhemispheric AI, **volume AI**, and
`compare/strength_vs_volume_ai.csv` — all three output folders
(`strength/`, `volume/`, `compare/`).

Use **`--strength-only`** to skip volume AI (container entrypoint only).

**In the container:** Python 3.11, `numpy`, `pandas`, `scipy`, `nibabel`, `bctpy`,
`nodestrength` (includes `mif.py` for reading `dk_nodes.mif`), cohort scripts under
`/app/scripts/`.

**Not in the container:** FreeSurfer, MRtrix3, FSL, QSIPrep, QSIRecon.

---

## Why containerize?

| Benefit | Detail |
|---|---|
| Reproducible environment | Same Python + `bctpy` version on laptop, CI, and Slurm |
| No module conflicts | Avoid fighting cluster Python modules |
| Easy handoff | Analysts run one image against NFS-mounted connectomes |
| Singularity-friendly | HPC sites usually accept `.sif` built from this Dockerfile |
| Volume AI included | Reads `dk_nodes.mif` in pure Python — no MRtrix at run time |

---

## Build (Docker)

From the repository root:

```bash
docker build -t dwi-ai-analysis:latest .
```

Verify:

```bash
docker run --rm dwi-ai-analysis:latest --help
docker run --rm --entrypoint nodestrength dwi-ai-analysis:latest --help
```

---

## Run (Docker)

Default — **strength + volume + compare**:

```bash
docker run --rm \
  -v /mnt/nfs/Gugger_Lab/NIR/dwi_test2/dk_connectomes:/data/connectomes:ro \
  -v /mnt/nfs/Gugger_Lab/NIR/dwi_test2/node_strength_results:/data/out \
  dwi-ai-analysis:latest \
  --root /data/connectomes \
  --out  /data/out
```

Strength only (no `volume/` or `compare/`):

```bash
docker run --rm \
  -v .../dk_connectomes:/data/connectomes:ro \
  -v .../node_strength_results:/data/out \
  dwi-ai-analysis:latest \
  --root /data/connectomes --out /data/out --strength-only
```

Other scripts (override entrypoint):

```bash
docker run --rm --entrypoint python dwi-ai-analysis:latest \
  /app/scripts/verify_dk_labels.py --help
```

---

## Build (Singularity / Apptainer)

On this cluster, `/tmp` is often **noexec** — use the provided build script:

```bash
bash containers/build.sh
# → containers/dwi-ai-analysis.sif (~203 MB)
```

The script sets `APPTAINER_TMPDIR` and `PROOT_TMP_DIR` under `containers/.build-tmp`.

**Manual build** (same flags):

```bash
export APPTAINER_TMPDIR=$PWD/containers/.build-tmp
export PROOT_TMP_DIR=$APPTAINER_TMPDIR
mkdir -p "$APPTAINER_TMPDIR"
apptainer build --force containers/dwi-ai-analysis.sif containers/dwi-ai-analysis-build.def
```

**Option A — from Docker/Podman** (if rootless podman works on your machine):

```bash
podman build -t dwi-ai-analysis:latest .
apptainer build containers/dwi-ai-analysis.sif docker-daemon://dwi-ai-analysis:latest
```

**Option B — wrapper def** (requires pre-built Docker tag):

```bash
docker build -t dwi-ai-analysis:latest .
apptainer build containers/dwi-ai-analysis.sif containers/dwi-ai-analysis.def
```

Copy `containers/dwi-ai-analysis.sif` to a shared location (e.g. lab modules path).

---

## Run (Singularity / Apptainer on NFS)

```bash
SIF=/path/to/dwi-ai-analysis.sif
CONNECT=/mnt/nfs/Gugger_Lab/NIR/dwi_test2/dk_connectomes
OUT=/mnt/nfs/Gugger_Lab/NIR/dwi_test2/node_strength_results

apptainer run --cleanenv \
  -B "$CONNECT:$CONNECT:ro" \
  -B "$OUT:$OUT" \
  "$SIF" \
  --root "$CONNECT" \
  --out  "$OUT"
```

Helper script:

```bash
bash containers/run_dk_cohort.sh
```

---

## Verified on URMC (Jul 22, 2026)

Built with `bash containers/build.sh` (Apptainer 1.5.2). Tested against
`dwi_test2` (5 subjects):

- Default run → `strength/`, `volume/`, `compare/`; `manifest.json` reports
  `volume_ai_enabled: true`, `n_subjects_with_volume: 5`
- `--strength-only` → `strength/` only, no `volume/`
- BCT backend active inside container

---

## Slurm example

```bash
#!/bin/bash
#SBATCH --job-name=dwi-ai
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00

SIF=/mnt/nfs/Gugger_Lab/Workflows/DWI-AI/containers/dwi-ai-analysis.sif
CONNECT=/mnt/nfs/Gugger_Lab/NIR/dwi_test2/dk_connectomes
OUT=/mnt/nfs/Gugger_Lab/NIR/dwi_test2/node_strength_results

apptainer run --cleanenv \
  -B "$CONNECT:$CONNECT:ro" \
  -B "$OUT:$OUT" \
  "$SIF" \
  --root "$CONNECT" \
  --out  "$OUT"
```

Analysis is CPU-light (seconds per subject for five subjects); Slurm is optional
but useful for scheduled cohort refreshes.

---

## Inputs and outputs

| Host path | Container mount | Role |
|---|---|---|
| `.../dk_connectomes/sub-*/dk_connectome.csv` | bind-mount parent dir | Required — node strength |
| `.../dk_connectomes/sub-*/dk_nodes.mif` | same | Required for volume AI (default on) |
| `.../node_strength_results/strength/` | bind-mount rw | `_strength.csv`, `_ai.csv`, cohort tables |
| `.../node_strength_results/volume/` | bind-mount rw | `_volume.csv`, `_volume_ai.csv` |
| `.../node_strength_results/compare/` | bind-mount rw | `strength_vs_volume_ai.csv` |

Subjects missing `dk_nodes.mif` are skipped for volume with a warning; strength
outputs are still written.

---

## Scope limits

- Container runs **`run_dk_ai_cohort.py`** (via entrypoint) and installed **`nodestrength`** CLI.
- It does **not** rebuild connectomes. If `dk_connectome.csv` or `dk_nodes.mif`
  changes, re-run the container.
- Normative GLMs / `score_connectomes.py` work if you mount a derivatives tree
  with `connectome.csv` + `node_lookup.tsv` and override the entrypoint.

See [`../other_analysis.md`](../other_analysis.md) for downstream analyses not
yet wired into the default container entrypoint.
