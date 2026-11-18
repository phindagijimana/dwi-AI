# Statistics this project actually runs

Graph theory stops when \(s_i\) and AI exist. The rest is ordinary biomedical statistics. Mixing the two layers — treating a GLM as if it were a new network invariant — is how papers become unreproducible.

This page is the statistical stack **as implemented**, with the literature it sits in, and the disagreements that look like “maths changes” but are not.

## Per-subject features (the input to statistics)

From [Node strength](strength.md) and [Asymmetry](asymmetry.md):

- Node strength, intrahemispheric, interhemispheric
- Side AI, optional SOZ-aligned AI, log-ratio
- Optional volume and volume AI
- Optional global strength \(\frac12\sum_i s_i\) as a covariate

These are **features**. They are not p-values.

## ROC for a single biomarker

Given a scalar (hippocampal AI, volume AI) and a binary label (left-HS vs control):

- Plot TPR vs FPR as the threshold moves; **AUC** is \(P(\text{score}_{\mathrm{pos}}>\text{score}_{\mathrm{neg}})\) for a continuous score (Hanley & McNeil 1982).
- Correlated AUCs (same patients, two biomarkers): DeLong, DeLong & Clarke-Pearson 1988[^delong1988].
- An operating point \(\Rightarrow\) sensitivity, specificity, PPV, NPV. PPV/NPV need prevalence; AUC does not.

**Threshold rules are not unique:**

| Rule | What it optimises |
|---|---|
| Closest to \((0,1)\) in ROC space | Euclidean geometry on the unit square |
| Youden \(J=\mathrm{sens}+\mathrm{spec}-1\) | Youden 1950[^youden1950] |
| MATLAB `perfcurve` `optrocpt` | Toolbox default — **not** always either of the above |
| A clinically chosen TPR | e.g. “we will not miss more than 10% of HS” |

