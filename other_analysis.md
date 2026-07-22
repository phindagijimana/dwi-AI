# Other analyses on DK connectome results

Companion to [`nodestrength.md`](nodestrength.md) §11–12. Summarizes what is
**already computed** on the Gugger Lab `dwi_test2` cohort, what the
**`node_strength` package supports but has not been run** on DK data yet, and
what is **possible from the raw 84×84 connectome** with additional work.

Inputs assumed per subject:

- `dk_connectomes/sub-XXX/dk_connectome.csv` — 84×84 SIFT2-weighted, symmetric
- `dk_connectomes/sub-XXX/dk_nodes.mif` — 84-node label grid (for volume)

Current outputs: `node_strength_results/` with `strength/`, `volume/`, and
`compare/` subfolders.

---

## Already done (dwi_test2)

| Analysis | Output | Question |
|---|---|---|
| **Node strength** | `strength/per_subject/*_strength.csv` | How connected is each of 84 DK regions? |
| **Strength interhemispheric AI** | `strength/per_subject/*_ai.csv` | Is connectivity left–right asymmetric per ROI pair? |
| **ROI volume + volume AI** | `volume/per_subject/*_volume.csv`, `*_volume_ai.csv` | Is tissue volume left–right asymmetric? |
| **Strength vs volume comparison** | `compare/strength_vs_volume_ai.csv` | Do connectivity and volume asymmetry agree per ROI? |

Regenerate:

```bash
python scripts/run_dk_ai_cohort.py \
    --root /path/to/dk_connectomes \
    --out  /path/to/node_strength_results \
    --with-volume-ai
```

---

## Ready in the package — not yet run on DK

These work on DK data once you add **covariates** and/or **clinical labels**.

### 1. Normative z-scoring

Compare each subject to a **control cohort** after adjusting for age, sex, motion,
and mean-brain strength (Piper et al. 2026 style).

```bash
nodestrength fit-normative \
    --controls controls_long.csv \
    --out strength_model.pkl

python scripts/score_connectomes.py \
    --root /path/to/derivatives \
    --out  /path/to/out \
    --covariates covariates.csv \
    --model strength_model.pkl
```

**Needs:** matched controls + `participants.tsv` (age, sex, motion).

**Volume analogue:** `fit_volume_model()` with age, sex, ICV covariates.

### 2. SOZ-aligned asymmetry (`soz_ai`)

Reframe left/right as ipsilateral/contralateral relative to seizure onset zone:

```
soz_ai  = (ipsi − contra) / (ipsi + contra)    range [−1, +1]
log_ai  = ln(ipsi / contra)
```

Implemented in `nodestrength/asymmetry.py`. Distinct from interhemispheric
`side_ai` on `_ai.csv`.

**Needs:** per-patient SOZ side (L/R). Meaningful for epilepsy patients, not
controls.

```bash
nodestrength asymmetry \
    --cohort cohort_long.csv \
    --soz-side-col soz_side \
    --out cohort_soz_ai.csv
```

### 3. Group GLMs (Pillai's trace)

Paper-style mixed-design inference: group × side, SOZ × laterality,
seizure-freedom × laterality.

```bash
nodestrength analyze \
    --cohort cohort_long.csv \
    --within side \
    --between group \
    --value strength \
    --out glm_group_strength.csv
```

**Needs:** sufficient sample size + group labels (patient/control, SOZ, outcome).
With the current **5-subject** dwi_test2 cohort, inferential GLMs are
underpowered — use for pipeline validation or wait for a larger cohort.

### 4. Permutation diagnostics

Non-parametric check on mixed-ANOVA effects:

```bash
python scripts/run_diagnostics.py \
    --cohort cohort_long.csv \
    --out  diagnostics/ \
    --effect group
```

### 5. ICV-adjusted volume z-scoring

Same normative framework as strength, applied to `volume_mm3` with age, sex, and
intracranial volume as covariates. Requires a control cohort with ICV from
FreeSurfer.

---

## Possible from the raw 84×84 connectome

The connectome matrix is a full weighted graph. Analyses beyond scalar node
strength are possible but **not all are implemented** in `run_dk_ai_cohort.py`.

