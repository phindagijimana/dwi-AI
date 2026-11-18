# Other methods in connectomics

Node strength is one local summary of one kind of matrix. The field is larger. This page is a map of **neighbouring methods** you will see in papers, and whether this repository implements them (it mostly does not).

## Edge-level inference

**Network-based statistic (NBS)** — Zalesky, Fornito & Bullmore 2010[^zalesky2010nbs]. Permute group labels, threshold edges, look at the size of connected components of supra-threshold edges. Controls family-wise error at the *component* level. Use when the hypothesis is “some *connections* differ,” not “this *node’s total wiring* differs.”

**Threshold-free network-based statistics**, **FDR on edges**, **connectome-based predictive modelling (CPM)** (Shen et al. 2017[^shen2017]) — regression/classification from selected edges.

**Multivariate distance matrix regression (MDMR)** and **graphical lasso** precision matrices — common in fMRI.

## Bundle- and voxel-level white matter

Not connectomes, but often more anatomically specific:

| Method | What it is | Refs |
|---|---|---|
| Tractometry / AFQ | FA/MD along a named bundle | Yeatman 2012[^yeatman2012] |
| TractSeg / TractSeg2 | CNN bundle segmentation | Wasserthal 2018 |
| Fixel-based analysis (FBA) | Fibre-bundle element FD/FC/FDC | Raffelt 2015, 2017[^raffelt2017] |
| TBSS | Skeletonised FA voxelwise | Smith 2006[^smith2006tbss] |
| Apparent fibre density | CSD-based intra-axonal density | Raffelt 2012 |

Piper-style **node strength** collapses all bundles touching a parcel into one number. FBA/AFQ keep the bundle.

## Microstructure-informed tractography

SIFT/SIFT2[^smith2015], COMMIT[^daducci2015], LiFE (Pestilli 2014), Convex Optimization / global tractography (Reisert 2011; Christiaens 2015). These change \(W\) *before* strength. If two labs disagree on hippocampal AI, ask whether SIFT2 was on.

## Functional and effective connectivity

- Pearson / partial correlation, tangent-space embedding (Varoquaux)
- ICA / canonical ICA (Calhoun; Smith)
- DCM (Friston 2003, 2011[^friston2011])
- Granger causality (with strong caveats in fMRI)
- MEG/EEG amplitude-envelope coupling (Hipp 2012)

Graph metrics can be computed on those matrices; the biology is different.

## Multi-layer, temporal, and morphometric networks

- **Multilayer / multiplex** — structural + functional layers (Battiston; Vaiana & Muldoon)
- **Dynamic FC** — sliding windows (Lurie 2020 review; warnings by Laumann / Noble)
- **Morphometric similarity networks** — Seidlitz et al. 2018[^seidlitz2018]
- **Covariance of cortical thickness** — Mechelli; Alexander-Bloch
- **Structural covariance** vs true axons — interpret with care

## Machine learning on connectomes

- BrainNetCNN, graph neural nets on \(W\) (Kawahara 2017; later GNN reviews)
- Kernel two-sample tests on graphs
- Harmonisation (ComBat for connectivity; Fortin / Pomponio)

`nodestrength` stops at features (strength, AI, z). It does not train a classifier beyond optional ROC on a single AI column.

## Spatial statistics on the surface

GLM on thickness/myelination (FreeSurfer; Human Connectome Project pipelines), PALM permutation inference (Winkler 2014[^winkler2014]). Complementary to graphs: a hippocampal volume effect and a hippocampal strength effect can coexist.

## What to pick

| Scientific question | Method |
|---|---|
| Is this region under-connected in total? | **Node strength** (this tool) |
| Which specific projections differ? | NBS / edgewise / bundle tractometry |
| Crossing-fibre density in a voxel? | FBA |
| Is the *organisation* (modules, paths) different? | Clustering, efficiency, modularity + nulls |
| Can the matrix predict a score? | CPM / GNN |
| Is the *lesion side* the weak side? | AI + ROC ([Asymmetry](asymmetry.md)) |

[^zalesky2010nbs]: Zalesky A, Fornito A, Bullmore ET. Network-based statistic: identifying differences in brain networks. *NeuroImage*. 2010;53:1197–1207.
[^shen2017]: Shen X et al. Using connectome-based predictive modeling to predict individual behavior from brain connectivity. *Nat Protoc*. 2017;12:506–518.
[^yeatman2012]: Yeatman JD et al. Tract profiles of white matter properties: automating fiber-tract quantification. *PLoS One*. 2012;7:e49790.
[^raffelt2017]: Raffelt DA et al. Investigating white matter fibre density and morphology using fixel-based analysis. *NeuroImage*. 2017;144:58–73.
[^smith2006tbss]: Smith SM et al. Tract-based spatial statistics: voxelwise analysis of multi-subject diffusion data. *NeuroImage*. 2006;31:1487–1505.
[^smith2015]: Smith RE et al. *NeuroImage*. 2015;119:338–351.
[^daducci2015]: Daducci A et al. *IEEE TMI*. 2015;34:246–261.
[^friston2011]: Friston KJ. *Brain Connect*. 2011;1:13–36.
[^seidlitz2018]: Seidlitz J et al. Morphometric similarity networks detect microscale cortical organization and predict inter-individual cognitive variation. *Neuron*. 2018;97:231–247.
[^winkler2014]: Winkler AM et al. Permutation inference for the general linear model. *NeuroImage*. 2014;92:381–397.
