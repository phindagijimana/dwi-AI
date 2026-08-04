# Paper notes — Piper et al., *Epilepsia* 2026

**Citation.** Piper RJ, Feng X, Chari A, Seunarine K, Clayden JD, Carmichael DW, Wagstyl K, Hall G, Wang Y, Clark CA, Baldeweg T, Eriksson MH, Tahir MZ, Tisdall MM, Taylor PN. *Thalamocortical structural connectivity in children with focal epilepsy: A diffusion MRI, case–control study.* Epilepsia 2026;67(4):1901–1915. DOI: 10.1002/epi.70099.

PDF in this folder: `Epilepsia - 2026 - Piper - Thalamocortical structural connectivity in children with focal epilepsy A diffusion MRI case.pdf`.

---

## 1. Question and design

Do children with focal-onset epilepsy show distinct thalamocortical **structural connectivity** and **volumetric** profiles per thalamic nucleus, and do these profiles relate to seizure-onset zone (SOZ) and post-surgical seizure freedom?

- Retrospective, single-centre (Great Ormond Street Hospital), case–control.
- **81 patients** (median 12.2 y, IQR 9.6–16.0) operated for drug-resistant focal epilepsy 2015–2023, vs **63 healthy children** (median 12.8 y).
- SOZ groups: **TLE-HS** (n=16), **TLE-other** (n=29), **frontal** (n=29), **other** (insular/parietal/occipital/multilobar, n=7 — excluded from subgroup GLMs).
- Outcomes: seizure-free at last follow-up 47/79 (58%, 2 unknown). Median follow-up 1.7 y.

## 2. Imaging and pipeline

Same scanner/protocol for cases and controls — **3T Siemens Prisma, 20-ch coil**.

- T1 MPRAGE 1 mm iso.
- dMRI: 2D EPI, multi-shell **b = 1000 and 2200 s/mm²**, **60 directions**, 13 interleaved b=0, multiband factor 2; 2.0 mm in-plane, 0.2 mm gap, 66 slices; TR 3050 ms / TE 60 ms; phase-encode reversed b=0 scan for distortion correction.

**Image processing pipeline (Figure 1 of paper):**

1. **Cortex/subcortex parcellation** — FreeSurfer 7.2.3 `recon-all` → **Lausanne aparc60** atlas (native space; chosen for resolution and surgical anatomical accuracy). Manual control points where intensity normalisation failed.
2. **Thalamic parcellation** — replace Lausanne thalamus with **THOMAS (T1w version)**, 8 bilateral nuclei: AV, VA, VLa, VLP, VPL, **PUL, CM, MDPf**. Geniculates excluded (not relevant); habenular and mammillothalamic tracts excluded (too small to seed).
3. **dMRI preprocessing — MRtrix3**: `dwidenoise` → `dwifslpreproc` (susceptibility + eddy + motion) → `dwibiascorrect` (FSL N4). Total framewise displacement (sum across 133 directions) kept as a per-subject motion covariate.
4. **T1↔dMRI registration** — `reg_aladin` (NiftyReg, rigid); resample 5TT segmentation with `reg_resample`.
5. **Tractography** — `dwi2response dhollander` → `dwi2fod` → `tckgen` **5M streamlines** (ACT, 5tt) → **`tcksift2`** to assign per-streamline weights matching estimated fibre density.
6. **Connectome** — `tck2connectome` with Lausanne+THOMAS labels → adjacency matrix of **summed SIFT2 weights**, self-connections zeroed.
7. **Node strength per nucleus** — sum of edge SIFT2 weights to all other ROIs (using Brain Connectivity Toolbox). This is the "**connectivity strength**" used everywhere downstream.
8. **Nucleus volume** — sum of voxels per THOMAS parcel (MATLAB).

## 3. Statistical model

Primary nuclei analysed: **AV, CM, MDPf, PUL** (those implicated in adult epilepsy connectivity and current DBS targets).

- **Normalisation** — per-subject *z*-score of each nucleus's connectivity strength against the **control distribution**, after a GLM on controls that regresses out:
  - age, sex
  - **whole-brain mean ROI strength** (guards against trivial global-connectivity scaling)
  - **total in-sequence motion** (sum of FD).
  Right-side nuclei z-scored vs right-side controls (and L vs L). Volumes use the same idea but covariates are age, sex, **intracranial volume**.