| Analysis type | Examples | Notes |
|---|---|---|
| **Edge-level** | Single ROI–ROI SIFT2 weights (e.g. thalamus ↔ hippocampus) | Piper tract-specific hypotheses; read directly from `dk_connectome.csv` |
| **Network metrics (BCT)** | Clustering, characteristic path length, global/local efficiency, modularity | Standard graph theory on the 84-node DK graph via `bctpy` |
| **Hub identification** | Rank nodes by strength, betweenness, participation coefficient | Identify highly connected or central DK regions |
| **Community structure** | Modularity optimization, community detection | Anatomical/functional modules in DK parcellation space |
| **Rich-club / core–periphery** | Backbone of strongest inter-regional connections | Higher-order topology beyond node strength |
| **Thresholded networks** | Sparsify at fixed edge density or weight cutoff | Sensitivity analysis — results depend on threshold choice |
| **Edge-wise difference maps** | Patient − control per edge, ipsi/contra projections | Exploratory whole-brain maps (Piper supplementary style) |
| **Correlation with clinical variables** | Strength or AI vs seizure freedom, duration, ILAE | Join existing CSVs with an external clinical spreadsheet |
| **Multivariate / ML** | Classify outcome from 84 strengths or 42 AI values | Needs larger N; high risk of overfitting at N=5 |
| **Longitudinal** | Δ strength or Δ AI between timepoints | Requires repeat scans and aligned parcellations |

---

## DK-specific upgrades (larger lift)

| Upgrade | What it unlocks |
|---|---|
| **THOMAS thalamic nuclei** | Per-nucleus AV/CM/MDPf/PUL strength and AI — Piper-faithful thalamus analysis (DK gives whole thalamus only) |
| **FreeSurfer `segstats` volumes** | Anatomical ROI volumes on native FreeSurfer grid (alternative to tractography-grid `dk_nodes.mif`) |
| **Exclude inter-thalamic edges** | Already supported for THOMAS in `connectome.py`; could be adapted for DK whole-thalamus strength |
| **Cross-modality with ASL-AI / PET-AI** | Same interhemispheric AI formula on CBF or PET — lab ASL-AI pipeline is a direct analogue |

See [`nodestrength.md`](nodestrength.md) §12.9 and [`paper.md`](paper.md) for
moving toward Piper et al. 2026 inference.

---

## Practical recommendations for dwi_test2 (N = 5)

Full GLMs and normative models need **more subjects and controls**. Near-term
value from the current cohort:

1. **Descriptive** — cohort summaries already in `strength/cohort_summary.csv`
   and `volume/cohort_volume_summary.csv`; inspect thalamus and other ROIs of
   interest per subject.
2. **Edge screening** — extract specific edges from `dk_connectome.csv` (e.g.
   L/R thalamus → hippocampus, thalamus → precentral) for hypothesis-driven
   tables or plots.
3. **Strength–volume divergence** — scatter or correlate `strength_side_ai` vs
   `volume_side_ai` from `compare/strength_vs_volume_ai.csv`.
4. **Prepare for scale-up** — assemble `participants.tsv` (age, sex, motion,
   ICV, group, SOZ, outcome) so normative z-scoring and GLMs are ready when the
   cohort grows.

---

## Summary tiers

| Tier | Analyses |
|---|---|
| **Done** | Node strength, strength AI, volume AI, strength vs volume compare |
| **Package ready; needs labels/controls** | Normative z-scores, SOZ-AI, group GLMs, permutation diagnostics |
| **Connectome-native; needs scripts or new code** | Edge-level weights, BCT graph metrics, hubs, communities, ML |
| **Atlas upgrade** | THOMAS nuclei for Piper-faithful thalamic nucleus analysis |

---

## Related documentation

| File | Contents |
|---|---|
| [`nodestrength.md`](nodestrength.md) §11 | Gugger Lab runbook, cohort status, output layout |
| [`nodestrength.md`](nodestrength.md) §12 | Per-file definitions for `_strength.csv`, `_ai.csv`, volume, compare |
| [`paper.md`](paper.md) | Piper et al. 2026 — methods and findings |
| [`BCT.md`](BCT.md) | Node strength and BCT `strengths_und` |
| [`node.md`](node.md) | IDEAS/MICA-MICs runbooks, THOMAS pipeline notes |
