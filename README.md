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

Atlas-agnostic: built-in support for Lausanne + THOMAS (the paper's atlas) and MRtrix3 `fs_default` Desikan–Killiany (84 nodes, ordering empirically verified).

## Install

```bash
pip install -e .[bct]
```

Runtime deps: `numpy`, `pandas`, `scipy`, `nibabel`. Optional: `bctpy` (enables canonical BCT backend; otherwise an equivalent numpy expression is used).

## Quick start

### A. DK connectomes (QSIPrep → QSIRecon → labelconvert)

```bash
python scripts/run_dk_ai_cohort.py \
    --root /path/to/dk_connectomes \
    --out  /path/to/node_strength_results
```

Per-subject and cohort CSVs for node strength + AI land in `--out`.
See **`nodestrength.md` §12** for full documentation of `sub-XXX_strength.csv`
and `sub-XXX_ai.csv` (definitions, sources, interpretation, limitations).

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

## Tests

```bash
pytest -q     # 100 tests
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
  dk_atlas.py      Desikan–Killiany / fs_default
  bids.py          generic BIDS walker
  ideas.py         IDEAS dataset adapter
  inspect.py       readiness probe
  pipeline.py      FreeSurfer / THOMAS / MRtrix3 wrappers
  cli.py           CLI entry points
scripts/           cohort runners + DK label verifier
tests/             pytest suite
paper.md           Piper et al. 2026 — summary and key ideas
BCT.md             Brain Connectivity Toolbox reference
node.md            Extended paper notes and cohort runbooks
```

## Details and caveats

See [`node.md`](node.md) for the paper summary, formula derivations, dataset runbooks (IDEAS, MICA-MICs), and the honest list of what's reproduced vs. deferred.

## License

MIT.

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