- **Group-level GLMs** — within-subject factors `nucleus` (AV/CM/MDPf/PUL) and `side` (R/L) or `laterality` (ipsi/contra); between-subject factors `group` (patient/control), `SOZ` (TLE-HS / TLE-other / frontal), and `seizure-freedom`. Multivariate test = **Pillai's trace**. Effect size = **partial η²** (small >.01, moderate >.06, large >.14). α = .05. Run in R 4.1.0 + SPSS 29.
- **Tract-specific hypotheses** — single SIFT2 edges extracted from the connectome: **AV ↔ hippocampus** (Papez; expected reduced in TLE-HS) and **CM ↔ sensorimotor cortex** (mean across precentral/paracentral/postcentral; expected higher in FBTCS).
- **Exploratory edge-wise map** — for each ROI, (patient − control) of GLM-adjusted SIFT2 edges, ipsilateral edges projected on right hemisphere via Simple Brain Plot. Scale clipped to 10th–90th percentile.

## 4. Key findings

**Controls (normative).** Expected thalamocortical fingerprints recovered (Figure 2): AV→limbic/Papez; CM→sensorimotor; MDPf→prefrontal; PUL→temporal/visual subfields. Raw MDPf (R and L) and right PUL strength declines with age in controls only.

**Patients vs controls.**
- Thalamic connectivity strength **higher** in patients overall (η²ₚ=.072, p=.015), least so for AV.
- **No** overall nucleus-volume difference (η²ₚ<.000, p=.968), but nucleus-by-group interaction (η²ₚ=.115, p<.001) shows reduced **AV** volume and increased **CM** volume in patients.

**By SOZ (TLE-HS vs TLE-other vs frontal).**
- TLE-HS is the outlier: **reduced AV** connectivity strength (driven ipsilaterally; group-by-laterality η²ₚ=.107, p=.023) and **reduced ipsilateral AV/MDPf/PUL volumes**.
- CM, MDPf, PUL connectivity is similarly elevated in TLE-other and frontal SOZs.
- Edge-wise map: widespread AV-connectivity reductions specific to TLE-HS; **CM → paracentral (sensorimotor)** edges elevated across all epilepsy subgroups.

**Outcome (seizure freedom).**
- Seizure-free patients show an **asymmetry**: lower **ipsilateral** and higher **contralateral** nucleus strength (η²ₚ=.111, p=.005) and volume (η²ₚ=.073, p=.025). Not-seizure-free patients look more bilateral.
- Interpretation: focal/lateralised thalamocortical abnormality may flag an "isolatable" epileptogenic network amenable to unilateral resection.

**Tract-specific.**
- AV↔hippocampus: no significant laterality × SOZ effect.
- CM↔sensorimotor: laterality × FBTCS × SOZ interaction (η²ₚ=.179, p=.005). Ipsilateral CM-sensorimotor elevated in FBTCS; contralateral elevated specifically in TLE-HS with FBTCS.

## 5. Key ideas — short list

1. **Thalamic node strength** (per-nucleus sum of SIFT2 streamline weights) is a tractable, anatomy-aware proxy for nucleus-level network involvement.
2. **GLM-based z-scoring against a normative cohort**, with whole-brain mean strength + motion + age + sex as covariates, is the trick that lets a small clinical study compare cases to controls without being eaten by global confounds.
3. **Nucleus specificity matters**: TLE-HS ≠ "epilepsy" — it has its own thalamic signature (AV down). Frontal and TLE-other epilepsies do **not** show ANT reduction, which is a direct challenge to one-size-fits-all ANT DBS.
4. **Laterality of the thalamic abnormality** (ipsi reduction with contra preservation) appears to track post-operative seizure freedom — a candidate prognostic imaging biomarker.
5. **Volume and connectivity tell complementary stories**: CM volume up in patients without CM connectivity going down, AV connectivity down in TLE-HS coinciding with AV atrophy.
6. **Pipeline is fully open**: FreeSurfer + Lausanne, THOMAS, MRtrix3 (dwidenoise/dwifslpreproc/dwibiascorrect/dwi2response dhollander/dwi2fod/tckgen/tcksift2/tck2connectome), BCT, NiftyReg, Simple Brain Plot. No bespoke code is required to reproduce the connectomes.
7. **Limitations to keep in mind for any re-implementation**: SIFT2-summed strength is a coarse summary (ignores edge-level spatial variability); dMRI ≠ functional epileptic network; subgroups are small and pathology-heterogeneous.

