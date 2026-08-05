# dwi-AI

Node strength and asymmetry-index pipeline for diffusion MRI connectomes.

Implementation of the analysis pipeline in:

> Piper RJ, Feng X, …, Taylor PN. *Thalamocortical structural connectivity in children with focal epilepsy: A diffusion MRI, case–control study.* **Epilepsia** 67(4):1901–1915 (2026). DOI: [10.1002/epi.70099](https://doi.org/10.1002/epi.70099).

## What it computes

Given a square SIFT2-weighted connectome (`tck2connectome -symmetric -zero_diagonal`):

| Quantity | Formula |
|---|---|
| Node strength | `s_i = Σ_{j≠i} W_ij` (BCT `strengths_und`) |
| Side asymmetry | `(L − R) / (L + R)` |
| SOZ-aligned asymmetry | `(ipsi − contra) / (ipsi + contra)` |
| Log asymmetry | `ln(ipsi / contra)` |
| Normative z-score | OLS on controls (age, sex, motion, mean-brain strength), residual / σ |
| Mixed-design GLM | Pillai's trace, partial η², nucleus × side × group/SOZ/outcome |

Atlas-agnostic: built-in support for Lausanne + THOMAS (the paper's atlas) and for
MRtrix3 `fs_default` Desikan–Killiany connectomes (**DKT analysis**, 84 nodes).

### DKT vs DK

| Role | Name | What it is |
|------|------|------------|
| **Analysis** | DKT | `dkt_connectome.csv` on the MRtrix `fs_default` 84-node grid — strength, AI, volume |
| **Visualization** | DK | FreeSurfer aparc on fsaverage5 + ENIGMA subcortical surfaces for report figures |

ROI names are shared; ENIGMA maps are the DK-side adapter (`nodestrength.parcellations`,
`nodestrength.report_viz`). Legacy `dk_connectome.csv` is still read for analysis.

## Data privacy

This repo is **public**. Do **not** commit:

- Real subject IDs or `participants.tsv` with clinical metadata
- Cohort output folders (`node_strength_results/`, `sample_report*/`, `scripts/outputs/`)
- Absolute NFS/SMB paths from your site

Use generic placeholders in docs (`/path/to/dkt_connectomes`). Before pushing:

```bash
bash scripts/check_no_phi.sh
```

Generated `manifest.json` files under an output directory record local paths for
reproducibility on your machine — keep those directories out of git (see `.gitignore`).

## Install

```bash
pip install -e .[bct]
```

Runtime deps: `numpy`, `pandas`, `scipy`, `nibabel`. Optional: `bctpy` (enables canonical BCT backend; otherwise an equivalent numpy expression is used).

## Quick start

### A. DK connectomes (QSIPrep → QSIRecon → labelconvert)

```bash
python scripts/run_dkt_ai_cohort.py \
    --root /path/to/dkt_connectomes \
    --out  /path/to/node_strength_results
```

Per-subject and cohort CSVs land in `--out` under modality subfolders:

```
node_strength_results/
├── strength/     # always — _strength.csv, _ai.csv, cohort tables
├── volume/       # with --with-volume-ai
└── compare/      # with --with-volume-ai — strength_vs_volume_ai.csv
```

```bash
python scripts/run_dkt_ai_cohort.py \
    --root /path/to/dkt_connectomes \
    --out  /path/to/node_strength_results \
    --with-volume-ai   # optional
```

**Clinical PDF** (lean clinician summary — tables + two figures):

```bash
python scripts/run_dkt_ai_cohort.py \
    --root /path/to/dkt_connectomes \
    --out  /path/to/node_strength_results \
    --report
```

The PDF includes key-structure AI (strength, intra, volume), top-5 standard and
intra asymmetry tables, a cortical |AI| map, and a subcortical panel. Optional
`--participants` still writes research CSVs (`_soz_ai.csv`, `_strength_z.csv`) but
those are not shown in the PDF.

See **`nodestrength.md` §11–12** for the full folder layout and file definitions
(`strength/per_subject/sub-XXX_strength.csv`, `_ai.csv`, volume, and compare).

### B. IDEAS II pre-processed archive

```bash
nodestrength ingest-preprocessed \
    --archive /path/to/ideas_ii_processed \
    --participants /path/to/participants.tsv \
    --out cohort.csv

nodestrength asymmetry --cohort cohort.csv --out ai.csv

nodestrength analyze --cohort cohort.csv \
    --within nucleus side --between group \
    --value strength --out glm.csv
```

### C. Probe a new dataset before committing compute

```bash
nodestrength inspect /path/to/dataset
```

Reports subjects discovered, ROI naming sanity, participants.tsv column map, and a single `READY` / `PARTIAL` / `NOTHING_FOUND` verdict.

## Container (standalone)

Run the analysis **without a repo checkout or Python install** — the same way you
run FreeSurfer or qsiprep images. You only provide paths on your system:

| Path | Required | Purpose |
|---|---|---|
| Connectomes root | yes | One folder per subject with `dkt_connectome.csv` |
| Output directory | yes | Writable folder for results |
| FreeSurfer `SUBJECTS_DIR` | optional | Used to find `dk_nodes.mif` when it is not beside the connectome |

**Per subject** under the connectomes root (any folder name — BIDS `sub-XXX` or other IDs):

| File | Required | Role |
|---|---|---|
| `dkt_connectome.csv` | yes | 84×84 symmetric SIFT2 connectome |
| `dk_nodes.mif` | for volume AI | MRtrix label grid (in connectome folder or `FS/<subject>/`) |

Legacy connectome filenames (`dk_connectome.csv`, `connectome.csv`) are still
discovered automatically. The CLI alias `dk-ai-cohort` remains available.

**Default run:** strength + volume + compare + one-page PDF report per subject.
Use `--strength-only` or `--no-report` to skip parts of that.

### Get the image

```bash
# Build from this repo (Apptainer/Singularity)
bash containers/build.sh
# → containers/nodestrength_0.1.0.sif

# Pull from Docker Hub (Apptainer ORAS artifact)
apptainer pull nodestrength_0.1.0.sif \
  oras://index.docker.io/phindagijimana321/nodestrength:0.1.0
```

Copy `containers/run.sh` next to the `.sif` for a convenience launcher. Full
container docs: [`containers/README.md`](containers/README.md).

### Run with Apptainer

```bash
SIF=/path/to/nodestrength_0.1.0.sif
CONNECT=/path/to/connectomes
OUT=/path/to/results
FS=/path/to/freesurfer/subjects   # optional

mkdir -p "$OUT"

apptainer run --cleanenv \
  -B "$CONNECT:$CONNECT:ro" \
  -B "$OUT:$OUT" \
  ${FS:+-B "$FS:$FS:ro"} \
  "$SIF" \
  "$CONNECT" "$OUT" ${FS:+"$FS"}
```

Positional arguments inside the container:

```
CONNECTOME_DIR  OUTPUT_DIR  [FS_DIR]  [OPTIONS]
```

Flag form (equivalent):

```bash
apptainer run --cleanenv \
  -B "$CONNECT:$CONNECT:ro" -B "$OUT:$OUT" \
  "$SIF" \
  --root "$CONNECT" --out "$OUT" --fs-root "$FS"
```

### Run with `run.sh`

```bash
./run.sh /path/to/connectomes /path/to/results
./run.sh /path/to/connectomes /path/to/results /path/to/freesurfer/subjects
./run.sh /path/to/connectomes /path/to/results --strength-only
./run.sh /path/to/connectomes /path/to/results --include 001 sub-002
```

Or via environment variables:

```bash
export CONNECTOME_ROOT=/path/to/connectomes
export OUTPUT_DIR=/path/to/results
export FS_ROOT=/path/to/freesurfer/subjects   # optional
./run.sh
```

### Common options

| Flag | Effect |
|---|---|
| `--strength-only` | Skip `volume/` and `compare/` |
| `--no-report` | Skip `reports/` PDF summaries |
| `--include SUB ...` | Process only listed subject IDs (with or without `sub-` prefix) |

Help (no bind mounts needed):

```bash
apptainer run nodestrength_0.1.0.sif --help
```

### Outputs

```
node_strength_results/
├── strength/per_subject/     sub-XXX_strength.csv, sub-XXX_ai.csv
├── volume/per_subject/       sub-XXX_volume.csv, sub-XXX_volume_ai.csv  (default on)
├── compare/                  strength_vs_volume_ai.csv
├── reports/sub-XXX/          report.pdf + figures/ (default on)
├── manifest.json
└── README.md
```

Clinical PDFs include key-structure tables (with Intra AI), top-5 standard and
intrahemispheric asymmetry tables, plus two figures: an inflated cortical
asymmetry brain map and a subcortical strength/asymmetry panel.

### Docker

```bash
docker build -t nodestrength:0.1.0 .
docker run --rm \
  -v /path/to/connectomes:/data/connectomes:ro \
  -v /path/to/out:/data/out \
  nodestrength:0.1.0 \
  /data/connectomes /data/out
```

Image on Docker Hub: [`phindagijimana321/nodestrength`](https://hub.docker.com/r/phindagijimana321/nodestrength)

See [`containers/README.md`](containers/README.md) for build, publish, and Slurm examples.


## Tests

```bash
pytest -q     # 121 tests
```

Coverage: BCT parity, normative GLM, mixed ANOVA, AI formulas, BIDS walker, IDEAS ingestion, DK label-ordering lock-in.

## Layout

```
nodestrength/
  connectome.py    strength + load + mask
  normative.py     OLS GLM z-scoring
  stats.py         Pillai's trace + partial η²
  asymmetry.py     three AI formulas
  atlases.py       THOMAS labels
  parcellations.py DKT analysis vs DK ENIGMA viz roles
  dk_atlas.py      fs_default 84-node grid (DKT analysis)
  report_viz.py    DK aparc/fsa5 + ENIGMA figure adapter
  bids.py          generic BIDS walker
  ideas.py         IDEAS dataset adapter
  inspect.py       readiness probe
  pipeline.py      FreeSurfer / THOMAS / MRtrix3 wrappers
  cli.py           CLI entry points
scripts/           cohort runners + DK label verifier
tests/             pytest suite
paper.md           Piper et al. 2026 — summary and key ideas
BCT.md             Brain Connectivity Toolbox reference
other_analysis.md  Further analyses possible on DK connectomes (not yet run)
node.md            Extended paper notes and cohort runbooks
containers/        Docker + Singularity for the analysis layer
```

## Details and caveats

See [`node.md`](node.md) for the paper summary, formula derivations, dataset runbooks (IDEAS, MICA-MICs), and the honest list of what's reproduced vs. deferred.

## License

MIT.

## Privacy / what not to commit

Do **not** commit site-specific or identifying information:

- Internal filesystem or SMB paths (lab shares, home directories)
- Real subject identifiers or clinical metadata
- Cohort-specific runbooks — use a local `nodestrength.local.md` (gitignored)

Regenerate `nodestrength.docx` locally after editing `nodestrength.md`; the
Word file is not tracked in git.

## New scripts (usage)

Fit and save a normative model from controls:

```bash
python scripts/fit_normative_model.py --controls controls_long.csv --target strength --out strength_model.pkl
```

Score a directory of connectomes (per-subject `connectome.csv` + `node_lookup.tsv`):

```bash
python scripts/score_connectomes.py --root /path/to/derivatives --out /path/to/out --covariates covariates.csv --model strength_model.pkl
```

Run permutation diagnostics on a cohort long file:

```bash
python scripts/run_diagnostics.py --cohort /path/to/out/cohort_long.csv --out /path/to/out/diagnostics --effect group
```

