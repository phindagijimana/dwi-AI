# Graph theory beyond this tool

The Brain Connectivity Toolbox (Rubinov & Sporns 2010)[^rubinov2010] catalogues dozens of measures. MATLAB/Python BCT, NetworkX, `bctpy`, `igraph`, and Brainstorm implement most of them. This package uses **one** (`strengths_und`) plus laterality. The rest of the catalogue is real graph theory. This page is the map, with enough formula and literature that a newcomer can see what each measure *is*, what question it answers, and why we do not ship it by default.

Companion textbook: Fornito, Zalesky & Bullmore (2016)[^fornito2016]. Companion primer: [Graph theory primer](graphs.md).

## Local measures (one number per node)

### Clustering coefficient

**Question:** are my neighbours connected to each other?  
**Binary:** \(C_i = 2t_i / k_i(k_i-1)\). **Weighted:** Onnela / Barrat / Zhang variants (name which).  
**BCT:** `clustering_coef_bu`, `clustering_coef_wu`.  
**Pitfall:** \(C\) rises automatically with density. Compare at matched density to a rewired null (van Wijk 2010[^vanwijk2010]).  
**When to use:** a segregation hypothesis (“the epileptic hippocampus is less locally clustered”), *after* you have stated the null.

### Local efficiency

**Question:** if node \(i\) is removed, how well do its neighbours still communicate?  
**Formula:** global efficiency of the neighbourhood subgraph (Latora & Marchiori 2001[^latora2001]; Achard & Bullmore 2007 on brain networks).  
**BCT:** `efficiency_bin` / `efficiency_wei` with local flag.  
**Pitfall:** needs a distance transform on weighted graphs; disconnected neighbourhoods drive the metric.

### Betweenness centrality

**Question:** what fraction of shortest paths sit on \(i\)?  
**Formula (Freeman 1977):** \(b_i = \sum_{s\neq i \neq t} \sigma_{st}(i)/\sigma_{st}\). Weighted versions use a length matrix.  
**BCT:** `betweenness_bin`, `betweenness_wei`. Brandes (2001) algorithm is the practical implementation.  
**Pitfall:** a single bottleneck edge can dominate; very sensitive to false-positive long-range streamlines. Not a substitute for strength.

### Closeness and harmonic closeness

**Question:** how near is \(i\) to everyone else?  
**Closeness:** \(1/\sum_j d_{ij}\) — undefined or awkward if the graph is disconnected.  
**Harmonic:** \(\sum_j 1/d_{ij}\) — well-defined with \(d_{ij}=\infty\).  
**Pitfall:** in a 400-node connectome almost everyone is 2–3 hops away; the dynamic range is tiny once density is high.

### Eigenvector, PageRank, Katz

**Question:** is \(i\) connected to other well-connected nodes?  
**Eigenvector:** principal eigenvector of \(A\) (Bonacich 1987).  
**PageRank:** \((I-\alpha A D^{-1})^{-1}\) damped walk (Brin & Page 1998).  
**Katz:** walks of all lengths with attenuation \(\alpha\).  
**BCT:** `eigenvector_centrality_und`, `pagerank_centrality`.  
**Pitfall:** on undirected connected graphs these are highly correlated with strength. They earn their keep on *directed* or very heterogeneous graphs.

### Matching index

**Question:** how similar are the neighbour sets of \(i\) and \(j\)?  
Used more as a *generative* term (Betzel et al. 2016[^betzel2016]) than as a clinical biomarker.

### Within-module degree \(z\) and participation \(P_i\)

**Question:** provincial hub or connector hub?  
Requires a community partition first (Guimerà & Amaral 2005[^guimera2005]; Sporns, Honey & Kötter 2007).  
**BCT:** `module_degree_zscore`, `participation_coef`.  
**Pitfall:** garbage partition \(\Rightarrow\) garbage cartography. Run consensus communities, not one Louvain seed.

## Mesoscale (structure of groups of nodes)

### Community detection

