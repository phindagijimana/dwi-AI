# Literature guide

A reading path, not a dump. Papers are grouped so someone new to **networks → connectomics → graph theory in neuroscience → this tool** can walk it in order. Full bibliographic entries are on [References](../references.md).

## 1. What is a connectome?

| Paper | Why read it |
|---|---|
| Sporns, Tononi & Kötter 2005, *PLoS Comput Biol* | Named the human connectome |
| Hagmann et al. 2008, *PLoS Biol* | First high-profile diffusion network of cortex; structural core |
| Bullmore & Sporns 2009, *Nat Rev Neurosci* | The review everyone cites |
| Van Essen et al. 2013, *NeuroImage* | HCP: how modern multi-modal data are organised |
| Lichtman & Sanes 2008 | Microscale / electron-microscopy connectomics (different scale, same word) |

## 2. Graph theory without tears

| Paper / book | Why |
|---|---|
| Watts & Strogatz 1998, *Nature* | Small-world |
| Barabási & Albert 1999, *Science* | Scale-free (use critically) |
| Newman 2010, *Networks* | Textbook |
| Barrat et al. 2004, *PNAS* | Weighted networks; strength |
| Latora & Marchiori 2001 | Efficiency |
| Newman 2006, *PNAS* | Modularity |
| Freeman 1977 | Betweenness |

## 3. Network neuroscience catalogues

| Paper / book | Why |
|---|---|
| Rubinov & Sporns 2010, *NeuroImage* | **BCT.** Definitions of strength and almost every other metric |
| Fornito, Zalesky & Bullmore 2016 | Best textbook for this audience |
| Fornito, Zalesky & Breakspear 2013, *NeuroImage* | Pitfalls |
| Bassett & Sporns 2017, *Nat Neurosci* | Field manifesto |
| van den Heuvel & Sporns 2011 / 2013 | Rich club; hubs |
| Bassett & Bullmore 2006, 2017 | Small-world brain networks (and the revisit) |
| Meunier, Lambiotte & Bullmore 2010 | Modules |
| Zalesky et al. 2010 *NeuroImage* (nodes) | Parcellation changes the graph |
| van Wijk, Stam & Daffertshofer 2010 | Density and size confounds |
| de Reus & van den Heuvel 2013 | Parcellation-based connectome limits |

## 4. Diffusion MRI and tractography (how \(W\) is born)

| Paper | Why |
|---|---|
| Basser, Mattiello & LeBihan 1994 | DTI |
| Tournier, Calamante & Connelly 2007 | CSD |
| Jeurissen et al. 2014 | MSMT-CSD |
| Tournier et al. 2019, *NeuroImage* | MRtrix3 |
| Smith et al. 2012 | ACT |
| Smith et al. 2013 / 2015 | SIFT / SIFT2 |
| Daducci et al. 2015 | COMMIT |
| Cieslak et al. 2021, *Nat Methods* | QSIPrep |
| Jones, Knösche & Turner 2013 | “Fiber count and other fallacies” |
| Thomas et al. 2014, *PNAS* | Anatomical accuracy is limited |
| Maier-Hein et al. 2017, *Nat Commun* | International tractography challenge |
| Schilling et al. 2019 | Modern methods still limited |
| Yeh et al. 2021 | Challenges and opportunities review |
| Cammoun et al. 2012 | Lausanne 2008 scales |
| Desikan et al. 2006 | DK atlas |

## 5. Functional connectivity (contrast class)

| Paper | Why |
|---|---|
| Biswal et al. 1995 | Resting-state FC |
| Friston 2011 | Functional vs effective |
| Smith et al. 2011 | Network modelling for fMRI |
| Power et al. 2012 | Motion artefact |
| Zalesky, Fornito & Bullmore 2010 | **NBS** |

## 6. Laterality, epilepsy, hippocampus, thalamus

| Paper | Why |
|---|---|
| Toga & Thompson 2003 | Mapping brain asymmetry |
| Kong et al. 2018, *PNAS* | ENIGMA cortical laterality |
| Spencer 2002; Richardson 2012 | Epilepsy as a network disorder |
| Bernhardt, Bonilha & Gross 2015, *Epilepsia* | Connectomics in epilepsy |
| **Piper et al. 2026, *Epilepsia*** | **This software’s methods paper** (thalamocortical strength) |
| Su et al. THOMAS | Thalamic nuclei atlas |

## 7. Methods this CLI does not run (but the literature does)

| Paper | Topic |
|---|---|
| Zalesky 2010 NBS | Edgewise component inference |
| Shen et al. 2017 | Connectome-based predictive modelling |
| Raffelt et al. 2017 | Fixel-based analysis |
| Yeatman et al. 2012 | AFQ tractometry |
| Seidlitz et al. 2018 | Morphometric similarity networks |
| Atasoy et al. 2016 | Connectome harmonics |
| Stam et al. 2014 | Minimum spanning trees |
| Marquand et al. 2016 | Normative models |
| Winkler et al. 2014 | PALM permutation inference |
| Traag, Waltman & van Eck 2019 | Leiden communities |
| Broido & Clauset 2019 | Scale-free networks are rare |

## 8. How to cite work that used this stack

Minimum set for a paper that ran QSIPrep → MRtrix/QSIRecon → `nodestrength`:

1. Cieslak et al. 2021 (if QSIPrep)
2. Tournier et al. 2019 (MRtrix3)
3. Smith et al. 2015 (if SIFT2)
4. Atlas paper (Desikan 2006 or Cammoun 2012 or THOMAS)
5. Rubinov & Sporns 2010 (strength)
6. Piper et al. 2026 (analysis design)
7. **Ndagijimana P. (2026).** *nodestrength* [computer software]. [github.com/phindagijimana/dwi-AI](https://github.com/phindagijimana/dwi-AI). Contact: [phindagijimana@gmail.com](mailto:phindagijimana@gmail.com). See [Citing](../citing.md).

## 9. Suggested four-week reading plan

**Week 1** — Sporns 2005; Bullmore & Sporns 2009; this site’s [Networks](networks.md) and [Graphs](graphs.md) pages.  
**Week 2** — Rubinov & Sporns 2010 with BCT open; Barrat 2004; Fornito textbook ch. 1–4.  
**Week 3** — Hagmann 2008; Jeurissen 2014; Smith SIFT2; Jones 2013; Maier-Hein 2017; [Connectomics](connectomics.md).  
**Week 4** — Piper 2026; Toga 2003; Bernhardt 2015; [Strength](strength.md), [Asymmetry](asymmetry.md), [Statistics](statistics.md); then skim [Beyond](beyond.md) so you know what you are *not* claiming.