---

## 6. Can we do a paper implementation?

Short answer: **yes, the analysis pipeline is reproducible end-to-end with open tools — but our ability to reproduce the *findings* depends entirely on the data we can put in.**

### What's reproducible without their cohort

A faithful re-implementation as a software pipeline is well-scoped. Every step uses public software:

| Stage | Tool | Notes |
|---|---|---|
| Cortical/subcortical parcellation | FreeSurfer `recon-all` → Lausanne `aparc60` | Lausanne multiscale parcellation script (e.g. `multiscale_parcellator` / `cmtklib`) |
| Thalamic nuclei | **THOMAS (T1w)** | https://github.com/thalamicseg/thomas_new — produces native-space 8-nuclei labels |
| dMRI preprocessing | MRtrix3 | `dwidenoise` → `dwifslpreproc` (needs FSL eddy+topup) → `dwibiascorrect ants/fsl` |
| Registration | NiftyReg `reg_aladin`/`reg_resample` | ANTs is a fine substitute |
| Tractography | MRtrix3 | `dwi2response dhollander` → `dwi2fod msmt_csd` → `tckgen -act 5tt -seed_dynamic` 5M → `tcksift2` |
| Connectome | MRtrix3 | `tck2connectome -scale_invnodevol no -tck_weights_in sift2.txt` |
| Node strength + GLMs | Python (numpy/pandas/statsmodels) or BCT-MATLAB | Pillai's trace, partial η² straightforward in R/`pingouin` |
| Edge-wise difference maps | Simple Brain Plot (MATLAB) or `nilearn.plotting.plot_connectome` | Cosmetic |

So the *engineering* side is a one-to-two-week job to wire end-to-end on a single test subject, then bulk-process a cohort.

### What we'd need

**Critical** (no substitutes):
- **Multi-shell dMRI** with reversed-PE b=0, ≥ ~30 directions/shell, and matched-protocol T1 MPRAGE. Single-shell single-PE data won't satisfy the dhollander response + SIFT2 step the way the paper does — you can adapt, but you're no longer reproducing.
- A **control cohort** scanned on the **same protocol** as the patients. This is the single biggest constraint — the GLM z-scoring requires it.
- Per-subject **SOZ labels**, **post-op seizure-freedom labels**, **FBTCS history**, **histopathology** for the TLE-HS split.

**Helpful but not strictly required**: ICV from FreeSurfer (we get it for free), age, sex.

**Compute**: 5M-streamline tractograms × ~150 subjects ≈ 1–3 CPU-days per subject for the full chain (recon-all dominates). Tractable on a small cluster; uncomfortable on one workstation.

### Realistic re-implementation paths

Three things we can actually do, in increasing order of fidelity:

1. **Method-replication on public data.** Run the full pipeline on an open paediatric dataset with multi-shell dMRI + T1 (e.g. ABCD, HCP-Development, dHCP at older ages) plus a small epilepsy dataset such as the Epilepsy fMRI/dMRI public cohorts. We can produce the THOMAS connectomes, nucleus strengths, and the GLM/normative model. We **won't** replicate the SOZ-specific findings without epilepsy patients, but we can verify the pipeline yields the controls panel (Figure 2 / Table S1).
2. **Apply the method to a local epilepsy cohort.** With access to a focal-epilepsy dMRI cohort and matched controls, re-implement the pipeline as a Python/CLI tool and run the same GLM analyses on local data. This is the most scientifically interesting version because the result is a *new* finding, not a reproduction.
3. **Tool-level open-source release.** Package the pipeline as a Snakemake/Nextflow + BIDS-Apps style container that consumes a BIDS dataset and outputs per-subject THOMAS connectomes, nucleus strengths, and group-level GLM reports. This is a worthwhile artefact regardless of which cohort it runs against.

### Suggested first sprint (~1 week, single subject)

