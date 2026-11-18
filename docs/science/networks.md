# Why represent the brain as a network?

The short answer: because we want a language for **parts**, **connections**, and **the pattern of those connections**, not only for the size or intensity of a single region.

A mass-univariate voxel test can say “this hippocampus is small.” It cannot say “this hippocampus is weakly wired to ipsilateral temporal cortex, and that wiring pattern is more diagnostic than volume.” Network neuroscience exists for the second sentence.

In this field a **node** is a parcel of grey matter (or a neuron, a voxel, a recording site). An **edge** is a measured relationship — streamlines of white matter, a statistical dependence in BOLD, a synaptic count from tracers or electron microscopy. The object of study is the graph \(G=(V,E)\), often weighted. Agenda-setting reviews: Bullmore & Sporns (2009)[^bullmore2009], Rubinov & Sporns (2010)[^rubinov2010], Fornito, Zalesky & Bullmore (2016)[^fornito2016], Bassett & Sporns (2017)[^bassett2017].

## A short history of the idea

| Year | What happened | Ref |
|---|---|---|
| 19th–20th c. | Golgi, Cajal, the neuron doctrine; the brain is already a network of cells | — |
| 1991– | Macroscopic “connectome” language; Crick & Jones call for a human brain map | Crick & Jones 1993 |
| 2005 | Sporns, Tononi & Kötter name the **human connectome** as a structural description | Sporns 2005[^sporns2005] |
| 2005–2008 | First diffusion-MRI cortical networks | Hagmann 2005, 2008[^hagmann2008]; Iturria-Medina; Gong 2009 |
| 2009 | *Nature Reviews Neuroscience* review makes graph metrics standard vocabulary | Bullmore & Sporns 2009 |
| 2010 | BCT paper: a shared catalogue of measures (including strength) | Rubinov & Sporns 2010 |
| 2010–2013 | HCP; warnings about nodes, density, pitfalls | Van Essen 2013[^vanessen2013]; Zalesky 2010; Fornito 2013 |
| 2017– | “Network neuroscience” as a named field | Bassett & Sporns 2017 |

Microscale connectomics (Lichtman & Sanes 2008; *C. elegans* White et al. 1986; FlyEM, MICrONS) uses the same word at a different scale: synapses, not streamlines. Do not mix those literatures in one methods sentence.

## Three questions the graph is for

1. **Integration.** Can this region talk to the rest of the brain? **Degree / strength** — the quantity `nodestrength` computes — is the first-order answer. Path length and efficiency are higher-order answers (how *indirectly* it talks).
2. **Segregation.** Are there clusters that are densely wired internally and sparsely wired between? Clustering, transitivity, modularity, communities (Meunier, Lambiotte & Bullmore 2010).
3. **Layout / economy.** Is the wiring cheap, small-world, core–periphery, hierarchical? Watts–Strogatz (1998)[^watts1998]; Barabási–Albert (1999)[^barabasi1999] (use critically); Bullmore & Sporns (2012) on the economical brain[^bullmore2012]; Bassett & Bullmore (2017) on small-world brain networks[^bassett2017smallworld]; van den Heuvel & Sporns (2011) on the rich club.

A hippocampal node-strength study is almost entirely question 1, plus laterality. It is still graph theory. It is not “the” graph-theory paper; it does not need to be.

## Structural vs functional vs effective connectivity

Friston (2011)[^friston2011] is the canonical trichotomy.

| Kind | Typical measurement | Edge meaning | What a zero means | Canonical refs |
|---|---|---|---|---|
| **Structural** | dMRI tractography; tracers (CoCoMac, Allen) | Anatomical pathway | “We did not reconstruct a connection” — not “no axons exist” | Hagmann 2008; Sporns 2005; Markov et al. macaque |
| **Functional** | fMRI / EEG / MEG correlations | Statistical dependence | “Time series are uncorrelated *under this model*” | Biswal 1995[^biswal1995]; Smith 2011 |
| **Effective** | DCM, some Granger, perturb-and-measure | Directed causal influence | Model-dependent | Friston 2003, 2011 |

`nodestrength` is **structural**. Do not treat a Count matrix as if it were a Pearson matrix: the null models, the meaning of a zero, the role of negative weights, and the statistics all differ (Zalesky 2010 on node choice[^zalesky2010]; Fornito, Zalesky & Breakspear 2013 on pitfalls[^fornito2013]). Running `strengths_und` on Fisher-z functional connectivity is mathematically defined and biologically a different construct — call it “weighted functional degree,” not “streamline strength.”

## Why parcellate?

A voxel-wise white-matter graph has \(\sim 10^5\)–\(10^6\) nodes and is dominated by noise and spatial autocorrelation. Atlases trade spatial detail for stable, named nodes:

- **Desikan–Killiany** (Desikan 2006)[^desikan2006] — gyral, ~34 cortical regions per hemisphere; this package’s `fs_default` / DKT path.
- **Destrieux** — finer gyral/sulcal.
- **AAL** (Tzourio-Mazoyer 2002) — still common, not recommended as a first choice.
- **Lausanne / Cammoun 2012**[^cammoun2012] — recursive splits of DK; scales ~36/60/125/250. IDEAS connectomes in this project.
- **Schaefer 2018** — gradient-informed functional parcels at 100–1000 nodes.
- **Glasser MMP 2016** — multi-modal HCP parcels (360 cortical).
- **Brainnetome** (Fan 2016) — structural–functional hybrid, includes subcortical.

