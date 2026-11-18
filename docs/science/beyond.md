# Graph theory beyond this tool

BCT (Rubinov & Sporns 2010)[^rubinov2010] and the Brain Connectivity Toolbox in MATLAB/Python implement dozens of measures. This package uses **one** of them (`strengths_und`) plus laterality. Everything below is real graph theory that **we do not compute**, so that a newcomer can see the rest of the map.

The Brain Connectivity Toolbox paper is the primary catalogue[^rubinov2010]. Complementary: Fornito, Zalesky & Bullmore 2016[^fornito2016]; Sporns 2018 *Graph Theory Methods for the Neurosciences*.

## Local measures (node-level)

| Measure | Idea | Why it is not strength |
|---|---|---|
| Clustering coefficient | Triangles among neighbours | Needs a 3-node motif, not a sum |
| Local efficiency | Inverse of shortest paths in the neighbourhood | Path-based |
| Betweenness centrality | Fraction of shortest paths through \(i\) | Global paths |
| Closeness / harmonic closeness | How near to all others | Distance |
| Eigenvector / PageRank / Katz | Prestige | Spectral |
| Matching index | Similarity of neighbour sets | Overlap, not mass |
| Within-module degree z | Hub inside a community | Needs a partition |
| Participation coefficient | Diversity of modules touched | Needs a partition |

## Mesoscale

- **Community detection** — Louvain, Leiden (Traag 2019), Infomap (Rosvall & Bergstrom 2008), stochastic block models (Peixoto).
- **Core–periphery** — Borgatti & Everett 2000; rich-club (van den Heuvel & Sporns 2011)[^vdh2011].
- **Motifs** — Milo et al. 2002; Sporns & Kötter 2004.
- **K-core decomposition**.

## Global

- Characteristic path length, global efficiency (Latora & Marchiori 2001)
- Small-world index \(\sigma\) or \(\omega\) (Telesford 2011)
- Assortativity (Newman 2002) — do high-strength nodes connect to each other?
- Synchronisability, algebraic connectivity (Fiedler eigenvalue of the Laplacian)
- Graph energy, von Neumann graph entropy
- Minimum spanning tree statistics (Stam 2014)

## Spectral graph theory

Eigenvalues of \(A\) or \(L = D-W\):

- Number of connected components = multiplicity of eigenvalue 0 of \(L\)
- Cheeger inequality — cuts vs spectral gap
- Connectome harmonics (Atasoy 2016)[^atasoy2016]
- Graph signal processing on the brain (Huang; Shuman; Ortega)

This is the part of “graph theory” that looks like linear algebra courses. Strength is the diagonal of \(D\), i.e. the *zeroth* spectral object.

## Random-graph ensembles and inference

- Erdős–Rényi, configuration model, stochastic block model
- Exponential random graph models (ERGM) — rarely well-posed on 400-node MRI graphs
- Geometric / spatially embedded nulls (Roberts, Perry, Lord, Roberts, Mitchell; Betzel)
- Hyperbolic / latent-space models

Without a null, “small-world” and “modularity” are not findings (Fornito, Zalesky & Breakspear 2013[^fornito2013]).

## Directed, signed, temporal, higher-order

- Directed: in-/out-strength, reciprocity, trophic analysis
- Signed: functional anticorrelations (Rubinov & Sporns 2011 signed networks)
- Temporal: time-respecting paths (Holme & Saramäki 2012)
- Higher-order: simplicial complexes, hypergraphs, O-information (Rosas; Battiston 2020, 2021)

Streamline connectomes are usually treated as undirected, positive, static, pairwise — the simplest quadrant of that cube.

## Why we still only ship strength

Piper et al. 2026 asked whether **thalamic nuclei differ in total structural coupling** with cortex, by side and group. That hypothesis is a **weighted degree** hypothesis. Adding efficiency or modularity would answer a different question and would require density-matched nulls, which the paper did not claim.

If you extend `nodestrength` with other BCT measures, document the null model and the edge definition. Do not dump 50 metrics on 288 subjects and Bonferroni your way to a story (the “connectomic garden of forking paths”; see also Ioannidis; Button et al. 2013 on power).

[^rubinov2010]: Rubinov M, Sporns O. *NeuroImage*. 2010;52:1059–1069.
[^fornito2016]: Fornito A, Zalesky A, Bullmore ET. *Fundamentals of Brain Network Analysis*. 2016.
[^vdh2011]: van den Heuvel MP, Sporns O. *J Neurosci*. 2011;31:15775–15786.
[^atasoy2016]: Atasoy S et al. *Nat Commun*. 2016;7:10340.
[^fornito2013]: Fornito A, Zalesky A, Breakspear M. *NeuroImage*. 2013;80:426–444.