AUC can match to \(10^{-15}\) while sensitivity/specificity differ. If a MATLAB table used `pos_label=0` for patients, sklearn `pos_label=1` maps \(\mathrm{AUC}\mapsto 1-\mathrm{AUC}\). That is a **codebook** issue. Do not change `strengths_und` to chase it. See [Asymmetry](asymmetry.md#roc-sensitivity-specificity).

## Normative models (Piper design)

Piper et al. 2026 residualise each nucleus’s strength in **controls** with a general linear model of age, sex, motion, and global brain strength, then z-score patients against the control residual SD[^piper2026]. Volumes use age, sex, and intracranial volume.

This package implements that design with **OLS** (`numpy.linalg.lstsq` in `nodestrength.normative`):

\[
y = X\beta + \varepsilon, \qquad \hat\beta = (X^\top X)^{+} X^\top y, \qquad z = \frac{y-X\hat\beta}{\hat\sigma}
\]

where \(X\) has an intercept, continuous covariates as-is, and categorical covariates one-hot with `drop_first=True`. Residual SD uses \(\mathrm{ddof}=p\). Fits are **per (nucleus, side)** so right-sided patients are z-scored against right-sided control residuals.

The broader **normative modelling** literature (Marquand et al. 2016, 2019[^marquand2016]; GAMLSS) writes the same idea as a conditional distribution of the response given covariates \(x\):

\[
y \mid x \sim f\bigl(\hat{\mu}(x),\; \hat{\sigma}(x),\; \ldots\bigr)
\]

Here \(\hat{\mu}(x)\) is the estimated mean (or location) at age/sex/motion/global strength, \(\hat{\sigma}(x)\) is an optional scale function, and \(f\) is a named family (Gaussian for OLS; more flexible in GAMLSS). A patient z-score is then \((y-\hat{\mu}(x))/\hat{\sigma}(x)\). Piper’s GLM is the Gaussian, homoscedastic case: \(\hat{\sigma}\) does not depend on \(x\), and \(\hat{\mu}(x)=x^\top\hat\beta\).

A **penalised spline GAM** (`pygam`, `mgcv`) is a different estimator for \(\mu(x)\). If you need splines, fit them outside this CLI and say so. Bayesian linear models in large biobanks are another option in that same family.

`nodestrength fit-normative --controls controls.csv --out model.pkl` pickles the OLS fits. `dkt-ai-cohort --participants` can fit from the control rows (`--control-group`) or load `--normative-model`.

## Mixed-design GLM / MANOVA

Piper reports **Pillai’s trace** and **partial η²** for within-subject factors (nucleus, side) and between-subject factors (group, SOZ, outcome) — the SPSS `GLM` multivariate repeated-measures convention.

`nodestrength.stats` implements the wide multivariate form (Rencher, *Methods of Multivariate Analysis*; Bakeman 2005 for multivariate partial η² \(= V/s\)):

- Outcome matrix \(Y\) has one column per within-cell (e.g. 4 nuclei × 2 sides).
- Between-subject design \(X\).
- Hypothesis \(LB M = 0\) with \(L\) picking between-effects and \(M\) an orthonormal within-contrast.
- Hypothesis and error SSP matrices \(H\), \(S\); Pillai \(V=\mathrm{tr}(H(H+S)^{-1})\); \(F\) approximation; partial η².

These will **not** bit-match SAS `PROC GLM` in the 7th decimal. Reproduce the *design*, not the binary of a floating-point trace.

Permutation analogue: PALM (Winkler et al. 2014)[^winkler2014]; Freedman–Lane. Use those if exchangeability is clearer than Pillai’s \(F\).

CLI:

```bash
nodestrength analyze --cohort long.csv \
    --within nucleus side --between group \
    --value strength --out glm.csv
```

## Multiple comparisons

- Few planned hippocampal tests (left-HS vs control on hippocampal AI at one scale, one weight): report the raw p, AUC, and effect size. Bonferroni on four planned tests is fine.
- Whole-atlas strength maps (84 or 462 nodes): FDR (Benjamini–Hochberg 1995) or a permutation max-statistic. Do not treat neighbouring parcels as independent.
- **Do not** treat 4 scales × 5 weights × 2 reconstructions as independent discoveries of the same hippocampus. Pre-register the primary (\(W\), scale) pair; the rest are sensitivity analyses.
- Edgewise maps: NBS, not Bonferroni on \(n(n-1)/2\) edges.

Button et al. (2013) on power in neuroscience: a Cohen’s \(d\) of 0.3 on \(n=20\) vs \(n=20\) is mostly noise. 288 subjects helps; 50 uncorrected BCT metrics undoes that help.

## What is **not** a maths change

Reimplementing `strengths_und` and AI in Python, with the same LUT order and the same \(W\), should match MATLAB/BCT to \(\sim 10^{-15}\). If it does, **nobody changed the formula**. Remaining disagreements are:

1. Different \(W\) (det vs prob, SIFT, Count vs FA)
2. Different LUT order (GraphML vs FreeSurfer LUT)
3. Different intrahemispheric mask
4. Different ROC operating point / `pos_label`
5. GAM vs OLS
6. Missing subjects (NaN `isControl` on rows without a connectome)
7. SPSS vs NumPy Pillai

Those are **data and estimator** issues. The IDEAS replication trail in this project’s research notes is exactly that list: bitwise-identical AI when \(W\) and LUT match; different AUC when true deterministic Count replaces a copied probabilistic matrix; different sens/spec when `optrocpt` is not closest-to-(0,1).

[^delong1988]: DeLong ER, DeLong DM, Clarke-Pearson DL. Comparing the areas under two or more correlated ROC curves. *Biometrics*. 1988;44:837–845.
[^youden1950]: Youden WJ. Index for rating diagnostic tests. *Cancer*. 1950;3:32–35.
[^piper2026]: Piper RJ et al. *Epilepsia*. 2026;67:1901–1915.
[^marquand2016]: Marquand AF et al. Understanding heterogeneity in clinical cohorts using normative models. *Biol Psychiatry*. 2016;80:552–561.
[^winkler2014]: Winkler AM et al. *NeuroImage*. 2014;92:381–397.
