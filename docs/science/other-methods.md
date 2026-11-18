# Other methods in connectomics

Node strength is one local summary of one kind of matrix. The field is larger. This page maps **neighbouring methods** you will see in papers, what question each answers, key citations, and whether this repository implements them (almost never).

If your question is “is this region under-connected in total?”, stay on [node strength](strength.md). If your question is any of the rows below, you need a different tool — not a different flag on `dkt-ai-cohort`.

## Edge-level inference on connectomes

### Network-based statistic (NBS)

Zalesky, Fornito & Bullmore (2010)[^zalesky2010nbs]. Procedure:

1. Mass-univariate test on each edge (t-test, GLM).
2. Threshold edges at an uncorrected primary \(t\).
3. Find connected components of supra-threshold edges.
4. Permute group labels; the null is the *size* (or intensity) of the largest component.

Family-wise error is controlled at the **component** level, not the edge level. Use when the hypothesis is “some *connections* differ,” not “this *node’s total wiring* differs.” Strength can be significant while NBS is not (a distributed weak degree effect) and vice versa (a focal bundle).

Related: TFNBS (Baggio), MFC / “threshold-free” variants, FDR on edges (more conservative, no spatial clustering).

### Connectome-based predictive modelling (CPM)

Shen et al. (2017)[^shen2017]: correlate every edge with a behaviour, keep positively/negatively associated edges, sum them, fit a linear model, cross-validate. A prediction method, not a graph-theory method. Requires honest cross-validation (no leaking the edge mask).

### MDMR, graphical lasso, tangent space

**Multivariate distance matrix regression** (McArtor / Shehzad-style neuroimaging uses): is the *pattern* of connectivity different? **Graphical lasso** (Friedman, Hastie & Tibshirani): sparse inverse covariance as an “effective” functional graph. **Tangent-space embedding** of covariance matrices (Varoquaux, Poldrack’s work, Nilearn): the right geometry for classifying functional connectomes. All of this is fMRI-adjacent; do not apply graphical lasso to a streamline Count matrix and call it SIFT.

## Bundle- and voxel-level white matter

These are **not** connectomes. They keep anatomy that node strength throws away.

| Method | Object | What you get | Landmark |
|---|---|---|---|
| DTI voxel maps | FA, MD, RD per voxel | Microstructure, crossings unresolved | Basser 1994 |
| TBSS | FA skeleton | Voxelwise group FA | Smith 2006[^smith2006tbss] |
| Tractometry / AFQ | Named bundle, points along it | FA/MD profile of e.g. uncinate | Yeatman 2012[^yeatman2012] |
| TractSeg | CNN bundle mask | 72+ bundles without a full connectome | Wasserthal 2018 |
| Apparent fibre density | CSD intra-axonal density | Per-direction density | Raffelt 2012 |
| Fixel-based analysis | Fibre-bundle element | FD, FC, FDC at crossings | Raffelt 2015, 2017[^raffelt2017] |

Piper-style **node strength** collapses every bundle that touches a parcel into one number. If the scientific claim is “the fornix is degenerated,” use AFQ/FBA/TractSeg, not `strengths_und` of the hippocampus.

## Microstructure-informed tractography (changing \(W\) before strength)

These methods sit **upstream** of this CLI. They change the numbers in \(W\).

| Method | Idea | Ref |
|---|---|---|
| SIFT | Delete streamlines until FODs are explained | Smith 2013 |
| SIFT2 | Keep streamlines; fit a weight per streamline | Smith 2015[^smith2015] |
| COMMIT | Convex fit of microstructural contributions | Daducci 2015[^daducci2015] |
| LiFE | Linear fascicle evaluation vs a forward model | Pestilli 2014 |
| Global tractography | Jointly fit all tracks | Reisert 2011; Christiaens 2015 |

If two labs disagree on hippocampal AI, the first question is not OLS vs GAM; it is whether SIFT2 was on and whether det vs prob was labelled.

## Functional and effective connectivity

Covered as a trichotomy in [Why graphs](networks.md). Methods you will see:

