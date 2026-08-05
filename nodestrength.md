# nodestrength — Pipeline Documentation

## 1. Overview

`nodestrength` is a Python package + CLI that takes diffusion-MRI tractography connectomes as input and produces:

1. Per-node **connectivity strength** (Brain Connectivity Toolbox `strengths_und`).
2. Per-region **asymmetry indices** (side, SOZ-aligned, log-ratio).
3. Per-subject **normative z-scores** against a control cohort, adjusted for age, sex, motion, and global brain strength.
4. Group-level **mixed-design GLMs** (Pillai's trace, partial η²) over within-subject (nucleus, side) and between-subject (group, SOZ, post-surgical outcome) factors.

The implementation follows Piper et al. *Epilepsia* (2026), DOI 10.1002/epi.70099, and is atlas-agnostic — built-in support is shipped for Lausanne + THOMAS thalamic nuclei (the paper's atlas) and for the MRtrix3 `fs_default` Desikan–Killiany 84-node parcellation.

**Companion documents:**

| File | Contents |
|------|----------|
| [`paper.md`](paper.md) | Concise summary of Piper et al. 2026 — design, findings, key ideas |
| [`BCT.md`](BCT.md) | Brain Connectivity Toolbox reference — node strength, `strengths_und`, how this repo uses BCT |
| [`node.md`](node.md) | Extended paper notes, IDEAS/MICA-MICs runbooks, reproduction planning |

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

### 6.1 DKT cohort outputs (`run_dkt_ai_cohort.py`)

Written to `node_strength_results/` (see **§12** for full methodology, sources,
and interpretation). Outputs are grouped by modality:

```
node_strength_results/
├── strength/          # connectivity (always)
│   ├── per_subject/
│   ├── node_strength_cohort.csv
│   ├── asymmetry_index_cohort.csv
│   └── cohort_summary.csv
├── volume/            # optional (--with-volume-ai)
│   ├── per_subject/
│   └── … cohort volume tables
└── compare/           # optional (--with-volume-ai)
    └── strength_vs_volume_ai.csv
```

| File | Contents |
|---|---|
| `strength/per_subject/sub-XXX_strength.csv` | 84 nodes × strength (see §12.1) |
| `strength/per_subject/sub-XXX_ai.csv` | 42 L/R pairs × interhemispheric AI (see §12.3) |
| `strength/per_subject/sub-XXX_strength_intra.csv` | 84 nodes × intrahemispheric-only strength (see §12.4) |
| `strength/per_subject/sub-XXX_ai_intra.csv` | 42 pairs × intrahemispheric AI (see §12.4) |
| `strength/node_strength_cohort.csv` | Cohort stack of all `_strength.csv` files |
| `strength/asymmetry_index_cohort.csv` | Cohort stack of all `_ai.csv` files |
| `strength/node_strength_intra_cohort.csv` | Cohort stack of all `_strength_intra.csv` files |
| `strength/asymmetry_index_intra_cohort.csv` | Cohort stack of all `_ai_intra.csv` files |
| `strength/cohort_summary.csv` | Per-ROI mean/SD of strength `side_ai` and `log_ai` |
| `strength/cohort_intra_summary.csv` | Per-ROI mean/SD of intrahemispheric `side_ai` and `log_ai` |
| `volume/per_subject/sub-XXX_volume.csv` | 84 nodes × volume_mm3 *(with `--with-volume-ai`)* |
| `volume/per_subject/sub-XXX_volume_ai.csv` | 42 pairs × volume AI *(with `--with-volume-ai`)* |
| `compare/strength_vs_volume_ai.csv` | Side-by-side strength vs volume AI *(with `--with-volume-ai`)* |
| `manifest.json` | Run metadata, atlas info, warnings |
| `README.md` | Auto-generated summary (regenerated each run) |
| `nodestrength.docx` | Full pipeline documentation (copy for end users; see §11.2) |

## 7. Worked example — DK / fs_default cohort

End-to-end on a directory of QSIRecon DK connectomes:

```bash
python scripts/run_dkt_ai_cohort.py \
    --root /path/to/dkt_connectomes \
    --out  /path/to/node_strength_results
```

Produces under `node_strength_results/` (strength only by default):

```
node_strength_results/
├── README.md
├── nodestrength.docx              full pipeline documentation
├── manifest.json
└── strength/
    ├── node_strength_cohort.csv       84 nodes × N subjects
    ├── asymmetry_index_cohort.csv     42 L/R pairs × N subjects
    ├── cohort_summary.csv             per-ROI cohort means + SDs
    └── per_subject/
        ├── sub-XXX_strength.csv
        └── sub-XXX_ai.csv
```

With `--with-volume-ai`, also creates `volume/` and `compare/` (see §11.2).

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

- Piper RJ, Feng X, …, Taylor PN. *Epilepsia* 2026 — summary in [`paper.md`](paper.md)
- Rubinov M, Sporns O. *NeuroImage* 2010 — BCT details in [`BCT.md`](BCT.md)
- Taylor PN et al. *The imaging database for epilepsy and surgery (IDEAS).* Epilepsia 66(2):471–481 (2025).
- Taylor PN et al. *Open diffusion MRI and connectivity data for epilepsy and surgery: IDEAS II release.* Epilepsia (2026).
- Tournier J-D et al. *MRtrix3: A fast, flexible and open software framework for medical image processing and visualisation.* NeuroImage 202:116137 (2019).

## 11. DKT cohort workflow (analysis) and DK ENIGMA maps (visualization)

Generic notes for running `dkt-ai-cohort` on Desikan–Killiany connectomes at any
site. **Analysis** uses `dkt_connectome.csv` on the MRtrix `fs_default` 84-node
grid (**DKT**). **Report figures** map the same ROI names onto FreeSurfer **DK**
aparc on fsaverage5 and ENIGMA subcortical surfaces (`nodestrength.parcellations`,
`nodestrength.report_viz`).

Keep institution-specific paths and subject identifiers in a local file such as
`nodestrength.local.md` (gitignored).

| Layer | Scheme | Key artifacts |
|-------|--------|----------------|
| Strength / AI / volume | **DKT** | `dkt_connectome.csv`, `dk_atlas`, `dkt-ai-cohort` |
| Cortical / subcortical maps | **DK** | `aparc_fsa5.csv`, ENIGMA Toolbox (optional) |

Legacy `dk_connectome.csv` is still accepted when `dkt_connectome.csv` is absent.

### 11.1 Upstream imaging pipeline

Typical workflow before this analysis layer:

1. **QSIPrep** — preprocess DWI, register to T1w, define tractography space.
2. **FreeSurfer / FastSurfer** — `recon-all` on T1w → `aparc+aseg.mgz`.
3. **QSIRecon** — SS3T CSD, 5TT, ACT tractography, SIFT2 weighting.
4. **Post-hoc DK connectome** — warp labels into DWI space, `labelconvert` to
   MRtrix3 `fs_default` (84 nodes), `tck2connectome -symmetric -zero_diagonal`
   → **`dkt_connectome.csv`** per subject (legacy sites may still use
   `dk_connectome.csv`).

Then the analysis layer (`dkt-ai-cohort`):

5. **Node strength** — BCT `strengths_und`: `s_i = Σ_{j≠i} W_ij` for each of
   84 DK nodes → `strength/per_subject/sub-XXX_strength.csv`.
6. **Interhemispheric asymmetry index (strength)** — for each of 42 matched L/R
   pairs: `side_ai = (L − R) / (L + R)` and `log_ai = ln(L / R)` →
   `strength/per_subject/sub-XXX_ai.csv`.
7. **Volume + volume AI** *(optional, `--with-volume-ai`)* — ROI volume from
   `dk_nodes.mif` → `volume/per_subject/`; cross-modality table in
   `compare/strength_vs_volume_ai.csv`.

### 11.2 Result locations and folder layout

| Location | Role |
|---|---|
| `/path/to/dkt_connectomes/<subject>/dkt_connectome.csv` | Per-subject connectome input |
| `/path/to/dkt_connectomes/<subject>/` | Other per-subject inputs (`dk_nodes.mif`, etc.) |
| `/path/to/node_strength_results/` | Analysis outputs |

**Output folder structure:**

```
node_strength_results/
├── README.md, manifest.json, nodestrength.md, nodestrength.docx, …
├── strength/                          # connectivity (always written)
│   ├── per_subject/
│   │   ├── sub-XXX_strength.csv
│   │   └── sub-XXX_ai.csv
│   ├── node_strength_cohort.csv
│   ├── asymmetry_index_cohort.csv
│   └── cohort_summary.csv
├── volume/                            # optional (--with-volume-ai)
│   ├── per_subject/
│   │   ├── sub-XXX_volume.csv
│   │   └── sub-XXX_volume_ai.csv
│   ├── node_volume_cohort.csv
│   ├── volume_asymmetry_index_cohort.csv
│   └── cohort_volume_summary.csv
└── compare/                           # optional (--with-volume-ai)
    └── strength_vs_volume_ai.csv
```

**User documentation:** `nodestrength.docx` can be generated locally from this
file with `python scripts/md_to_docx.py --in nodestrength.md --out nodestrength.docx`.

### 11.3 Running the cohort analysis

**Standalone container** (recommended — see [`containers/README.md`](containers/README.md)):

```bash
./run.sh /path/to/connectomes /path/to/node_strength_results
```

Volume AI is **on by default** in the container (reads `dk_nodes.mif`). Use
`--strength-only` to skip `volume/` and `compare/`.

**Python** (from repo checkout):

```bash
dkt-ai-cohort \
    --root /path/to/connectomes \
    --out  /path/to/node_strength_results \
    --with-volume-ai
```

Restrict to one subject after a connectome rebuild:

```bash
dkt-ai-cohort \
    --root /path/to/connectomes \
    --out  /tmp/redo_one_subject \
    --include SUBJECT_ID
```

**Clinical PDF reports** (optional):

```bash
dkt-ai-cohort \
    --root /path/to/connectomes \
    --out  /path/to/node_strength_results \
    --report
```

The PDF is a lean clinician summary: key structures (Str / Intra / Vol AI),
top-5 standard and intra asymmetry, cortical |AI| map, and subcortical panel.
Pass `--participants` separately to also write research CSVs (`_soz_ai.csv`,
`_strength_z.csv`, `normative_strength_model.pkl`); those are not in the PDF.
Use `--no-report` to skip PDF generation.

Then merge the new per-subject CSVs into cohort tables and refresh
`manifest.json` (and `volume/` / `compare/` if volume AI was enabled).

### 11.4 Output files — quick reference

Each subject gets two tables under `strength/per_subject/`. **Full methodology, sources,
column definitions, interpretation, and limitations are in §12.**

| File | Rows | Question it answers |
|---|---|---|
| `strength/per_subject/sub-XXX_strength.csv` | 84 | How much connectivity does each DK node have? |
| `strength/per_subject/sub-XXX_ai.csv` | 42 | Is connectivity left–right asymmetric for each ROI pair? |
| `strength/per_subject/sub-XXX_soz_ai.csv` | 42 | SOZ-aligned asymmetry *(with `--participants` + SOZ side)* |
| `strength/per_subject/sub-XXX_strength_z.csv` | 42 | Normative L/R strength z per pair *(with controls)* |
| `reports/sub-XXX/report.pdf` | — | Clinician PDF: key structures, top-5 AI, two figures *(with `--report`)* |
| `volume/per_subject/sub-XXX_volume.csv` | 84 | What is each DK node's volume (mm³)? *(with `--with-volume-ai`)* |
| `volume/per_subject/sub-XXX_volume_ai.csv` | 42 | Is volume left–right asymmetric for each ROI pair? *(with `--with-volume-ai`)* |

Cohort-level mirrors live under `strength/` and `volume/`; cross-modality comparison
under `compare/strength_vs_volume_ai.csv`.

### 11.5 Interhemispheric asymmetry index (summary)

**Interhemispheric asymmetry index** (also **side AI**, **hemispheric AI**) compares
left and right homologous regions:

```
    side_ai = (L − R) / (L + R)     range [−1, +1]
    log_ai  = ln(L / R)             unbounded, symmetric around 0
```

Interpretation:

| `side_ai` | Meaning |
|---|---|
| **+1** | All signal on the left |
| **0** | Perfect symmetry (L = R) |
| **−1** | All signal on the right |
| **Positive** | Left > right |
| **Negative** | Right > left |

In `nodestrength`, this is `side_ai` in `nodestrength/asymmetry.py`. It does
**not** require seizure-onset-zone (SOZ) information.

**Distinct from SOZ-aligned AI:** `soz_ai = (ipsi − contra) / (ipsi + contra)`
reframes the comparison relative to the patient's SOZ side. The Piper paper
primarily tests laterality as a **mixed-GLM interaction** rather than a single
closed-form index; `side_ai` is a complementary scalar for plots and correlations.

### 11.6 Strength AI vs volumetric AI

These are **not the same measurement**, but they use the **same interhemispheric
formula** on different modalities:

| | Node-strength interhemispheric AI | Volumetric interhemispheric AI |
|---|---|---|
| **Formula** | `(L − R) / (L + R)` | `(L − R) / (L + R)` |
| **Quantity** | Connectivity (SIFT2-weighted streamline counts) | ROI volume (mm³ from segmentation) |
| **Output location** | `strength/` | `volume/`; comparison in `compare/` |
| **Package support** | `dkt-ai-cohort` | Same CLI with `--with-volume-ai` |

They can **agree** (both left-biased) or **diverge** (symmetric volume but
asymmetric connectivity, or vice versa). Piper et al. report complementary
strength and volume effects — low cross-modality correlation is not necessarily
an error.

**Normative adjustment differs:** strength z-scoring uses age, sex, motion, and
mean-brain strength; volume z-scoring uses age, sex, and ICV.

### 11.7 Optional step — volumetric AI after node strength

Volume AI is an **optional second block** in `dkt-ai-cohort` — no need to
rerun QSIPrep, FreeSurfer, or QSIRecon:

```
Step A (default):  dkt_connectome.csv  →  strength  →  strength AI
Step B (optional): dk_nodes.mif       →  ROI volume →  volume AI
Step C (optional): merge strength AI + volume AI for comparison
```

CLI:

```bash
dkt-ai-cohort \
    --root /path/to/connectomes \
    --out  /path/to/node_strength_results \
    --with-volume-ai
```

**Volume source:** voxel counts in `dk_nodes.mif` (same 84-node grid as the
connectome). Alternative for other workflows: FreeSurfer `segstats` on
`aparc+aseg` (standard but slightly different spatial frame).

**Extra outputs when `--with-volume-ai` is set** (under `volume/` and `compare/`):

| File | Contents |
|---|---|
| `volume/node_volume_cohort.csv` | Long-form: subject × node × volume_mm3 |
| `volume/volume_asymmetry_index_cohort.csv` | 42 pairs × volume AI |
| `volume/cohort_volume_summary.csv` | Per-ROI mean/SD of volume AI |
| `volume/per_subject/sub-XXX_volume.csv` | Per-subject volumes |
| `volume/per_subject/sub-XXX_volume_ai.csv` | Per-subject volume AI |
| `compare/strength_vs_volume_ai.csv` | Side-by-side comparison per ROI |

Subjects without `dk_nodes.mif` are skipped for volume with a warning; strength
outputs are still written.

**Caveats for v1:** `_ai.csv` remains raw asymmetry; normative z-scores and SOZ AI
are written to separate tables and included in the clinical PDF when
`participants.tsv` supplies controls and/or SOZ side. DK thalamus remains
whole-structure, not THOMAS nuclei.

### 11.8 Regenerating one subject

When a connectome is rebuilt (e.g. after label-warp QC), regenerate only that
subject and merge into the cohort:

1. Delete `strength/per_subject/sub-XXX_strength.csv` and `sub-XXX_ai.csv`.
2. Run `dkt-ai-cohort --include SUBJECT_ID` to a temporary output dir.
3. Remove old rows for that subject from `strength/node_strength_cohort.csv` and
   `strength/asymmetry_index_cohort.csv`; append new rows.
4. Recompute `strength/cohort_summary.csv`.
5. Record the event in `manifest.json` → `regenerated_subjects`.

### 11.9 Synthetic demo results (not empirical)

`scripts/demo_synthetic.py` writes to `scripts/outputs/` (gitignored):

- `synthetic_cohort.csv`, `synthetic_ai.csv`, `synthetic_patients_zscored.csv`
- Six `glm_*.csv` files (controls vs patients, SOZ, seizure freedom × strength/volume)

These demonstrate the full Piper-style analysis pipeline on **simulated** data
only. They are **not** real cohort findings.

### 11.10 Quick FAQ

**Q: Is interhemispheric AI the same as volumetric AI?**
A: Same formula and left–right comparison; different underlying quantity
(strength vs volume). Strength AI lives in `strength/per_subject/sub-XXX_ai.csv`;
volume AI in `volume/per_subject/sub-XXX_volume_ai.csv`.

**Q: What is in `_ai.csv`?**
A: Interhemispheric asymmetry on **node strength** — 42 L/R pairs with
`side_ai` and `log_ai`, under `strength/per_subject/`.

**Q: Where are results?**
A: Under your chosen output directory (e.g. `/path/to/node_strength_results/`)
with subfolders `strength/`, `volume/` (optional), and `compare/` (optional).

**Q: Can we compare strength AI to volume AI?**
A: Yes — see `compare/strength_vs_volume_ai.csv` (one row per subject × ROI
pair with both modalities side by side). Expect complementary rather than
identical signals.

**Q: Does this replace Piper et al. thalamic nucleus analysis?**
A: Not yet — DK whole-thalamus only. Per-nucleus AV/CM/MDPf/PUL analysis
requires THOMAS segmentation on top of FreeSurfer.

## 12. Per-subject output reference — strength and volume files

This section is the authoritative description of DK cohort output files under
`strength/`, `volume/`, and `compare/`. It covers definitions, upstream inputs,
credible sources, how the files relate to each other, interpretation, and explicit
limitations.

### 12.1 Data flow

```
dkt_connectomes/sub-XXX/dkt_connectome.csv     (84×84, SIFT2-weighted, symmetric)
                    │
                    ▼
         BCT strengths_und  (nodestrength.connectome)
                    │
                    ▼
      strength/per_subject/sub-XXX_strength.csv   (84 rows — one per DK node)
                    │
                    │  pair 42 homologous L/R ROIs (nodestrength.dk_atlas)
                    ▼
      strength/per_subject/sub-XXX_ai.csv         (42 rows — interhemispheric AI)
```

Implementation: `dkt-ai-cohort` → `_node_table()` and `_pair_ai_table()`.

### 12.2 `sub-XXX_strength.csv`

#### Purpose

Reports **node strength** — the total structural connectivity of each
Desikan–Killiany ROI — derived from the subject's diffusion connectome.

#### Columns

| Column | Type | Description |
|---|---|---|
| `subject` | string | Subject ID without `sub-` prefix |
| `fs_default_index` | int | MRtrix3 `fs_default` node index (1–84) |
| `name` | string | Canonical ROI label, e.g. `L.bankssts`, `R.Thalamus-Proper` |
| `side` | string | `L`, `R`, or cerebellum side as applicable |
| `region_type` | string | `cortex`, `subcortical`, or `cerebellum` |
| `strength` | float | Node strength (see formula below) |

**Row count:** exactly **84** (one per DK node). Midline / brain-stem nodes are
not included in the 84-node atlas.

#### Formula

Given connectome matrix `W` (symmetric, zero diagonal):

```
    s_i = Σ_{j ≠ i} W_ij
```

With the diagonal already zeroed by `tck2connectome -zero_diagonal`, this is
equivalent to summing row `i` (or column `i`) of `W`.

#### Methodological basis and sources

| Layer | Source | What it provides |
|---|---|---|
| **Connectivity strength concept** | Piper RJ et al. *Epilepsia* 2026;67(4):1901–1915. DOI [10.1002/epi.70099](https://doi.org/10.1002/epi.70099) | Defines **connectivity strength** as the sum of SIFT2-weighted edges from each ROI to all other ROIs in the connectome (paper pipeline step 7, Section 2.6). |
| **Node strength computation** | Rubinov M, Sporns O. *NeuroImage* 2010;52(3):1059–1069. [BCT](https://sites.google.com/site/bctnet) | Canonical **`strengths_und`** — undirected weighted node strength as the row sum of the adjacency matrix. Implemented via `bctpy` when installed; numpy fallback is bit-identical. |
| **Connectome construction** | Tournier J-D et al. *NeuroImage* 2019;202:116137 (MRtrix3) | `tck2connectome -symmetric -zero_diagonal` on ACT tractography with SIFT2 weighting. |
| **Parcellation** | MRtrix3 `fs_default.txt` via `labelconvert` | 84-node Desikan–Killiany ordering; empirically verified in this repo (`scripts/verify_dk_labels.py`, 14 unit tests in `tests/test_dk_atlas.py`). |

#### Credibility assessment

| Aspect | Rating | Notes |
|---|---|---|
| Strength **metric** | **High** | Standard graph-theoretic measure (BCT) applied to a peer-reviewed epilepsy connectivity framework (Piper 2026). |
| Connectome **weights** | **High** | Mainstream MRtrix3 + SIFT2 workflow; site-specific QSIPrep/QSIRecon upstream. |
| **DK atlas application** | **Moderate** | Validated locally, but **not identical** to Piper's Lausanne + THOMAS nuclei. Thalamus is one whole node per hemisphere, not AV/CM/MDPf/PUL. |
| **Edge exclusions** | **Moderate** | Piper optionally excludes inter-thalamic edges for nucleus strength; the DK runner sums **all** non-self edges (`exclude_inter_thalamic=False` for whole-brain DK). |

#### What `_strength.csv` is NOT

- Not normative z-scores (raw streamline-weight sums; no age/sex/motion adjustment).
- Not nucleus-level thalamic strength as in Piper et al. (requires THOMAS).
- Not a measure of tissue volume (see volumetric AI, §12.7).
- Not edge-level connectivity (strength collapses all edges into one scalar per node).

### 12.3 `sub-XXX_ai.csv`

#### Purpose

Reports **interhemispheric asymmetry index** on node strength — for each
homologous left/right ROI pair, how asymmetric is connectivity between
hemispheres?

Also called **side AI**, **hemispheric AI**, or **normalized asymmetry index**.

#### Columns

| Column | Type | Description |
|---|---|---|
| `subject` | string | Subject ID |
| `roi_name` | string | Base region name without side, e.g. `bankssts`, `Thalamus-Proper` |
| `region_type` | string | `cortex`, `subcortical`, or `cerebellum` |
| `L_index`, `R_index` | int | `fs_default_index` of the paired left and right nodes |
| `L_strength`, `R_strength` | float | Node strengths copied from `_strength.csv` |
| `side_ai` | float | Interhemispheric AI: `(L − R) / (L + R)`; NaN if `L + R ≤ 0` |
| `log_ai` | float | Log-ratio AI: `ln(L / R)`; NaN if either value ≤ 0 |

**Row count:** exactly **42** matched L/R pairs (34 cortical + 7 subcortical +
1 cerebellum cortex). Pairing rules are in
`nodestrength.dk_atlas.lr_pair_table()`.

#### Formulas

```
    side_ai = (L − R) / (L + R)        range [−1, +1]
    log_ai  = ln(L / R)                unbounded; 0 = symmetry
```

Both are computed by `nodestrength.asymmetry.side_ai()` and `.log_ai()`.

#### Methodological basis and sources

| Layer | Source | What it provides |
|---|---|---|
| **Input values** | `_strength.csv` (see §12.2) | L and R node strengths per ROI pair. |
| **Interhemispheric AI formula** | Standard normalized asymmetry index: `AI = (L − R) / (L + R)` | Scale-invariant left–right comparison |
| **L/R pairing** | `nodestrength.dk_atlas` (empirically verified fs_default ordering) | Ensures homologous regions are compared (e.g. `L.bankssts` ↔ `R.bankssts`). |
| **Conceptual alignment with Piper 2026** | Piper et al. *Epilepsia* 2026 | Paper tests **laterality** (L/R or ipsi/contra) as a **mixed-GLM interaction** (Pillai's trace), not as a single pre-defined AI column. |

#### Credibility assessment

| Aspect | Rating | Notes |
|---|---|---|
| **AI formula** | **High** | Well-established normalized asymmetry measure; lab-standard (ASL-AI). |
| **Applied to node strength** | **High** | Natural downstream of BCT strength; same left–right question as the paper's laterality effects. |
| **As Piper's primary statistic** | **Low / N/A** | Piper does **not** define closed-form `_ai.csv` as the main outcome. Use mixed GLMs (`nodestrength analyze`) for paper-faithful inference. |
| **Raw vs adjusted** | **Moderate** | Current `_ai.csv` uses **raw** strength. Piper typically analyses **normative z-scored** strength with covariates (age, sex, motion, mean-brain strength). |

#### Interpretation of `side_ai`

| Value | Meaning |
|---|---|
| **+1** | All connectivity on the left (R ≈ 0) |
| **0** | Perfect symmetry (L = R) |
| **−1** | All connectivity on the right (L ≈ 0) |
| **Positive** | Left hemisphere > right for this ROI |
| **Negative** | Right hemisphere > left for this ROI |

**Example (thalamus):** L = 100, R = 90 → `side_ai ≈ +0.053` (slight left bias).

#### What `_ai.csv` is NOT

- **Not volumetric AI** — same formula is applied to ROI volume in
  `_volume_ai.csv` (§12.7); this file uses **connectivity strength** only.
- **Not SOZ-aligned AI** — `_ai.csv` uses left vs right, not ipsi vs contra.
  SOZ-aligned `soz_ai` is in `_soz_ai.csv` when SOZ side is in `participants.tsv`.
- **Not a substitute for Piper's mixed GLM** — complementary scalar for plots,
  screening, and correlations.
- **Not statistically tested** — no p-values or group contrasts; use
  `nodestrength analyze` or external stats on cohort tables.

### 12.4 Intrahemispheric-only strength and AI

#### Purpose

Same as §12.2–12.3, but node strength is computed from **within-hemisphere edges
only** (L↔L and R↔R). Cross-hemisphere / callosal edges are excluded before
summing. Useful for epilepsy analyses where interhemispheric connectivity may
dominate standard AI without reflecting local network imbalance.

#### Files

| File | Rows | Primary column |
|---|---|---|
| `strength/per_subject/sub-XXX_strength_intra.csv` | 84 | `strength_intra` |
| `strength/per_subject/sub-XXX_ai_intra.csv` | 42 | `side_ai`, `log_ai` |

#### Formula

```
    s_i^intra = Σ_{j: side(j) = side(i), j ≠ i} W_ij
    side_ai   = (L^intra − R^intra) / (L^intra + R^intra)
```

Implementation: `nodestrength.connectome.intrahemispheric_strengths_und()` +
`_pair_ai_table(..., "L_strength_intra", "R_strength_intra")` in `dkt-ai-cohort`.

Cohort stacks: `node_strength_intra_cohort.csv`, `asymmetry_index_intra_cohort.csv`,
`cohort_intra_summary.csv`.

The clinical PDF report includes a **key structures** table (Str AI, Intra AI,
Vol AI), **top-5 standard** and **top-5 intrahemispheric** asymmetry tables, and
two figures: cortical |AI| brain map and subcortical panel. Values are raw AI
(not normative z-scores). Research derivatives (`_soz_ai.csv`, `_strength_z.csv`)
are written separately when `--participants` is supplied.

### 12.5 Relationship between strength files

All strength paths are under `strength/`:

| | `_strength.csv` | `_ai.csv` | `_strength_intra.csv` | `_ai_intra.csv` |
|---|---|---|---|---|
| **Location** | `strength/per_subject/` | `strength/per_subject/` | `strength/per_subject/` | `strength/per_subject/` |
| **Unit** | Single hemisphere / node | L+R pair | Single hemisphere / node | L+R pair |
| **Rows** | 84 | 42 | 84 | 42 |
| **Primary value** | `strength` | `side_ai`, `log_ai` | `strength_intra` | `side_ai`, `log_ai` |
| **Depends on** | `dkt_connectome.csv` | `_strength.csv` | `dkt_connectome.csv` (intra mask) | `_strength_intra.csv` |
| **Use when** | Absolute connectivity per region | Left–right imbalance (all edges) | Local within-hemisphere connectivity | Left–right imbalance (intra only) |

Every value in `L_strength` and `R_strength` in `_ai.csv` is a direct lookup
from `_strength.csv` at the paired node indices. The AI file adds no new
imaging computation — only a deterministic transform of strength values.

### 12.6 Cohort-level counterparts

| Per-subject file | Cohort file | Description |
|---|---|---|
| `strength/per_subject/sub-XXX_strength.csv` | `strength/node_strength_cohort.csv` | All subjects stacked; same columns + `subject` |
| `strength/per_subject/sub-XXX_ai.csv` | `strength/asymmetry_index_cohort.csv` | All subjects stacked |
| `strength/per_subject/sub-XXX_strength_intra.csv` | `strength/node_strength_intra_cohort.csv` | All subjects stacked |
| `strength/per_subject/sub-XXX_ai_intra.csv` | `strength/asymmetry_index_intra_cohort.csv` | All subjects stacked |
| `volume/per_subject/sub-XXX_volume.csv` | `volume/node_volume_cohort.csv` | All subjects stacked *(with `--with-volume-ai`)* |
| `volume/per_subject/sub-XXX_volume_ai.csv` | `volume/volume_asymmetry_index_cohort.csv` | All subjects stacked *(with `--with-volume-ai`)* |
| — | `strength/cohort_summary.csv` | Per-ROI mean/SD of strength `side_ai` and `log_ai` |
| — | `strength/cohort_intra_summary.csv` | Per-ROI mean/SD of intrahemispheric `side_ai` and `log_ai` |
| — | `volume/cohort_volume_summary.csv` | Per-ROI mean/SD of volume `side_ai` and `log_ai` |
| — | `compare/strength_vs_volume_ai.csv` | Side-by-side strength AI vs volume AI per ROI |

### 12.7 `sub-XXX_volume.csv` and `sub-XXX_volume_ai.csv` *(optional)*

When `run_dkt_ai_cohort.py` is run with `--with-volume-ai`, two additional
per-subject files are written from `dk_nodes.mif`:

```
dkt_connectomes/sub-XXX/dk_nodes.mif   (84 labels on tractography grid)
                    │
                    ▼
         voxel count × voxel size (nodestrength.dk_atlas)
                    │
                    ▼
      volume/per_subject/sub-XXX_volume.csv       (84 rows — volume_mm3 per node)
                    │
                    ▼
      volume/per_subject/sub-XXX_volume_ai.csv    (42 rows — interhemispheric AI on volume)
```

**Volume source:** `dk_nodes.mif` on the QSIPrep/QSIRecon tractography grid —
same 84-node label space as `tck2connectome`. Not interchangeable with
FreeSurfer `segstats` volumes (different voxel grid).

**`_volume.csv` columns:** same identity columns as `_strength.csv`, with
`volume_mm3` instead of `strength`.

**`_volume_ai.csv` columns:** same pairing as `_ai.csv`, with
`L_volume_mm3`, `R_volume_mm3`, `side_ai`, and `log_ai` using the identical
formulas as strength AI.

**Caveats:** raw volumes (no ICV normalization); DK whole thalamus only.

### 12.8 `compare/strength_vs_volume_ai.csv` *(optional)*

When both strength and volume AI are computed, the runner merges cohort AI tables
into one comparison file under `compare/`:

| Column group | Contents |
|---|---|
| Keys | `subject`, `roi_name`, `region_type`, `L_index`, `R_index` |
| Strength | `L_strength`, `R_strength`, `strength_side_ai`, `strength_log_ai` |
| Volume | `L_volume_mm3`, `R_volume_mm3`, `volume_side_ai`, `volume_log_ai` |

One row per subject × ROI pair (210 rows for 5 subjects × 42 pairs). Use this
table for scatter plots, correlations, or screening where both modalities are
relevant; it does not replace mixed GLMs on normative z-scores.

### 12.9 Making results more paper-faithful

To move closer to Piper et al. 2026 inference:

1. **THOMAS nuclei** — replace whole-thalamus DK nodes with AV/CM/MDPf/PUL.
2. **Normative z-scoring** — pass `--participants` with control subjects to
   `dkt-ai-cohort` (fits `normative_strength_model.pkl` automatically), or use
   `nodestrength fit-normative` for IDEAS-style long tables.
3. **SOZ-aligned asymmetry** — `soz_ai` in `_soz_ai.csv` when SOZ side is in
   `participants.tsv` (also shown in the clinical PDF).
4. **Mixed-design GLM** — `nodestrength analyze --value strength` with Pillai's
   trace (paper Figures 3–4).

Raw `_strength.csv` and `_ai.csv` remain useful as transparent, per-subject
artefacts regardless of downstream normalization.