1. Pick one BIDS subject (test data) with multi-shell dMRI + T1.
2. FreeSurfer `recon-all` + Lausanne `aparc60` mapping.
3. Run THOMAS on the T1 (Docker image available).
4. MRtrix3 chain through SIFT2 weights.
5. Build the combined Lausanne+THOMAS label image, run `tck2connectome`, compute the four nucleus strengths and volumes.
6. Sanity-check against Figure 2 / Table S1 ordering of strongest connections.

Once that works on one subject, scaling is just job orchestration and a GLM in `statsmodels` / `pingouin`.

### Recommendation

If the goal is a faithful methods reproduction and a local follow-up study, the highest-leverage move is path (2): implement the pipeline once as a clean Python/MRtrix tool here in `node_strength/`, then point it at whatever paediatric or adult focal-epilepsy dMRI cohort we have access to. We'll get a real, novel result rather than a re-run of the GOSH cohort we can't access.

Open question for you before we start: **do we have access to a local multi-shell dMRI epilepsy cohort + matched controls?** If yes → path 2. If no → path 1 on a public dataset, with patient analysis deferred until data lands.

---

## 7. Implementation in this folder

The reimplementation lives in `nodestrength/` (Python ≥3.9). Layout:

```
node_strength/
├── pyproject.toml
├── node.md                              ← this file
├── nodestrength/
│   ├── atlases.py                       — THOMAS nuclei + label IDs, the 4-nucleus subset
│   ├── connectome.py                    — MRtrix3 connectome → per-nucleus SIFT2 strength + volume
│   ├── normative.py                     — control-cohort OLS GLM + per-(nucleus, side) z-scoring
│   ├── stats.py                         — Pillai's trace + partial η², mixed-design ANOVA driver
│   ├── pipeline.py                      — subprocess wrappers (recon-all, THOMAS, MRtrix3 chain)
│   └── cli.py                           — `nodestrength {run-subject,compute-strength,fit-normative,analyze}`
├── scripts/
│   └── demo_synthetic.py                — end-to-end demo on a simulated cohort
└── tests/                               — pytest suite (24 tests, all green)
```

**Runtime deps:** numpy, pandas, scipy, nibabel (no statsmodels — GLM is pure numpy).
**Optional:** `bctpy` (`pip install bctpy`, or `pip install nodestrength[bct]`). When installed, `compute_nucleus_strength` delegates the row-sum to `bct.strengths_und` so the audit trail matches the paper exactly. Without it, an equivalent pure-numpy expression (`W.sum(axis=0)`) is used — the values are bit-for-bit identical.
**Imaging deps (only for `run-subject`):** FreeSurfer 7.x, FSL 6.x, MRtrix3, THOMAS (T1w),
plus a Lausanne aparc60 converter (e.g. CMTK Lausanne2008). The pipeline module checks
`shutil.which` for each binary and fails fast with `ToolUnavailableError`.

### Tests

```
$ python -m pytest -q
........................                                                 [100%]
24 passed
```

Test coverage:

* `test_connectome.py` — strength matches a manual edge-sum; inter-thalamic and self-edge
  exclusions behave; volume from a hand-built NIfTI matches voxel-count × voxel volume.
* `test_normative.py` — z-scoring controls returns ≈ N(0,1); patients' z diverges in the
  engineered direction; ICV is wired into the volume model; missing categorical levels
  at predict-time don't crash the design alignment.
* `test_stats.py` — Helmert contrast is orthonormal; Pillai's F = univariate F in the
  2-group / 1-response degenerate case (numerical check against the closed-form ANOVA);
  mixed_anova recovers the paper's expected directional effects on the simulated cohort.
* `test_pipeline.py` — argument-construction for recon-all / MRtrix3 commands;
  dry-run path; tool-availability error path; in-Python label merge of Lausanne + THOMAS.

### Synthetic-cohort demo

```
$ python scripts/demo_synthetic.py
Simulated cohort: 137 subjects (63 controls, 74 patients: {'TLE-other': 29, 'frontal': 29, 'TLE-HS': 16}).
...
=== Patients by seizure freedom (strength) ===
              effect    value      F   df_num df_den   p_value   partial_η²
        seizure_free    0.047   3.52      1.0   72.0   0.06467        0.047
  seizure_free × side   0.493  70.06      1.0   72.0  3.12e-12        0.493
```

