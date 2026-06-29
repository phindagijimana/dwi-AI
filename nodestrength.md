# nodestrength — Pipeline Documentation

## 1. Overview

`nodestrength` is a Python package + CLI that takes diffusion-MRI tractography connectomes as input and produces:

1. Per-node **connectivity strength** (Brain Connectivity Toolbox `strengths_und`).
2. Per-region **asymmetry indices** (side, SOZ-aligned, log-ratio).
3. Per-subject **normative z-scores** against a control cohort, adjusted for age, sex, motion, and global brain strength.
4. Group-level **mixed-design GLMs** (Pillai's trace, partial η²) over within-subject (nucleus, side) and between-subject (group, SOZ, post-surgical outcome) factors.

The implementation follows Piper et al. *Epilepsia* (2026), DOI 10.1002/epi.70099, and is atlas-agnostic — built-in support is shipped for Lausanne + THOMAS thalamic nuclei (the paper's atlas) and for the MRtrix3 `fs_default` Desikan–Killiany 84-node parcellation.

## 2. Conceptual model

```
                  ┌──────────────────────────┐
                  │   Per-subject inputs     │
                  │   T1, dMRI, bvec/bval    │
                  │   reverse-PE (optional)  │
                  └────────────┬─────────────┘
                               │
   ┌───────────────────────────┴───────────────────────────┐
   │                                                       │
   ▼                                                       ▼
[Raw path]                                          [Fast path]
recon-all                                       (pre-processed
THOMAS / Lausanne                                connectome archive,
MRtrix3 preproc + SIFT2                          e.g. IDEAS II)
tck2connectome
   │                                                       │
   └───────────────────────────┬───────────────────────────┘
                               ▼
                  ┌──────────────────────────┐
                  │   N×N connectome.csv     │
                  │   node_lookup.tsv        │
                  └────────────┬─────────────┘
                               │
                               ▼
                  ┌──────────────────────────┐
                  │  nodestrength analysis   │
                  │  layer (this package)    │
                  └────────────┬─────────────┘
                               ▼
        ┌──────────────┬──────────────┬───────────────┐
        ▼              ▼              ▼               ▼
    Strength      Asymmetry        Normative      Mixed-design
    table         indices          z-scores       GLM (Pillai)
```

## 3. Inputs

### 3.1 Required per subject

| File | Notes |
|---|---|
| Connectome matrix | N×N, symmetric, zero diagonal, non-negative (SIFT2 weights). CSV or whitespace-delimited. |
| Node lookup | 1-indexed `index, name` table identifying each row of the connectome. |

### 3.2 Optional per subject

| File | Notes |
|---|---|
| Label NIfTI | For per-region volume computation (e.g. THOMAS nucleus volumes). |
| Reverse-PE b=0 | For the raw imaging pipeline (`run-subject`). |

### 3.3 Cohort-level

| File | Notes |
|---|---|
| `participants.tsv` | BIDS-standard columns: `participant_id`, `age`, `sex`, plus optional `group`, `soz`, `histopathology`, `outcome`, `fbtcs`, `protocol`. The `ideas.PARTICIPANT_COLUMN_ALIASES` table maps common variants. |

## 4. Stages

### Stage 1 — Optional raw imaging pipeline

Subprocess wrappers around external tools, invoked by `nodestrength run-subject`. Each wrapper checks `shutil.which` for the binary and raises `ToolUnavailableError` early if it's missing.

| Step | Binary | Output |
|---|---|---|
| Cortical parcellation | `recon-all` (FreeSurfer 7.x) | `aparc+aseg.mgz` |
| Lausanne aparc60 | `lausanne_parcellator` (site-specific) | `aparc60.nii.gz` |
| Thalamic nuclei | `thomas` (T1w mode) | `left/`, `right/` per-nucleus masks |
| Label merge | in-Python (`pipeline.merge_thomas_into_lausanne`) | `labels_combined.nii.gz` |
| dMRI denoise | `dwidenoise` (MRtrix3) | `dwi_den.mif` |
| Topup + eddy | `dwifslpreproc` (MRtrix3 → FSL) | `dwi_preproc.mif` |
| Bias correction | `dwibiascorrect` (MRtrix3 → ANTs/FSL) | `dwi_biascorr.mif` |
| Response | `dwi2response dhollander` | `wm.txt`, `gm.txt`, `csf.txt` |
| FOD | `dwi2fod msmt_csd` | `wmfod.mif` |
| 5tt | `5ttgen fsl` | `5tt.mif` |
| Tractography | `tckgen -act -seed_dynamic` (5 M streamlines) | `tracks_5M.tck` |
| SIFT2 | `tcksift2` | `sift2_weights.txt` |
| Connectome | `tck2connectome -symmetric -zero_diagonal -tck_weights_in` | `connectome.csv` |

This stage is **dry-run tested only** — no external tool was executed during package development. The argument strings are correct; the wrappers should run on any standard FreeSurfer / FSL / MRtrix3 / THOMAS install.

### Stage 2 — Per-subject node strength

Module: `nodestrength.connectome`.

Given the N×N connectome `W` and a node lookup, `compute_nucleus_strength(W, lookup, rois, config)` returns one row per thalamic ROI:

```
    s_i = Σ_{j} W_ij   over all j with j ≠ i AND j ∉ T   (paper)
    s_i = Σ_{j ≠ i} W_ij                                  (whole-brain / DK)
```

`T` is the thalamic-ROI index set. The two exclusions are:

* **self** (`exclude_self=True`, default): drop the diagonal.
* **inter-thalamic** (`exclude_inter_thalamic=True`, default for the paper): drop edges between any pair of thalamic ROIs, per Piper et al. Figure 2 caption.

The row sum is delegated to `bct.strengths_und` when `bctpy` is installed (verified by parity test); the numpy fallback is `W.sum(axis=0)` — bit-identical.

`mean_brain_strength(W)` returns the global covariate `s̄` used downstream.

### Stage 3 — Normative z-scoring

Module: `nodestrength.normative`.

For each (nucleus, side) cell, fit OLS on the control cohort:

```
    s_i^(c) = β0 + β_age·age + β_sex·sex + β_global·s̄ + β_motion·motion + ε,
              ε ~ Normal(0, σ_i²)
```

Then z-score any subject `k`:

```
                 s_i^(k) - prediction_i(k)
    z_i^(k) = ─────────────────────────────
                          σ_i
```

For nucleus volume, covariates become `(age, sex, ICV)`.

R-side subjects are z-scored to R-side controls (separate fit per side).

### Stage 4 — Asymmetry indices

Module: `nodestrength.asymmetry`.

Three formulas. `side_ai` is hemispheric and needs no SOZ information; `soz_ai` and `log_ai` need a per-patient SOZ side and return NaN otherwise.

```
    side_ai = (L - R) / (L + R)                       range [-1, +1]
    soz_ai  = (ipsi - contra) / (ipsi + contra)       range [-1, +1]
    log_ai  = ln(ipsi / contra)                       range (-inf, +inf)
```

`cohort_ai()` collapses a long-form `(subject, nucleus, side, strength)` table to one row per (subject, nucleus) with all three AIs plus the underlying ipsi/contra/L/R values and SOZ side. Pass-through clinical columns (group, SOZ, seizure_free, etc.) are auto-joined on `subject`.

### Stage 5 — Mixed-design GLM

Module: `nodestrength.stats`.

A pure-numpy multivariate general linear model in the "wide repeated-measures" form SPSS uses:

* Wide form: one row per subject, one column per within-cell (e.g. 4 nuclei × 2 sides = 8 columns).
* Within-subject contrasts via orthonormal Helmert matrices.
* Hypothesis test `L β M = 0`, with `L` selecting between-subject design columns and `M` projecting onto a within-subject contrast.
* Test statistic: **Pillai's trace** `V = tr(H (H + S)⁻¹)`.
* F-approximation: standard Rao form.
* Effect size: **partial η² = V / s**, with `s = min(rank(L), ncol(M))` — matches SPSS's multivariate-tests table.

The driver `mixed_anova(long, subject, within_factors, between_factors, value)` returns one row per source of variation: between-main, within-main, all between × within interactions.

## 5. CLI reference

All subcommands are exposed under the `nodestrength` entry point.

### `nodestrength run-subject`

Run the full raw pipeline for one subject.

```bash
nodestrength run-subject SUBJECT_ID \
    --t1 T1.nii.gz --dwi dwi.nii.gz \
    --bvec dwi.bvec --bval dwi.bval --rpe-b0 rpe.nii.gz \
    --subjects-dir /path/to/freesurfer \
    --out-dir /path/to/derivatives/sub-XXX \
    [--dry-run]
```

### `nodestrength compute-strength`

Single-subject strength + volume table from a pre-computed connectome.

```bash
nodestrength compute-strength \
    --subject-id S001 \
    --connectome connectome.csv --lookup node_lookup.tsv \
    --labels labels_combined.nii.gz \
    --out S001_strengths.csv
```

### `nodestrength fit-normative`

Fit per-(nucleus, side) GLM on a control cohort and pickle the model.

```bash
nodestrength fit-normative \
    --controls controls_long.csv \
    --out normative_model.pkl
```

### `nodestrength analyze`

Mixed-design GLM with Pillai's trace and partial η².

```bash
nodestrength analyze \
    --cohort cohort_long.csv \
    --within nucleus side --between group \
    --value strength --out glm.csv
```

### `nodestrength asymmetry`

Per-subject asymmetry indices from a long-form cohort.

```bash
nodestrength asymmetry \
    --cohort cohort_long.csv \
    --soz-side-col soz_side \
    --out cohort_ai.csv
```

### `nodestrength ingest-ideas`

Walk an IDEAS raw BIDS root and emit a manifest CSV.

```bash
nodestrength ingest-ideas \
    --bids /data/ideas_raw \
    --participants /data/ideas_raw/participants.tsv \
    --out manifest.csv
```

### `nodestrength ingest-preprocessed`

Build a long-form cohort directly from the IDEAS II pre-processed dMRI archive.

```bash
nodestrength ingest-preprocessed \
    --archive /data/ideas_ii_processed \
    --participants /data/ideas_ii_processed/participants.tsv \
    --out cohort_long.csv
```

### `nodestrength inspect`

Readiness probe — accepts any dataset path and emits a structured verdict.

```bash
nodestrength inspect /path/to/dataset --json /tmp/inspect.json
```

## 6. Outputs

Per-subject artefacts (raw pipeline, in `<out-dir>/sub-XXX/`):

| File | Contents |
|---|---|
| `labels_combined.nii.gz` | Lausanne + THOMAS merged label image (native space) |
| `dwi/dwi_biascorr.mif` | Preprocessed, distortion-corrected, bias-corrected dMRI |
| `tracto/tracks_5M.tck` | 5 M streamlines (ACT-guided) |
| `tracto/sift2_weights.txt` | Per-streamline SIFT2 weights |
| `connectome.csv` | N×N SIFT2-weighted adjacency matrix |
| `node_lookup.tsv` | Index → ROI name mapping |

Cohort-level artefacts (analysis layer):

| File | Contents |
|---|---|
| `cohort_long.csv` | Long-form table, one row per (subject, nucleus, side) |
| `cohort_ai.csv` | Per (subject, nucleus) AI table |
| `glm_*.csv` | Mixed-ANOVA results, one row per source of variation |
| `normative_model.pkl` | Pickled per-(nucleus, side) OLS fits |

## 7. Worked example — DK / fs_default cohort

End-to-end on a directory of QSIRecon DK connectomes:

```bash
python scripts/run_dk_ai_cohort.py \
    --root /path/to/dk_connectomes \
    --out  /path/to/AI_results
```

Produces under `AI_results/`:

```
AI_results/
├── README.md
├── manifest.json
├── node_strength_cohort.csv       84 nodes × N subjects
├── asymmetry_index_cohort.csv     41 L/R pairs × N subjects
├── cohort_summary.csv             per-ROI cohort means + SDs
└── per_subject/
    ├── sub-XXX_strength.csv
    └── sub-XXX_ai.csv
```

The DK label ordering is encoded in `nodestrength.dk_atlas` and was empirically verified against real `dk_nodes.mif` files via `scripts/verify_dk_labels.py`. If you suspect a parcellation mismatch, run the verifier on one subject:

```bash
python scripts/verify_dk_labels.py \
    --subject /path/to/sub-XXX \
    --out /tmp/empirical_lut.csv
```

## 8. Validation

- 100 unit tests on synthetic data (`pytest -q`).
- BCT parity verified — `bct.strengths_und(W) == nodestrength.connectome._strengths_und(W)` bit-for-bit.
- Pillai's F matches univariate F in the degenerate 2-group / 1-response case (closed-form cross-check).
- DK label ordering locked in by 14 tests; any future change that breaks the empirically-verified mapping fails loudly.
- BIDS / IDEAS walkers tested on synthetic trees mimicking the real layouts.

## 9. Limitations

- **Raw imaging pipeline wrappers** have not been executed end-to-end during package development. The argument strings are correct and the wrappers will fail fast if any external tool is missing, but real-data validation is the responsibility of the operator.
- **Single-shell vs multi-shell** dMRI is auto-handled by MRtrix3's `dwi2response dhollander` + `dwi2fod msmt_csd`; single-shell datasets should swap in `tournier` + `csd` manually in `pipeline.tractography_cmds`.
- **GLM diagnostics** — no Mauchly's test for sphericity, no Greenhouse–Geisser correction. Pillai is robust to sphericity violations, which is why the paper uses it.
- **Cluster orchestration** — `scripts/run_micamics_cohort.py` emits SLURM commands but does not handle job dependencies or retries. Re-runs must skip completed subjects manually.

## 10. References

- Piper RJ, Feng X, …, Taylor PN. *Thalamocortical structural connectivity in children with focal epilepsy: A diffusion MRI, case–control study.* Epilepsia 67(4):1901–1915 (2026). DOI: 10.1002/epi.70099.
- Rubinov M, Sporns O. *Complex network measures of brain connectivity.* NeuroImage 52(3):1059–1069 (2010). BCT source: https://sites.google.com/site/bctnet.
- Taylor PN et al. *The imaging database for epilepsy and surgery (IDEAS).* Epilepsia 66(2):471–481 (2025).
- Taylor PN et al. *Open diffusion MRI and connectivity data for epilepsy and surgery: IDEAS II release.* Epilepsia (2026).
- Tournier J-D et al. *MRtrix3: A fast, flexible and open software framework for medical image processing and visualisation.* NeuroImage 202:116137 (2019).
