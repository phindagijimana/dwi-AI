# Statistics this project actually runs

Graph theory stops when \(s_i\) and AI exist. The rest is ordinary biomedical statistics. Mixing the two layers is how papers become unreproducible.

## Per-subject features

- Node strength, optionally intrahemispheric
- Side AI, SOZ-aligned AI, log-ratio
- Optional volume and volume AI
- Optional global strength (sum of \(s_i / 2\) for undirected graphs)

## ROC for a single biomarker

Given AI (or hippocampal volume) and a binary label (e.g. left HS vs control):

- ROC curve and AUC (Hanley & McNeil 1982; DeLong 1988 for correlated AUCs[^delong1988])
- An operating point → sensitivity, specificity, PPV/NPV

MATLAB `perfcurve` with `pos_label` and `optrocpt` is **not** the same helper as `sklearn.metrics.roc_curve` plus Euclidean distance to \((0,1)\). AUC can match to machine precision while sens/spec differ. If you need MATLAB’s operating point, call MATLAB; do not “fix” AI.

Inverting the positive class maps \(\mathrm{AUC} \mapsto 1-\mathrm{AUC}\). Left-HS studies sometimes code the patient class as `0`. Check the codebook.

## Normative models (Piper)

Piper et al. 2026 residualise strength in controls with a GAM of age, sex, motion, and global brain strength, then z-score patients against that residual SD[^piper2026].

This package implements the covariates with **OLS** (`numpy.linalg.lstsq` in `nodestrength.normative`), not `pygam`. Piper et al. describe a GLM/GAM-style residualisation; a true spline GAM is a different estimator. If you need penalised splines, fit them outside this CLI and say so in the paper.

Related literature: Marquand et al. 2016, 2019 normative modelling[^marquand2016]; GAMLSS; Bayesian linear regression as in some UK Biobank pipelines.

## Mixed-design GLM / MANOVA

Within-subject factors: nucleus, side.  
Between-subject: group, SOZ, outcome.

Piper reports Pillai’s trace and partial η². `nodestrength.stats` implements the wide multivariate form used by SPSS GLM (Rencher; Bakeman 2005 for partial η² \(= V/s\)). These will not bit-match SAS `PROC GLM` in the 7th decimal. The *design* is the thing to reproduce.

Permutation analogues: PALM (Winkler 2014)[^winkler2014]; Freedman–Lane.

## Multiple comparisons

- Few planned hippocampal tests: report raw p and effect sizes.
- Whole-atlas strength maps: FDR (Benjamini–Hochberg) or NBS if you switch to edges.
- Do not treat 4 scales × 5 weights × 2 reconstructions as independent discoveries of the same hippocampus.

## What is **not** a maths change

Reimplementing `strengths_und` and AI in Python, with the same LUT order and the same \(W\), should match MATLAB/BCT to \(\sim 10^{-15}\). If it does, **nobody changed the formula**. Remaining disagreements are:

1. Different \(W\) (det vs prob, SIFT, Count vs FA)
2. Different LUT order
3. Different intrahemispheric mask
4. Different ROC operating point / `pos_label`
5. GAM vs OLS
6. Missing subjects (NaN `isControl`)

Those are **data and estimator** issues. See the project README and research notes in the GitHub repository for the IDEAS replication trail.

[^delong1988]: DeLong ER, DeLong DM, Clarke-Pearson DL. Comparing the areas under two or more correlated ROC curves. *Biometrics*. 1988;44:837–845.
[^piper2026]: Piper RJ et al. *Epilepsia*. 2026;67:1901–1915.
[^marquand2016]: Marquand AF et al. Understanding heterogeneity in clinical cohorts using normative models: beyond group averages. *Biol Psychiatry*. 2016;80:552–561.
[^winkler2014]: Winkler AM et al. *NeuroImage*. 2014;92:381–397.