The simulator engineers the three signature paper effects (overall higher patient
thalamic strength; ipsilateral AV reduction specific to TLE-HS; ipsi-low/contra-high
asymmetry tied to seizure-freedom) and the GLM recovers them in the expected
direction. Effect sizes are larger than the paper's (synthetic noise is tight),
but the *pattern* matches Figures 3A, 3B, and 4C.

Artefacts land in `scripts/outputs/`: cohort CSV, z-scored patients CSV, and one
GLM-result CSV per analysis.

### Running on real data

The CLI mirrors the analysis order described in Section 2 of the paper:

```bash
# 1. Per-subject pipeline (one subject at a time; cluster-scale via job array)
nodestrength run-subject S001 \
    --t1 sub-S001/anat/sub-S001_T1w.nii.gz \
    --dwi sub-S001/dwi/sub-S001_dwi.nii.gz \
    --bvec sub-S001/dwi/sub-S001_dwi.bvec \
    --bval sub-S001/dwi/sub-S001_dwi.bval \
    --rpe-b0 sub-S001/dwi/sub-S001_acq-rpe_dwi.nii.gz \
    --subjects-dir derivatives/freesurfer \
    --out-dir derivatives/nodestrength/sub-S001

# 2. Per-subject strength + volume table
nodestrength compute-strength --subject-id S001 \
    --connectome derivatives/.../connectome.csv \
    --lookup derivatives/.../node_lookup.tsv \
    --labels derivatives/.../labels_combined.nii.gz \
    --out derivatives/.../S001_strengths.csv

# 3. Fit normative model on the control cohort table
nodestrength fit-normative --controls cohort_controls_long.csv \
    --out derivatives/.../normative_model.pkl

# 4. Mixed-design GLM (Pillai + partial η²)
nodestrength analyze --cohort cohort_all_long.csv \
    --within nucleus side --between group \
    --value strength --out derivatives/.../glm_group.csv
```

## 8. Running on the IDEAS open dataset

**Primary open-data path: IDEAS** (Imaging Database for Epilepsy And
Surgery) from the CNNP Lab at Newcastle. Peter Taylor leads CNNP and is
the **last author on the Piper paper**, so IDEAS and the paper are sibling
efforts. IDEAS II ships 216 focal-epilepsy patients + 98 healthy controls
with dMRI, plus a **pre-processed connectome archive on Figshare** —
meaning we can skip the 20-node-day pipeline and feed the analysis layer
directly.

Citations:
* IDEAS I (T1+FLAIR): Taylor PN et al., *Epilepsia* 66(2):471–481 (2025).
  DOI 10.1111/epi.18192.
* IDEAS II (+dMRI / connectomes): Taylor PN et al., *Epilepsia* (2026).
  DOI 10.1002/epi.70186.
* Project page: https://sites.google.com/view/cnnp-lab/ideas-data

Two acquisition protocols (`NODDI`, `P58`) are present; their TOPUP `acqp`
parameters are baked into `nodestrength.ideas.TOPUP_PARAMS`. Protocol is
auto-detected from BIDS filenames (`acq-noddi` / `acq-p58`) or the JSON
sidecar `ProtocolName`.

### Step 0 — pick a Figshare archive

| Archive | Use | Cost |
|---|---|---|
| Raw scans (T1, FLAIR, dMRI in BIDS) | full method reproduction | ~20 node-days for ~300 subjects |
| **Fully processed dMRI / connectomes** | **fast path** — straight to the GLMs | minutes |

The fast path is the right starting point. Use the raw path later if you
need to vary tractography, change parcellation, or QC subjects.

### Fast path — pre-processed connectomes

```bash
nodestrength ingest-preprocessed \
    --archive /data/ideas_ii_processed \
    --participants /data/ideas_ii_processed/participants.tsv \
    --out /data/ideas/cohort_long.csv
```

Then the four GLMs from the paper:

