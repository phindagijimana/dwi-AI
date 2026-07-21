# Paper summary — Piper et al., *Epilepsia* 2026

**Citation.** Piper RJ, Feng X, Chari A, Seunarine K, Clayden JD, Carmichael DW, Wagstyl K, Hall G, Wang Y, Clark CA, Baldeweg T, Eriksson MH, Tahir MZ, Tisdall MM, Taylor PN. *Thalamocortical structural connectivity in children with focal epilepsy: A diffusion MRI, case–control study.* **Epilepsia** 2026;67(4):1901–1915. DOI: [10.1002/epi.70099](https://doi.org/10.1002/epi.70099).

PDF in this repo: `Epilepsia - 2026 - Piper - Thalamocortical structural connectivity in children with focal epilepsy A diffusion MRI case.pdf`.

For implementation runbooks and IDEAS/MICA-MICs notes, see [`node.md`](node.md). For how this repo applies the methods on DK connectomes, see [`nodestrength.md`](nodestrength.md) §11–12.

---

## One-sentence summary

Children with focal epilepsy show **nucleus-specific thalamic structural connectivity and volume changes** that differ by **seizure-onset zone (SOZ)** and relate to **post-surgical seizure freedom**, with **TLE-hippocampal sclerosis (TLE-HS)** showing a distinct **anterior thalamic (AV) reduction** not seen in other SOZ groups.

---

## Question and design

**Primary question:** Do children with focal-onset epilepsy have distinct **per-nucleus thalamic structural connectivity** and **volume** profiles, and do these relate to SOZ and surgical outcome?

| Item | Detail |
|------|--------|
| Design | Retrospective single-centre case–control (Great Ormond Street Hospital) |
| Patients | 81 operated for drug-resistant focal epilepsy (2015–2023); median age 12.2 y |
| Controls | 63 healthy children; median age 12.8 y |
| Scanner | 3T Siemens Prisma, 20-channel head coil |
| SOZ groups | TLE-HS (16), TLE-other (29), frontal (29), other (7 — excluded from subgroup GLMs) |
| Outcome | Seizure-free at last follow-up: 47/79 (58%); median follow-up 1.7 y |

---

## Imaging pipeline (Figure 1)

1. **Parcellation** — FreeSurfer `recon-all` → **Lausanne aparc60** (cortex/subcortex).
2. **Thalamus** — Replace Lausanne thalamus with **THOMAS (T1w)**: 8 bilateral nuclei; primary analysis on **AV, CM, MDPf, PUL**.
3. **dMRI** — MRtrix3: `dwidenoise` → `dwifslpreproc` → `dwibiascorrect`.
4. **Registration** — NiftyReg rigid T1↔dMRI; resample 5TT.
5. **Tractography** — `dwi2response dhollander` → `dwi2fod` → **`tckgen` 5M streamlines** (ACT, 5TT) → **`tcksift2`**.
6. **Connectome** — `tck2connectome`; **summed SIFT2 weights**; zero diagonal.
7. **Node strength** — Sum of edge weights per nucleus via **Brain Connectivity Toolbox** (see [`BCT.md`](BCT.md)).
8. **Volume** — Voxel count per THOMAS parcel.

Acquisition: T1 MPRAGE 1 mm; multi-shell dMRI **b = 1000 and 2200 s/mm²**, 60 directions, reversed-PE b=0 for distortion correction.

---

## Statistical model

### Normative z-scoring (controls)

Per nucleus, per side, fit OLS on **controls** and z-score patients (and controls) on residuals:

**Strength covariates:** age, sex, **whole-brain mean ROI strength**, total dMRI motion (sum FD).

**Volume covariates:** age, sex, **intracranial volume (ICV)**.

Right-side nuclei z-scored against right-side controls (and L vs L).

### Group GLMs

| Factor type | Levels |
|-------------|--------|
| Within-subject | `nucleus` (AV, CM, MDPf, PUL); `side` (L/R) or `laterality` (ipsi/contra) |
| Between-subject | `group` (patient/control); `SOZ`; `seizure-freedom` |

- Test statistic: **Pillai's trace**
- Effect size: **partial η²** (small > .01, moderate > .06, large > .14)
- α = .05

### Additional analyses

- **Tract-specific edges:** AV↔hippocampus; CM↔sensorimotor cortex (precentral/paracentral/postcentral mean).
- **Exploratory edge-wise maps:** patient − control on GLM-adjusted SIFT2 edges.

**Note:** The paper tests **laterality in mixed GLMs**; it does **not** define a single closed-form “asymmetry index” column like `(L−R)/(L+R)`. This repo ships such formulas as complementary scalars ([`nodestrength.md`](nodestrength.md) §12).

---

## Key findings

### Controls (normative fingerprint)

Expected thalamocortical connectivity patterns recovered (Figure 2):

| Nucleus | Main connectivity fingerprint |
|---------|------------------------------|
| **AV** | Limbic / Papez (hippocampus, cingulate) |
| **CM** | Sensorimotor cortex |
| **MDPf** | Prefrontal cortex |
| **PUL** | Temporal / visual subfields |

MDPf and right PUL strength decline with age in controls.

### Patients vs controls

- Thalamic connectivity strength **higher in patients overall** (η²ₚ = .072, p = .015); effect weakest for AV.
- **No overall volume difference**, but **nucleus × group interaction**: **AV volume down**, **CM volume up** in patients.

### By SOZ

- **TLE-HS** is distinct: **reduced AV connectivity** (ipsilateral drive; laterality × group η²ₚ = .107, p = .023) and **reduced ipsilateral AV/MDPf/PUL volumes**.
- TLE-other and frontal groups: elevated CM, MDPf, PUL connectivity (not AV-specific reduction).
- Edge-wise: AV reductions specific to TLE-HS; **CM → paracentral** elevated across epilepsy subgroups.

### Surgical outcome

- **Seizure-free** patients: **lower ipsilateral**, **higher contralateral** nucleus strength (η²ₚ = .111, p = .005) and volume (η²ₚ = .073, p = .025).
- Interpretation: focal/lateralised thalamic abnormality may mark an **isolatable** epileptogenic network.

### Tract-specific

- AV↔hippocampus: no significant laterality × SOZ effect.
- CM↔sensorimotor: laterality × FBTCS × SOZ interaction (η²ₚ = .179, p = .005).

---

## Key ideas (takeaways)

1. **Thalamic node strength** (per-nucleus sum of SIFT2 streamline weights) is an anatomy-aware summary of nucleus-level structural network involvement.
2. **Normative GLM z-scoring** (age, sex, motion, mean-brain strength) lets a modest cohort compare patients to controls without global scaling artefacts.
3. **Nucleus and SOZ specificity matter** — TLE-HS ≠ “epilepsy”; AV reduction is not universal; challenges one-size-fits-all anterior-thalamic DBS.
4. **Laterality tracks outcome** — ipsilateral reduction with contralateral preservation associates with seizure freedom; candidate prognostic biomarker.
5. **Connectivity and volume are complementary** — e.g. CM volume up without CM connectivity down; AV connectivity down in TLE-HS with AV atrophy.
6. **Pipeline is open-source** — FreeSurfer, Lausanne, THOMAS, MRtrix3, BCT, NiftyReg; connectomes reproducible without proprietary code.
7. **Limitations** — SIFT2 strength is a coarse summary; dMRI ≠ functional epileptic network; small heterogeneous subgroups.

---

## Relation to this repository

| Paper element | This repo (`nodestrength`) |
|---------------|----------------------------|
| Atlas | Paper: Lausanne + **THOMAS nuclei**. Gugger Lab DK path: **84-node Desikan–Killiany** (whole thalamus). |
| Node strength | Same BCT `strengths_und` concept ([`BCT.md`](BCT.md)) |
| Normative GLM | Implemented (`nodestrength.normative`); not yet run on dwi_test2 |
| Mixed GLM (Pillai) | Implemented (`nodestrength.stats`); demo on synthetic data |
| Interhemispheric AI scalar | **Not in paper**; complementary (`nodestrength.asymmetry`) |
| IDEAS II cohort | Supported via `nodestrength.ideas` ([`node.md`](node.md)) |

The **`node_strength` package implements the analysis layer** Piper et al. describe; the Gugger Lab **QSIPrep → QSIRecon → DK** path is documented separately in `DWI_Connectivity_Pipeline_Documentation.md` on the dwi_test2 share.

---

## References

- Piper RJ et al. *Epilepsia* 2026. DOI [10.1002/epi.70099](https://doi.org/10.1002/epi.70099)
- Rubinov M, Sporns O. BCT node strength. *NeuroImage* 2010 — see [`BCT.md`](BCT.md)
- Tournier J-D et al. MRtrix3. *NeuroImage* 2019