Covered in the [primer](graphs.md#community-detection-and-modularity). Practical rule: report algorithm, resolution, consensus across runs, and \(Q\) versus a degree-preserving null. Leiden (Traag 2019)[^traag2019] is the default upgrade from Louvain. Infomap (Rosvall & Bergstrom 2008) optimises a different objective (random-walk compression) and can disagree with \(Q\) — that disagreement is scientifically interesting, not a bug.

### Core–periphery and rich club

Borgatti & Everett (2000) formalise a dense core with a sparse periphery. The **rich club** \(\phi(k)\) (Colizza 2006; van den Heuvel & Sporns 2011[^vdh2011]) asks whether high-degree nodes are *unexpectedly* densely linked to each other. Hagmann et al. 2008’s “structural core” (posterior medial / parietal) is the empirical cousin.

**Pitfall:** \(\phi(k)\) must be normalised by a configuration-model null, \(\phi_{\mathrm{norm}}(k)=\phi(k)/\phi_{\mathrm{rand}}(k)\). Raw \(\phi(k)\) always rises at high \(k\) in any heavy-tailed graph.

### Motifs and k-cores

**Motifs:** over-represented small subgraphs vs a null (Milo 2002; Sporns & Kötter 2004). Macroscale undirected connectomes have a limited motif zoo.

**k-core:** iteratively delete nodes with degree \(<k\). The remaining shell is a robust core (Alvarez-Hamelin; Hagmann-style cores). Cheap to compute; still needs a null if you compare groups.

## Global measures (one number per brain)

| Measure | Idea | Canonical ref | Main confound |
|---|---|---|---|
| Characteristic path length \(L\) | Mean shortest path | Watts–Strogatz 1998 | Density, disconnected nodes |
| Global efficiency \(E_{\mathrm{glob}}\) | Mean inverse path | Latora & Marchiori 2001 | Distance transform |
| Small-world \(\sigma\), \(\omega\) | High \(C\), short \(L\) vs nulls | Humphries 2008; Telesford 2011 | Almost always “significant” if null is ER |
| Assortativity \(r\) | Degree–degree correlation | Newman 2002 | Density, parcellation |
| Modularity \(Q\) | Quality of a partition | Newman 2006 | Resolution limit |
| Synchronisability | Laplacian spectrum | Barahona & Pecora | Model of dynamics, not a measurement |
| Algebraic connectivity \(\lambda_2\) | Fiedler value of \(L\) | Fiedler 1973; Chung 1997 | Component structure |
| Graph energy / von Neumann entropy | Spectral summaries | — | Hard to interpret clinically |
| MST diameter, leaf fraction | Stats on a tree backbone | Stam 2014[^stam2014] | Loses cycles on purpose |

Global metrics are where **forking paths** explode: threshold × weight × atlas × null × metric. Button et al. (2013) on power and Ioannidis on false-positive science apply brutally here. A pre-registered strength+AI contrast is a more defensible paper than an uncorrected 50-metric BCT dump.

## Spectral methods in more detail

The Laplacian \(L=D-W\) (or the normalised version) is the adjacency matrix’s more structural cousin:

- **Connected components** = dim ker \(L\).
- **Cheeger / Fiedler:** a small \(\lambda_2\) means a sparse cut — the graph almost falls into two pieces. Spectral clustering uses the Fiedler vector as a 1-D embedding and thresholds it.
- **Graph signal processing:** treat a cortical map (thickness, BOLD amplitude, an AI vector) as a *signal* on the nodes; the Laplacian eigenbasis is a Fourier basis on the connectome (Shuman 2013; Ortega 2018). Atasoy et al. (2016)[^atasoy2016] called the structural eigenmaps **connectome harmonics** and related them to resting-state patterns.
- **Heat kernels / diffusion embedding:** \(e^{-tL}\) is the graph analogue of a Gaussian blur; used in manifold learning on connectomes (Margulies 2016 “principal gradient” is a related embedding on functional connectivity).

Strength is \(\mathrm{diag}(D)\). If you only compute strength, you have not done spectral graph theory; you have done the degree sequence.

## Random-graph ensembles and statistical inference

Repeating the primer with the *inference* hat on:

- **Erdős–Rényi** — too simple; destroys hubs.
- **Configuration model** — preserves degrees; the default null for \(Q\), motifs, rich-club.
- **Stochastic block model** — infers communities as a generative model (Peixoto’s `graph-tool`); comes with model selection (minimum description length) instead of a single \(Q\).
- **Exponential random graph models (ERGM)** — specify \(P(G)\propto \exp(\theta\cdot \text{features})\). Poorly identified on \(n\sim 400\) MRI graphs; use with scepticism.
- **Geometric / hyperbolic / latent-space** — nodes have coordinates; edges prefer short distances (Betzel 2016; Roberts, Perry, Lord et al.). The brain is spatially embedded; a null that ignores Euclidean distance will call every short-range triangle “clustering.”
- **Minimum spanning tree** — one connected acyclic backbone; density is no longer a free parameter (Stam 2014). You lose all cycles, so clustering is identically zero; you study *hierarchy of the tree* instead.

Without some ensemble, “small-world” and “modular” are adjectives, not results (Fornito, Zalesky & Breakspear 2013[^fornito2013]).

## Directed, signed, temporal, higher-order

See the primer’s last technical section. Practical pointers:

- **Directed structural MRI** is usually a mistake: tractography polarity is not axon polarity. Directed *functional* graphs are a different literature (DCM, Granger — Friston 2011).
- **Signed** modularity must not treat a negative edge as “missing.” Rubinov & Sporns 2011 give the convention BCT uses.
- **Dynamic FC** reliability is low at short windows (Noble, Scheinost & Constable; Laumann et al.). Do not compute 50 BCT metrics per window.
- **Higher-order / simplicial** methods (Battiston 2020, 2021; Giusti, Ghrist, Bassett on clique topology) are active research. They are not a drop-in replacement for `strengths_und`.

## Why this package still only ships strength

Piper et al. 2026 asked whether **thalamic nuclei differ in total structural coupling** with cortex, by side and group[^piper2026]. That is a **weighted-degree** hypothesis. Efficiency, modularity, or rich-club would answer *different* questions and would require density-matched nulls the paper did not claim.

If you extend `nodestrength` with other BCT measures:

1. Document the edge definition (Count vs FA vs SIFT2).
2. Document the null.
3. Pre-register the metric list.
4. Do not Bonferroni 50 metrics on 288 subjects into a story.

The “connectomic garden of forking paths” is how the literature filled with unreplicable small-world papers. Strength plus a named laterality contrast is a narrower, cleaner claim.

[^rubinov2010]: Rubinov M, Sporns O. *NeuroImage*. 2010;52:1059–1069.
[^fornito2016]: Fornito A, Zalesky A, Bullmore ET. *Fundamentals of Brain Network Analysis*. 2016.
[^vanwijk2010]: van Wijk BCM, Stam CJ, Daffertshofer A. *PLoS One*. 2010;5:e13701.
[^latora2001]: Latora V, Marchiori M. *Phys Rev Lett*. 2001;87:198701.
[^betzel2016]: Betzel RF et al. Generative models of the human connectome. *NeuroImage*. 2016;124:1054–1064.
[^guimera2005]: Guimerà R, Nunes Amaral LA. *Nature*. 2005;433:895–900.
[^traag2019]: Traag VA, Waltman L, van Eck NJ. *Sci Rep*. 2019;9:5233.
[^vdh2011]: van den Heuvel MP, Sporns O. *J Neurosci*. 2011;31:15775–15786.
[^stam2014]: Stam CJ et al. *Int J Psychophysiol*. 2014;92:129–138.
[^atasoy2016]: Atasoy S et al. *Nat Commun*. 2016;7:10340.
[^fornito2013]: Fornito A, Zalesky A, Breakspear M. *NeuroImage*. 2013;80:426–444.
[^piper2026]: Piper RJ et al. *Epilepsia*. 2026;67:1901–1915.