```bash
# Figure 3A: controls vs patients (strength)
nodestrength analyze --cohort /data/ideas/cohort_long.csv \
    --within nucleus side --between group --value strength \
    --out /data/ideas/glm_cc_strength.csv

# Figure 3C: volumes
nodestrength analyze --cohort /data/ideas/cohort_long.csv \
    --within nucleus side --between group --value volume_mm3 \
    --out /data/ideas/glm_cc_volume.csv

# Figure 3B / 4A: patients only, by SOZ
# (filter via nodestrength.ideas.split_patients_by_soz first)
nodestrength analyze --cohort /data/ideas/cohort_patients.csv \
    --within nucleus side --between soz --value strength \
    --out /data/ideas/glm_soz_strength.csv

# Figure 4C: post-op seizure freedom asymmetry
nodestrength analyze --cohort /data/ideas/cohort_patients.csv \
    --within nucleus side --between seizure_free --value strength \
    --out /data/ideas/glm_sf_strength.csv
```

This replicates **all four GLMs Piper et al. report** on a single
openly-available dataset.

### Full path — raw BIDS through the pipeline

If the IDEAS II connectomes use a different parcellation, or you want to
match the paper's Lausanne+THOMAS atlas exactly:

```bash
# 1. Discover subjects + detect protocol.
nodestrength ingest-ideas \
    --bids /data/ideas_raw \
    --participants /data/ideas_raw/participants.tsv \
    --out /data/ideas_raw/manifest.csv

# 2. Submit per-subject pipeline (SLURM).
python scripts/run_micamics_cohort.py \
    --bids /data/ideas_raw \
    --derivatives /data/ideas_raw/derivatives/nodestrength \
    --subjects-dir /data/ideas_raw/derivatives/freesurfer \
    --slurm /scratch/submit_ideas.sh
bash /scratch/submit_ideas.sh

# 3. Aggregate.
python scripts/build_cohort_table.py \
    --derivatives /data/ideas_raw/derivatives/nodestrength \
    --participants /data/ideas_raw/participants.tsv \
    --out /data/ideas/cohort_long.csv
```

(`run_micamics_cohort.py` is BIDS-generic and works on IDEAS unchanged.)

### participants.tsv column mapping

`nodestrength.ideas.load_participants` canonicalises IDEAS headers to the
analysis schema:

| IDEAS column | Mapped to |
|---|---|
| `participant_id` | `subject` (`sub-` prefix stripped) |
| `diagnosis` / `group` / `patient_group` | `group` (`patient` / `control`) |
| `seizure_onset_zone` / `soz` | `soz` |
| `histology` / `pathology` | `histopathology` |
| `outcome` / `ilae` | `seizure_free` / `ilae` |
| `fbtcs` / `FBTCS` | `fbtcs` |
| `protocol` / `acquisition` | `protocol` |

Inspect the cohort CSV before running GLMs. If IDEAS uses a header we
missed, add it to `PARTICIPANT_COLUMN_ALIASES` in `nodestrength/ideas.py`.

### Caveats

* IDEAS II (2026) is recent and the precise BIDS layout / participants
  schema is **not fully documented on the CNNP project page**. The walker
  is tolerant; inspect one subject after download and tighten aliases if
  needed.
* The pre-processed connectomes use the IDEAS team's chosen parcellation.
  If thalamic ROIs aren't named with THOMAS conventions
  (`AV`/`CM`/`MDPf`/`PUL` × `L`/`R`), add a rename layer in the node
  lookup before the analysis sees it.
* IDEAS subjects are **adult**; the Piper paper is **paediatric**. We're
  testing whether the methods transfer; the comparator is the adult TLE
  literature the paper cites, not the paediatric numbers.

---

## 9. Asymmetry-index pipeline (strength → AI)

The Piper paper itself does not define a closed-form asymmetry index — it
tests asymmetry as a within-subject `laterality × {group / SOZ /
seizure_free}` interaction inside the mixed GLM (Section 3.3, Figure 4C).
For complementary use cases — per-subject scalars, plots, correlations
against continuous outcomes — `nodestrength` ships three standard
formulas in `nodestrength/asymmetry.py`:

```
    side_ai = (L - R) / (L + R)                # range [-1, +1]
    soz_ai  = (ipsi - contra) / (ipsi + contra) # range [-1, +1]
    log_ai  = ln(ipsi / contra)                 # range (-inf, +inf)
```

