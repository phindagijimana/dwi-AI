# Literature guide

A reading path, not a dump. Papers are grouped so someone new to **networks → connectomics → graph theory in neuroscience → this tool** can walk it in order. Full bibliographic entries: [References](../references.md). Software citation: [Citing](../citing.md).

Each section below says **what you should be able to explain after reading it**, then lists the papers. The Science pages of this site are the notes; the papers are the sources.

## 1. What is a connectome?

After this block you should be able to say what “connectome” means at micro vs macro scale, and why Hagmann 2008 is the structural-MRI ancestor of the matrices this tool scores.

| Paper | Why read it |
|---|---|
| Sporns, Tononi & Kötter 2005, *PLoS Comput Biol* | Named the human connectome as a structural description |
| Crick & Jones 1993, *Nature* | Early call to map human brain connections |
| Hagmann et al. 2008, *PLoS Biol* | Diffusion network of cortex; structural core |
| Gong et al. 2009, *Cereb Cortex* | DTI tractography networks of cortex |
| Bullmore & Sporns 2009, *Nat Rev Neurosci* | The review everyone cites |
| Van Essen et al. 2013, *NeuroImage* | HCP: how modern multi-modal data are organised |
| Lichtman & Sanes 2008 | Microscale / EM connectomics (different scale, same word) |
| White et al. 1986, *Phil Trans B* | *C. elegans* synaptic connectome — the existence proof |

Site: [Why graphs for the brain](networks.md).

## 2. Graph theory without tears

After this block you should be able to define graph, degree, strength, path, clustering, modularity \(Q\), small-world \(\sigma\)/\(\omega\), and say why a null model is required.

| Paper / book | Why |
|---|---|
| Euler 1736 | Königsberg — the first graph paper |
| Watts & Strogatz 1998, *Nature* | Small-world |
| Barabási & Albert 1999, *Science* | Scale-free (use with Clauset / Broido) |
| Newman 2003 review, *SIAM Rev* | Structure of complex networks |
| Newman 2010, *Networks* | Textbook |
| Barrat et al. 2004, *PNAS* | Weighted networks; **strength** |
| Opsahl, Agneessens & Skvoretz 2010 | Tunable degree–strength centrality |
| Latora & Marchiori 2001, *PRL* | Efficiency |
| Newman & Girvan 2004; Newman 2006 | Modularity |
| Blondel et al. 2008 | Louvain |
| Traag, Waltman & van Eck 2019 | Leiden |
| Fortunato & Barthélemy 2007 | Resolution limit of \(Q\) |
| Freeman 1977 | Betweenness |
| Guimerà & Amaral 2005 | Participation / cartography |
| Maslov & Sneppen 2002 | Degree-preserving rewiring |
| Clauset, Shalizi & Newman 2009 | How to test power laws |
| Broido & Clauset 2019 | Scale-free networks are rare |
| Milo et al. 2002 | Motifs |
| Colizza et al. 2006 | Rich club (general) |

Site: [Graph theory primer](graphs.md) (full formulas).

## 3. Network neuroscience catalogues

After this block you should be able to open BCT, find `strengths_und`, and know which metrics are confounded by density and parcellation.

| Paper / book | Why |
|---|---|
| Rubinov & Sporns 2010, *NeuroImage* | **BCT.** Definitions of strength and almost every other metric |
| Fornito, Zalesky & Bullmore 2016 | Best textbook for this audience |
| Fornito, Zalesky & Breakspear 2013, *NeuroImage* | Pitfalls |
| Bassett & Sporns 2017, *Nat Neurosci* | Field manifesto |
| Bullmore & Sporns 2012, *Nat Rev Neurosci* | Economy of brain networks |
| van den Heuvel & Sporns 2011 / 2013 | Rich club; hubs |
| Sporns, Honey & Kötter 2007 | Hub classification |
| Bassett & Bullmore 2006, 2017 | Small-world brain networks (and the revisit) |
| Humphries & Gurney 2008; Telesford 2011 | \(\sigma\) and \(\omega\) |
| Meunier, Lambiotte & Bullmore 2010 | Modules |
| Sporns & Betzel 2016 | Modular brain networks |
| Zalesky et al. 2010 *NeuroImage* (nodes) | Parcellation changes the graph |
| van Wijk, Stam & Daffertshofer 2010 | Density and size confounds |
| de Reus & van den Heuvel 2013 | Parcellation-based connectome limits |
| Betzel et al. 2016 | Generative models of the connectome |
| Stam et al. 2014 | Minimum spanning trees |
| Atasoy et al. 2016 | Connectome harmonics |
| Battiston et al. 2020, *Phys Rep* | Beyond pairwise interactions |

Site: [Beyond this tool](beyond.md).

## 4. Diffusion MRI and tractography (how \(W\) is born)

After this block you should be able to explain MSMT-CSD, ACT, SIFT2, det vs prob, and why streamline count is not axon count.

