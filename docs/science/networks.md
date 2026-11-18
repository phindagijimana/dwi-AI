# Why represent the brain as a network?

The short answer: because we want a language for **parts**, **connections**, and **the pattern of those connections**, not only for the size or intensity of a single region.

In network neuroscience a **node** is a parcel of grey matter (or a neuron, or a voxel). An **edge** is a measured relationship — streamlines of white matter, a statistical dependence in BOLD, a synaptic count. The object of study is the graph \(G = (V, E)\), possibly weighted. Reviews that set this agenda include Bullmore & Sporns (2009)[^bullmore2009], Rubinov & Sporns (2010)[^rubinov2010], Fornito, Zalesky & Bullmore’s textbook (2016)[^fornito2016], and Bassett & Sporns (2017)[^bassett2017].

## Three questions the graph is for

1. **Integration.** Can this region talk to the rest of the brain? That is **degree / strength**, the quantity `nodestrength` computes.
2. **Segregation.** Are there clusters that are densely wired internally? Clustering, modularity, communities.
3. **Layout.** Is the wiring economical, small-world, core–periphery, hierarchical? Watts–Strogatz (1998)[^watts1998], Barabási–Albert (1999)[^barabasi1999], Bassett & Bullmore (2017)[^bassett2017smallworld].

A hippocampal **node strength** study is almost entirely question 1, plus laterality. It is still “graph theory” in the same way that measuring blood pressure is still cardiovascular physiology — a real but thin slice of the field.

## Structural vs functional vs effective connectivity

| Kind | Typical measurement | Edge meaning | Canonical refs |
|---|---|---|---|
| Structural | dMRI tractography, tracers | Anatomical pathway | Hagmann et al. 2008[^hagmann2008]; Sporns, Tononi & Kötter 2005[^sporns2005] |
| Functional | fMRI, EEG, MEG correlations | Statistical dependence | Friston 2011[^friston2011]; Biswal et al. 1995[^biswal1995] |
| Effective | DCM, Granger, perturb-and-measure | Directed causal influence | Friston 2011[^friston2011] |

`nodestrength` is **structural**. Do not treat a Count matrix as if it were a correlation matrix: the null models, the meaning of a “zero”, and the statistics all differ (Zalesky, Fornito & Bullmore 2010 on resolution[^zalesky2010]; Fornito, Zalesky & Breakspear 2013 on graph-analysis pitfalls[^fornito2013]).

## Why parcellate?

Voxel graphs are huge and noisy. Atlases (Desikan–Killiany[^desikan2006], Destrieux, AAL, Schaefer, Lausanne/Cammoun[^cammoun2012], Glasser MMP) trade spatial detail for stable nodes. **Changing the atlas changes the graph** (Zalesky 2010[^zalesky2010]; de Reus & van den Heuvel 2013[^dereus2013]). Always name the atlas, the scale, and the row order (LUT).

## A reading order for newcomers

1. Sporns — *Networks of the Brain* (2011) or the 2005 “human connectome” paper[^sporns2005]
2. Bullmore & Sporns 2009 review[^bullmore2009]
3. Rubinov & Sporns 2010 (BCT measures, including strength)[^rubinov2010]
4. Fornito et al. 2016 textbook, chapters 1–3, 7–8[^fornito2016]
5. Then the dMRI-specific stack: Jeurissen 2014, Smith ACT/SIFT2, Yeh 2021 “limitations of tractography”[^yeh2021]

The rest of this section walks those ideas at the level needed to use this software honestly.

[^bullmore2009]: Bullmore E, Sporns O. Complex brain networks: graph theoretical analysis of structural and functional systems. *Nat Rev Neurosci*. 2009;10:186–198. [doi:10.1038/nrn2575](https://doi.org/10.1038/nrn2575)
[^rubinov2010]: Rubinov M, Sporns O. Complex network measures of brain connectivity: uses and interpretations. *NeuroImage*. 2010;52:1059–1069. [doi:10.1016/j.neuroimage.2009.10.003](https://doi.org/10.1016/j.neuroimage.2009.10.003)
[^fornito2016]: Fornito A, Zalesky A, Bullmore ET. *Fundamentals of Brain Network Analysis*. Academic Press; 2016.
[^bassett2017]: Bassett DS, Sporns O. Network neuroscience. *Nat Neurosci*. 2017;20:353–364. [doi:10.1038/nn.4502](https://doi.org/10.1038/nn.4502)
[^watts1998]: Watts DJ, Strogatz SH. Collective dynamics of ‘small-world’ networks. *Nature*. 1998;393:440–442.
[^barabasi1999]: Barabási A-L, Albert R. Emergence of scaling in random networks. *Science*. 1999;286:509–512.
[^bassett2017smallworld]: Bassett DS, Bullmore ET. Small-world brain networks revisited. *Neuroscientist*. 2017;23:499–516.
[^hagmann2008]: Hagmann P et al. Mapping the structural core of human cerebral cortex. *PLoS Biol*. 2008;6:e159.
[^sporns2005]: Sporns O, Tononi G, Kötter R. The human connectome: a structural description of the human brain. *PLoS Comput Biol*. 2005;1:e42.
[^friston2011]: Friston KJ. Functional and effective connectivity: a review. *Brain Connect*. 2011;1:13–36.
[^biswal1995]: Biswal B et al. Functional connectivity in the motor cortex of resting human brain using echo-planar MRI. *Magn Reson Med*. 1995;34:537–541.
[^zalesky2010]: Zalesky A et al. Whole-brain anatomical networks: does the choice of nodes matter? *NeuroImage*. 2010;50:970–983.
[^fornito2013]: Fornito A, Zalesky A, Breakspear M. Graph analysis of the human connectome: promise, progress, and pitfalls. *NeuroImage*. 2013;80:426–444.
[^desikan2006]: Desikan RS et al. An automated labeling system for subdividing the human cerebral cortex on MRI scans into gyral based regions of interest. *NeuroImage*. 2006;31:968–980.
[^cammoun2012]: Cammoun L et al. Mapping the human connectome at multiple scales with diffusion spectrum MRI. *J Neurosci Methods*. 2012;203:386–397.
[^dereus2013]: de Reus MA, van den Heuvel MP. The parcellation-based connectome: limitations and extensions. *NeuroImage*. 2013;80:397–404.
[^yeh2021]: Yeh C-H et al. Mapping structural connectivity using diffusion MRI: challenges and opportunities. *J Magn Reson Imaging*. 2021;53:1666–1682.