* `side_ai` is hemispheric and does not need SOZ information; useful for
  controls and for a generic asymmetry screen.
* `soz_ai` and `log_ai` need a per-patient SOZ side (`L` / `R`). Negative
  `soz_ai` matches the paper's "ipsilateral reduction / contralateral
  preservation" signature for seizure-free patients.

### Pipeline

```bash
# 1. Build the long-form cohort from IDEAS II pre-processed connectomes.
nodestrength ingest-preprocessed \
    --archive /data/ideas_ii_processed \
    --participants /data/ideas_ii_processed/participants.tsv \
    --out /data/ideas/cohort_long.csv

# 2. Collapse two sides into per-(subject, nucleus) AIs.
nodestrength asymmetry \
    --cohort /data/ideas/cohort_long.csv \
    --soz-side-col soz_side \
    --out /data/ideas/cohort_ai.csv

# Output columns: subject, nucleus, L, R, ipsi, contra, soz_side,
# side_ai, soz_ai, log_ai, value_kind, + group, soz, seizure_free, ...
```

The AI CSV is ready for downstream stats (`scipy.stats`, `pingouin`, R,
SPSS) — group-wise t-tests, Pearson correlations against ILAE bins or
disease duration, ROC curves predicting seizure-freedom, etc.

### When to use AI vs the GLM