| Paper | Why |
|---|---|
| Basser, Mattiello & LeBihan 1994 | DTI |
| Tournier, Calamante & Connelly 2007 | CSD |
| Jeurissen et al. 2014 | MSMT-CSD |
| Tournier et al. 2019, *NeuroImage* | MRtrix3 |
| Smith et al. 2012 | ACT |
| Smith et al. 2013 / 2015 | SIFT / SIFT2 |
| Daducci et al. 2015 | COMMIT |
| Pestilli et al. 2014 | LiFE |
| Cieslak et al. 2021, *Nat Methods* | QSIPrep |
| Jones, Knösche & Turner 2013 | “Fiber count and other fallacies” |
| Thomas et al. 2014, *PNAS* | Anatomical accuracy is limited |
| Maier-Hein et al. 2017, *Nat Commun* | International tractography challenge |
| Schilling et al. 2019 | Modern methods still limited |
| Yeh et al. 2021 | Challenges and opportunities review |
| Cammoun et al. 2012 | Lausanne 2008 scales |
| Desikan et al. 2006 | DK atlas |
| Glasser et al. 2016 | HCP MMP |
| Schaefer et al. 2018 | Functional parcels often co-opted for structure |

Site: [Connectomics](connectomics.md).

## 5. Functional connectivity (contrast class)

After this block you should be able to explain why a correlation matrix is not a tractogram, and what NBS is for.

| Paper | Why |
|---|---|
| Biswal et al. 1995 | Resting-state FC |
| Friston 2011 | Functional vs effective |
| Friston et al. 2003 | DCM |
| Smith et al. 2011 | Network modelling for fMRI |
| Power et al. 2012 | Motion artefact |
| Zalesky, Fornito & Bullmore 2010 | **NBS** |
| Shen et al. 2017 | CPM |
| Hipp et al. 2012 | MEG envelope coupling |

Site: [Other methods](other-methods.md).

## 6. Laterality, epilepsy, hippocampus, thalamus

After this block you should be able to write the AI formula, say what SOZ-aligned AI asks, and cite the methods paper this software implements.

| Paper | Why |
|---|---|
| Toga & Thompson 2003 | Mapping brain asymmetry |
| Geschwind & Galaburda 1985 | Classical laterality |
| Kong et al. 2018, *PNAS* | ENIGMA cortical laterality |
| Spencer 2002; Richardson 2012 | Epilepsy as a network disorder |
| Bernhardt, Bonilha & Gross 2015, *Epilepsia* | Connectomics in epilepsy |
| Tavakol et al. 2019 | Network models of focal epilepsy |
| **Piper et al. 2026, *Epilepsia*** | **This software’s methods paper** (thalamocortical strength) |
| Su et al. THOMAS | Thalamic nuclei atlas |
| Youden 1950; DeLong 1988 | Operating point and comparing AUCs |

Site: [Asymmetry](asymmetry.md), [Statistics](statistics.md).

## 7. Methods this CLI does not run (but the literature does)

| Paper | Topic |
|---|---|
| Zalesky 2010 NBS | Edgewise component inference |
| Shen et al. 2017 | Connectome-based predictive modelling |
| Raffelt et al. 2017 | Fixel-based analysis |
| Smith et al. 2006 | TBSS |
| Yeatman et al. 2012 | AFQ tractometry |
| Wasserthal et al. 2018 | TractSeg |
| Seidlitz et al. 2018 | Morphometric similarity networks |
| Marquand et al. 2016 | Normative models |
| Winkler et al. 2014 | PALM permutation inference |
| Kawahara et al. 2017 | BrainNetCNN |

Site: [Other methods](other-methods.md), [Beyond](beyond.md).

## 8. How to cite work that used this stack

Minimum set for a paper that ran QSIPrep → MRtrix/QSIRecon → `nodestrength`:

1. Cieslak et al. 2021 (if QSIPrep)
2. Tournier et al. 2019 (MRtrix3)
3. Smith et al. 2015 (if SIFT2)
4. Atlas paper (Desikan 2006 or Cammoun 2012 or THOMAS)
5. Rubinov & Sporns 2010 (strength)
6. Piper et al. 2026 (analysis design)
7. **Ndagijimana P. (2026).** *nodestrength* [computer software]. [github.com/phindagijimana/dwi-AI](https://github.com/phindagijimana/dwi-AI). Contact: [phindagijimana@gmail.com](mailto:phindagijimana@gmail.com). See [Citing](../citing.md).

## 9. Suggested reading plan

**Week 1 — networks.** Sporns 2005; Bullmore & Sporns 2009; this site’s [Networks](networks.md) and [Graphs](graphs.md) (whole page, including nulls and spectral).  
**Week 2 — BCT.** Rubinov & Sporns 2010 with BCT open; Barrat 2004; Fornito textbook ch. 1–4; [Beyond](beyond.md).  
**Week 3 — dMRI.** Hagmann 2008; Jeurissen 2014; Smith ACT + SIFT2; Jones 2013; Maier-Hein 2017; [Connectomics](connectomics.md).  
**Week 4 — this analysis.** Piper 2026; Toga 2003; Bernhardt 2015; [Strength](strength.md), [Asymmetry](asymmetry.md), [Statistics](statistics.md); [Other methods](other-methods.md) so you know what you are *not* claiming.

Contact for this documentation and software: **Philbert Ndagijimana**, [phindagijimana@gmail.com](mailto:phindagijimana@gmail.com).