**Changing the atlas changes the graph** (Zalesky et al. 2010[^zalesky2010]; de Reus & van den Heuvel 2013[^dereus2013]). There is no such thing as “the” clustering coefficient of a subject — only \(C\) for a named atlas, scale, threshold, and weight. Always report:

1. Atlas name and version
2. Scale / node count
3. **Row order (LUT)** — matching \(n\) is not matching order
4. Whether brainstem / white-matter / cerebellum nodes were dropped

Lausanne 2008 hippocampus is **one node per hemisphere at every scale**. Finer scales split neocortex, not the hippocampus. That fact matters for IDEAS hippocampal AI.

## The brain as an economical network

Wiring costs energy and volume. Bullmore & Sporns (2012)[^bullmore2012] review the tension between **cost** (prefer short fibres) and **topological value** (a few long fibres, a rich club, to keep paths short). Generative models that grow edges from spatial distance plus homophily can reproduce many connectome statistics (Betzel et al. 2016; Vértes et al. 2012 for functional graphs). If your “clustering” is exactly what a distance-preserving null predicts, you have rediscovered that nearby cortex is more often connected — anatomy, not a new organisation.

## What a newcomer should read first

1. Sporns, Tononi & Kötter 2005 — the connectome as a project[^sporns2005]
2. Bullmore & Sporns 2009 — the review[^bullmore2009]
3. Rubinov & Sporns 2010 — the measures, including strength[^rubinov2010]
4. Fornito, Zalesky & Bullmore 2016, chapters 1–3 and 7–8[^fornito2016]
5. Fornito, Zalesky & Breakspear 2013 — what goes wrong[^fornito2013]
6. Then dMRI: Jones, Knösche & Turner 2013; Jeurissen 2014; Smith SIFT2; Yeh 2021[^yeh2021]

Then this site: [Graph theory primer](graphs.md) → [Connectomics](connectomics.md) → [Node strength](strength.md).

[^bullmore2009]: Bullmore E, Sporns O. Complex brain networks: graph theoretical analysis of structural and functional systems. *Nat Rev Neurosci*. 2009;10:186–198. [doi:10.1038/nrn2575](https://doi.org/10.1038/nrn2575)
[^rubinov2010]: Rubinov M, Sporns O. Complex network measures of brain connectivity: uses and interpretations. *NeuroImage*. 2010;52:1059–1069. [doi:10.1016/j.neuroimage.2009.10.003](https://doi.org/10.1016/j.neuroimage.2009.10.003)
[^fornito2016]: Fornito A, Zalesky A, Bullmore ET. *Fundamentals of Brain Network Analysis*. Academic Press; 2016.
[^bassett2017]: Bassett DS, Sporns O. Network neuroscience. *Nat Neurosci*. 2017;20:353–364. [doi:10.1038/nn.4502](https://doi.org/10.1038/nn.4502)
[^sporns2005]: Sporns O, Tononi G, Kötter R. The human connectome: a structural description of the human brain. *PLoS Comput Biol*. 2005;1:e42.
[^hagmann2008]: Hagmann P et al. Mapping the structural core of human cerebral cortex. *PLoS Biol*. 2008;6:e159.
[^vanessen2013]: Van Essen DC et al. The WU-Minn Human Connectome Project. *NeuroImage*. 2013;80:62–79.
[^watts1998]: Watts DJ, Strogatz SH. Collective dynamics of ‘small-world’ networks. *Nature*. 1998;393:440–442.
[^barabasi1999]: Barabási A-L, Albert R. Emergence of scaling in random networks. *Science*. 1999;286:509–512.
[^bullmore2012]: Bullmore E, Sporns O. The economy of brain network organization. *Nat Rev Neurosci*. 2012;13:336–349.
[^bassett2017smallworld]: Bassett DS, Bullmore ET. Small-world brain networks revisited. *Neuroscientist*. 2017;23:499–516.
[^friston2011]: Friston KJ. Functional and effective connectivity: a review. *Brain Connect*. 2011;1:13–36.
[^biswal1995]: Biswal B et al. Functional connectivity in the motor cortex of resting human brain using echo-planar MRI. *Magn Reson Med*. 1995;34:537–541.
[^zalesky2010]: Zalesky A et al. Whole-brain anatomical networks: does the choice of nodes matter? *NeuroImage*. 2010;50:970–983.
[^fornito2013]: Fornito A, Zalesky A, Breakspear M. Graph analysis of the human connectome: promise, progress, and pitfalls. *NeuroImage*. 2013;80:426–444.
[^desikan2006]: Desikan RS et al. An automated labeling system for subdividing the human cerebral cortex on MRI scans into gyral based regions of interest. *NeuroImage*. 2006;31:968–980.
[^cammoun2012]: Cammoun L et al. Mapping the human connectome at multiple scales with diffusion spectrum MRI. *J Neurosci Methods*. 2012;203:386–397.
[^dereus2013]: de Reus MA, van den Heuvel MP. The parcellation-based connectome: limitations and extensions. *NeuroImage*. 2013;80:397–404.
[^yeh2021]: Yeh C-H et al. Mapping structural connectivity using diffusion MRI: challenges and opportunities. *J Magn Reson Imaging*. 2021;53:1666–1682.