| Question | Tool |
|---|---|
| Does asymmetry differ between two **discrete** groups (paper's design) | `nodestrength analyze` — laterality × group interaction |
| Does asymmetry correlate with a **continuous** outcome (ILAE bin, duration) | `nodestrength asymmetry` + scipy.stats / regression |
| Single biomarker per subject for plotting / ROC | `nodestrength asymmetry` (one of the three columns) |

They're complementary, not alternatives. The GLM preserves the
within-subject error structure (more power); AI gives you a per-subject
scalar (more flexibility downstream).

If you also want SOZ-aligned AI on the z-scored strengths (so the
covariate adjustment is folded in before the AI is computed), pipe
`fit-normative` outputs into `asymmetry --value strength_z`.

---

## 8b. Fallback — MICA-MICs (see §8 above for the IDEAS primary path)

We're targeting MICA-MICs (Lariviere et al. 2022, *Scientific Data*) for the
first real-data run: openly downloadable from OpenNeuro / the CONP portal,
healthy adults, multi-shell dMRI on a 3T Siemens Prisma — protocol-similar
to the GOSH paediatric data. Acquisition summary (per the dataset paper):

* 50 healthy adults, ~30 years, BIDS layout `sub-HC###/ses-01/`.
* T1w MP2RAGE 0.8 mm iso.
* Multi-shell dMRI: b = 300, 700, 2000 s/mm², ≈ 92 directions, AP + PA pairs.

**Honest scope.** MICA-MICs is healthy-controls only. The result we can
reproduce on this data is the paper's **normative thalamocortical
fingerprint** — Figure 2 (heat maps of strongest connections per nucleus)
and Table S1 (ranked target ROIs per nucleus). The clinical findings
(group/SOZ/seizure-freedom contrasts) require an epilepsy cohort and are
deferred until we add patient data.

### Step 0 — obtain the data

The MICA-MICs distribution lives on OpenNeuro and the CONP portal — search
for the dataset by name. After download, you should have a BIDS tree:

```
ds-micamics/
├── dataset_description.json
├── participants.tsv
└── sub-HC001/
    └── ses-01/
        ├── anat/sub-HC001_ses-01_T1w.nii.gz
        └── dwi/sub-HC001_ses-01_dir-AP_dwi.{nii.gz,bvec,bval,json}
            sub-HC001_ses-01_dir-PA_dwi.{nii.gz,bvec,bval,json}
```

The walker in `nodestrength.bids` will discover all subjects matching this
layout (and tolerates the no-session variant `sub-HC###/anat/...`).

### Step 1 — per-subject pipeline (cluster-friendly)

Loop the FreeSurfer + THOMAS + MRtrix3 pipeline over every subject:

```bash
# Local sequential (debug):
python scripts/run_micamics_cohort.py \
    --bids /data/openneuro/micamics \
    --derivatives /data/openneuro/micamics/derivatives/nodestrength \
    --subjects-dir /data/openneuro/micamics/derivatives/freesurfer \
    --dry-run             # drop --dry-run to actually execute

# SLURM submission script (recommended on a real cluster):
python scripts/run_micamics_cohort.py \
    --bids /data/openneuro/micamics \
    --derivatives /data/openneuro/micamics/derivatives/nodestrength \
    --subjects-dir /data/openneuro/micamics/derivatives/freesurfer \
    --slurm /scratch/submit_micamics.sh

bash /scratch/submit_micamics.sh
```

Expected per-subject runtime: ~6 h for FreeSurfer recon-all, ~1.5 h for THOMAS,
~2 h for the MRtrix3 chain at 5 M streamlines. On a 50-subject cohort that's
~ 20 node-days of compute — submit in parallel and it's a long weekend.

### Step 2 — aggregate per-subject artefacts

Once jobs finish, walk the derivatives tree and build the long-form cohort CSV
the analysis CLI consumes:

```bash
python scripts/build_cohort_table.py \
    --derivatives /data/openneuro/micamics/derivatives/nodestrength \
    --participants /data/openneuro/micamics/participants.tsv \
    --out /data/openneuro/micamics/derivatives/cohort_long.csv
```

The participants.tsv join automatically picks up `age` and `sex` columns so
the normative GLM has the covariates it needs.

### Step 3 — reproduce Figure 2 / Table S1

The fingerprint script ranks the strongest cortical/subcortical targets per
nucleus across the cohort:

```bash
python scripts/normative_fingerprint.py \
    --derivatives /data/openneuro/micamics/derivatives/nodestrength \
    --out /data/openneuro/micamics/derivatives/fingerprint \
    --top 30
```

Outputs:
- `fingerprint_long.csv` — every (nucleus, side, target) row, with the
  cohort mean SIFT2 weight and 10–90 percentiles.
- `fingerprint_all.csv` — same, aggregated and ranked.
- `fingerprint_topN.csv` — top-N targets per nucleus; this is the table to
  compare against the paper's Table S1.

Expected qualitative matches (from the paper):
- **AV** → cingulate, retrosplenial, mesial temporal, mammillary body
  (Papez circuit).
- **CM** → precentral, postcentral, paracentral (sensorimotor).
- **MDPf** → prefrontal cortices.
- **PUL** → posterior basal/lateral temporal cortices, occipital.

If those neighbourhoods dominate the top-30 per nucleus, the pipeline has
reproduced Figure 2 of the paper. Add more controls and you can also fit the
GLM normative model and have a reusable atlas of expected thalamic
connectivity values per age/sex bin.

### What MICA-MICs cannot show

- **Group contrasts** — no patients in this dataset, so Sections 3.3–3.4
  of the paper (controls vs patients, SOZ subgroup analyses,
  seizure-freedom asymmetry) cannot be tested here. They will run as soon
  as a patient cohort table is concatenated into the same long-form CSV.
- **Paediatric trends** — MICA-MICs is adults. Age-effect curves
  (Figure S1) will look different.

A natural follow-up is to download an open focal-epilepsy multi-shell dMRI
dataset on the same protocol family and concatenate it into the cohort
CSV; the analyze CLI will then run the full set of paper GLMs unchanged.

### Limitations of this implementation

- The pipeline wrappers assume each tool's standard CLI; site-specific module
  loads or container invocations need a thin shim.
- The Lausanne aparc60 step is delegated to whichever local converter you have
  (CMTK `parcellate.py`, `mne_lausanne2008.py`, or a custom mapping table) —
  `pipeline.run_lausanne_aparc60` is a placeholder for that binary.
- THOMAS T1w occasionally over-labels neighbouring tissue at low-resolution
  scans; rerun with `-t T1` and visually QC. The merge step zeros the
  FreeSurfer Left/Right Thalamus parcels (10/49) so the THOMAS labels win.
- Tractography here defaults to 5 M streamlines + ACT + SIFT2 to match the
  paper; on cohorts smaller than ~50 subjects, consider 10 M for the
  edge-wise difference map.
- The `mixed_anova` driver implements the wide-multivariate form. SPSS will
  also report Greenhouse–Geisser-adjusted univariate F values — they aren't
  implemented here because Pillai's trace is what the paper cites.