- **Pearson / partial correlation** of ROI time series (Biswal 1995; Smith 2011).
- **ICA / canonical ICA** (Calhoun; Smith HCP ICA).
- **DCM** (Friston 2003, 2011[^friston2011]) — generative, directed, model comparison with free energy.
- **Granger causality** on fMRI: sampling-rate and haemodynamic caveats are severe.
- **MEG/EEG amplitude-envelope coupling** (Hipp 2012); phase-locking; wPLI.

You *can* compute strength on a correlation matrix. Interpret it as weighted functional degree, cite the functional pipeline, and use an appropriate null (often a correlation-preserving or phase-randomised one, not Maslov–Sneppen on a binary skeleton).

## Multi-layer, temporal, morphometric, covariance

- **Multilayer / multiplex** (Kivelä 2014; Battiston; Vaiana & Muldoon): structural layer + functional layer on the same nodes; intra- and inter-layer edges. Participation across *layers* is a new measure.
- **Dynamic FC**: sliding windows (Hutchison; Calhoun; Lurie 2020 review). Reliability at short windows is poor (Noble; Laumann).
- **Morphometric similarity networks** (Seidlitz et al. 2018[^seidlitz2018]): edges from similarity of multivariate morphology (thickness, myelination, …). Not axons.
- **Structural covariance** of thickness (Mechelli; Alexander-Bloch): group-level correlation of anatomy across subjects. A different object from a single-subject dMRI graph; do not compare \(C\) of a covariance network to \(C\) of a tractogram.

## Machine learning on connectomes

- BrainNetCNN (Kawahara 2017) — edge-to-edge, edge-to-node filters on \(W\).
- Graph neural nets on brain graphs — large, fast-moving review literature; data-hungry; easy to overfit 288 subjects.
- Kernel two-sample tests (MMD) on graphs.
- Harmonisation: ComBat-style empirical Bayes for connectivity (Fortin; Pomponio; neuroCombat). Scanner effects will otherwise look like group effects.

`nodestrength` stops at features (strength, AI, z). The only classifier it supports is optional ROC on a **single** AI column.

## Spatial statistics on the surface (not graphs)

GLM on thickness, myelination, or an AI *map* (FreeSurfer; HCP pipelines). PALM permutation inference (Winkler 2014[^winkler2014]) with exchangeability blocks. A hippocampal **volume** effect and a hippocampal **strength** effect can coexist; they are not two graph metrics, they are two modalities.

## What to pick

| Scientific question | Method | In this repo? |
|---|---|---|
| Is this region under-connected in total? | **Node strength** | Yes |
| Is the SOZ side the weak side? | AI + ROC | Yes |
| Which specific projections differ? | NBS / tractometry | No |
| Crossing-fibre density in a voxel? | FBA | No |
| Is the *organisation* (modules, paths) different? | Clustering, \(E\), \(Q\) + nulls | No — see [Beyond](beyond.md) |
| Can the matrix predict a score? | CPM / GNN | No |
| Is morphology similar across regions? | MSN / covariance | No |

[^zalesky2010nbs]: Zalesky A, Fornito A, Bullmore ET. Network-based statistic: identifying differences in brain networks. *NeuroImage*. 2010;53:1197–1207.
[^shen2017]: Shen X et al. Using connectome-based predictive modeling to predict individual behavior from brain connectivity. *Nat Protoc*. 2017;12:506–518.
[^smith2006tbss]: Smith SM et al. Tract-based spatial statistics. *NeuroImage*. 2006;31:1487–1505.
[^yeatman2012]: Yeatman JD et al. Tract profiles of white matter properties. *PLoS One*. 2012;7:e49790.
[^raffelt2017]: Raffelt DA et al. Investigating white matter fibre density and morphology using fixel-based analysis. *NeuroImage*. 2017;144:58–73.
[^smith2015]: Smith RE et al. SIFT2. *NeuroImage*. 2015;119:338–351.
[^daducci2015]: Daducci A et al. COMMIT. *IEEE TMI*. 2015;34:246–261.
[^friston2011]: Friston KJ. *Brain Connect*. 2011;1:13–36.
[^seidlitz2018]: Seidlitz J et al. Morphometric similarity networks. *Neuron*. 2018;97:231–247.
[^winkler2014]: Winkler AM et al. Permutation inference for the general linear model. *NeuroImage*. 2014;92:381–397.
