# Graph theory primer

This page is a full vocabulary for reading network-neuroscience papers. It is not a substitute for Bondy & Murty, Diestel, or Newman’s *Networks* (2010)[^newman2010], but it is meant to be enough that someone new to graphs can follow Rubinov & Sporns (2010)[^rubinov2010], Fornito, Zalesky & Bullmore (2016)[^fornito2016], and then the rest of this site.

`nodestrength` uses **one** local weighted measure (strength) plus laterality. Everything else here is the field you are walking into. Measures this CLI does **not** compute are expanded again, with BCT names and pitfalls, on [Graph theory beyond this tool](beyond.md).

## Why a graph at all?

A **graph** \(G=(V,E)\) is the simplest object that can say “these parts exist” (\(V\)) and “these pairs are related” (\(E\)). Euler’s Königsberg bridges (1736) already treated land masses as nodes and bridges as edges. In the 20th century the same object described social ties (Moreno; Granovetter 1973), citation networks, the web, and metabolic maps. Watts & Strogatz (1998)[^watts1998] and Barabási & Albert (1999)[^barabasi1999] made “complex networks” a discipline. Bullmore & Sporns (2009)[^bullmore2009] brought that language to neuroimaging.

Three questions the object is for (Rubinov & Sporns 2010; Fornito et al. 2016):

1. **Integration** — can this node reach, or be reached by, the rest of the system? Degree, strength, path length, efficiency, some centralities.
2. **Segregation** — are there densely wired clusters? Clustering, transitivity, modules.
3. **Layout / economy** — is the pattern small-world, core–periphery, hierarchical, spatially cheap? Watts–Strogatz; Bullmore & Sporns 2012 on the economical brain[^bullmore2012econ]; van den Heuvel & Sporns 2011 on the rich club[^vdh2011].

A hippocampal **node-strength** study is almost entirely question 1, plus left versus right. That is still graph theory, in the same way that measuring blood pressure is still cardiovascular physiology — a real but thin slice.

## The object, in full

### Nodes, edges, simple graphs

- **Node** (vertex) \(i \in V\). In MRI, usually a grey-matter parcel. In microscopy, a neuron. In voxel graphs, a voxel.
- **Edge** \(\{i,j\} \in E\) (undirected) or \((i,j) \in E\) (directed). In dMRI, a reconstructed white-matter connection. In fMRI, a statistical dependence.
- **Simple graph**: no self-loops, at most one edge per pair. Connectomes are made simple by **zeroing the diagonal** \(w_{ii}=0\) (a parcel is not treated as connected to itself).
- **Order** \(n = |V|\). **Size** \(m = |E|\).
- **Density** (undirected, simple): \(2m / n(n-1)\). Density is the most important confound in brain-graph papers (van Wijk, Stam & Daffertshofer 2010[^vanwijk2010]). Two groups with different density will differ in almost every metric even if their *organisation* is the same.

### Directed, weighted, binary, multilayer

| Adjective | Meaning in MRI | Typical use |
|---|---|---|
| Undirected | \(w_{ij}=w_{ji}\) after symmetrisation | Structural connectomes (`tck2connectome -symmetric`) |
| Directed | Separate \(w_{ij}\) and \(w_{ji}\) | Tractography *can* be written directed; axon polarity is not trusted. fMRI Granger/DCM are the directed literature (Friston 2011[^friston2011]) |
| Weighted | \(w_{ij}\in\mathbb{R}_+\) | Streamline count, SIFT2, mean FA, mean length |
| Binary | \(a_{ij}\in\{0,1\}\) | A thresholded skeleton; “is there a connection?” |
| Signed | \(w_{ij}\) may be negative | Functional anticorrelations (Rubinov & Sporns 2011) |
| Multilayer / multiplex | several edge types on the same \(V\) | Count and FA as layers (Kivelä et al. 2014[^kivela2014]; Boccaletti et al. 2014; Battiston et al. 2017, 2020) |

The **adjacency matrix** \(A\) stores a binary graph; the **weight matrix** \(W\) stores a weighted one. Row \(i\) is “from \(i\)”. For undirected graphs \(W=W^\top\). Almost every BCT function is a recipe on \(A\) or \(W\).

**Symmetrisation** used here: replace \(W\) by \((W+W^\top)/2\). That is the undirected convention of `strengths_und`. If you skip it on an asymmetric tractography matrix, “strength” quietly becomes a mixture of in- and out-weight.

### Connected components

A graph is **connected** if every node can reach every other by a path. dMRI connectomes at group-consistent thresholds are usually one giant component plus (sometimes) isolates. The number of connected components is the multiplicity of eigenvalue 0 of the Laplacian (see spectral section). Isolated nodes have strength 0; they must stay in the table so laterality can be undefined rather than silently 0.

## Degree and strength (this tool)

**Degree** of \(i\) is the number of neighbours:

\[
k_i = \sum_{j \neq i} a_{ij}
\]

On a directed graph one splits **in-degree** \(k_i^{\mathrm{in}}=\sum_j a_{ji}\) and **out-degree** \(k_i^{\mathrm{out}}=\sum_j a_{ij}\).

**Strength** is the weighted analogue (Barrat, Barthélemy, Pastor-Satorras & Vespignani 2004[^barrat2004]; Opsahl, Agneessens & Skvoretz 2010[^opsahl2010]; Rubinov & Sporns 2010):

\[
s_i = \sum_{j \neq i} w_{ij}
\]

BCT name: `strengths_und` (undirected) or `strengths_dir` (in/out). That is the entire computational core of this repository. High strength means “this parcel participates in a large total weight of reconstructed connections.” It does **not** mean “this parcel is a topological hub.” Hubs combine *how much* connection mass with *where* those edges go (betweenness, participation, rich-club membership; Sporns, Honey & Kötter 2007[^sporns2007]; van den Heuvel & Sporns 2011, 2013[^vdh2011][^vdh2013]).

Opsahl et al. (2010) generalise node centrality as a tunable mix of degree and strength, \(k_i \times (s_i/k_i)^\alpha\). BCT `strengths_und` is the \(\alpha=1\) end: pure weight sum. See [Node strength](strength.md) for biology, intrahemispheric masks, and normalisation.

**Degree / strength distribution** \(P(k)\) or \(P(s)\) is the first global fingerprint of a network. Report the empirical histogram. Do not assume it is a power law (next section but one).

## Paths, distance, and efficiency

A **walk** is a sequence of edges. A **trail** does not repeat edges. A **path** does not repeat nodes. The **shortest-path length** \(d_{ij}\) is the fewest hops (binary) or the smallest sum of *distances* (weighted).

On a weighted brain graph, a large \(w_{ij}\) should mean a *short* distance, so one almost always transforms weights before running Dijkstra / Floyd–Warshall:

\[
\ell_{ij} = \frac{1}{w_{ij}} \quad \text{or} \quad \ell_{ij} = -\log w_{ij}
\]

(Rubinov & Sporns 2010). Using raw streamline counts as distances would make strong connections look *far*. BCT `distance_wei` implements the inverse-weight convention unless you pass a custom length matrix.

**Characteristic path length** of a connected graph:

\[
L = \frac{1}{n(n-1)}\sum_{i \neq j} d_{ij}
\]

**Global efficiency** (Latora & Marchiori 2001[^latora2001]) is the mean inverse distance, and remains defined if the graph is disconnected (\(d_{ij}=\infty \Rightarrow 1/d_{ij}=0\)):

\[
E_{\mathrm{glob}} = \frac{1}{n(n-1)}\sum_{i \neq j} \frac{1}{d_{ij}}
\]

**Local efficiency** of node \(i\) is the global efficiency of the subgraph induced by \(i\)’s neighbours (how well they communicate if \(i\) is removed). That is a segregation-plus-fault-tolerance measure, not a first-order sum.

`nodestrength` computes **none** of these. If you add them, you need a distance transform, a density-matched null, and a statement about disconnected nodes.

## Clustering, transitivity, and motifs

### Binary clustering

The **local clustering coefficient** of \(i\) is the fraction of pairs among \(i\)’s neighbours that are themselves connected (Watts & Strogatz 1998[^watts1998]):

\[
C_i = \frac{2 t_i}{k_i(k_i-1)}
\]

where \(t_i\) is the number of triangles through \(i\). Average \(C = n^{-1}\sum_i C_i\). **Transitivity** is a related global ratio \(3\times\text{triangles}/\text{connected triples}\) that does not overweight low-degree nodes (Newman). High clustering = local triangles = **segregation**.

### Weighted clustering

Several generalisations exist and they are **not interchangeable**:

- Barrat et al. 2004 — weights on the two edges from \(i\) to its neighbours.
- Onnela et al. 2005[^onnela2005] — geometric mean of the three edge weights of each triangle (BCT `clustering_coef_wu` uses this family).
- Zhang & Horvath / other variants.

Always name which formula you used. Clustering on a dense probabilistic connectome is not comparable to clustering on a sparse deterministic one without a null at the same density (van Wijk 2010[^vanwijk2010]; Fornito, Zalesky & Breakspear 2013[^fornito2013]).

### Motifs

A **motif** is a small recurrent subgraph (Milo et al. 2002[^milo2002]). In directed neuronal / C. elegans / macaque networks, specific 3-node motifs are over-represented (Sporns & Kötter 2004[^spornskotter2004]). Macroscale undirected dMRI graphs have fewer interesting 3-node types (a triangle or not). Motif analysis needs a degree-preserving null; otherwise “we found triangles” is just “the graph is clustered.”

## Community detection and modularity

Brain networks are **modular**: nodes fall into communities with dense internal edges and sparser edges between communities (Meunier, Lambiotte & Bullmore 2010[^meunier2010]; Sporns & Betzel 2016).

Newman’s **modularity** \(Q\) (Newman 2006[^newman2006]; Newman & Girvan 2004) scores a partition \(\{c_i\}\):

\[
Q = \frac{1}{2m}\sum_{ij}\left(A_{ij}-\frac{k_i k_j}{2m}\right)\delta(c_i,c_j)
\]

The term \(k_i k_j / 2m\) is the expected edge weight in a random graph with the same degrees (the **configuration-model** null). Weighted and directed generalisations exist (Leicht & Newman 2008; Rubinov & Sporns 2011).

**Algorithms** (none of these are in `nodestrength`):

| Algorithm | Idea | Refs |
|---|---|---|
| Newman spectral / greedy | Maximise \(Q\) | Newman 2006 |
| Louvain | Multilevel greedy | Blondel et al. 2008[^blondel2008] |
| Leiden | Louvain fix (connected communities) | Traag, Waltman & van Eck 2019[^traag2019] |
| Infomap | Compress random-walk description length | Rosvall & Bergstrom 2008[^rosvall2008] |
| Stochastic block model | Generate edges from group labels | Peixoto; Karrer & Newman 2011 |

**Resolution limit** (Fortunato & Barthélemy 2007[^fortunato2007]): \(Q\) cannot see communities smaller than a scale set by \(m\). Multiresolution Potts / Reichardt–Bornholdt models and the SBM are the usual responses. **Never** treat a single Louvain run as *the* modules of the brain; consensus clustering across resolutions is the honest report (Lancichinetti & Fortunato 2009, 2012[^lancichinetti2009]).

Once you have a partition, two node measures become available:

- **Within-module degree z-score** — is \(i\) a hub *inside* its module?
- **Participation coefficient** \(P_i\) (Guimerà & Amaral 2005[^guimera2005]) — are \(i\)’s edges spread across modules or concentrated in one?

Provincial hubs: high \(z\), low \(P\). Connector hubs: high \(P\). This is the cartographic classification used in many hub papers (Sporns 2007; van den Heuvel & Sporns 2013). Strength alone cannot draw that map.

## Small-world and scale-free

### Small-world

Watts & Strogatz (1998) interpolates a ring lattice (high \(C\), long paths) toward a random graph (low \(C\), short paths). In the middle: **high clustering and short paths** — a small world.

Humphries & Gurney (2008)[^humphries2008] summarise this as

\[
\sigma = \frac{C/C_{\mathrm{rand}}}{L/L_{\mathrm{rand}}}
\]

with \(\sigma>1\) called small-world. Telesford et al. (2011)[^telesford2011] prefer

\[
\omega = \frac{L_{\mathrm{rand}}}{L} - \frac{C}{C_{\mathrm{latt}}}
\]

near 0 for small-world. Bassett & Bullmore (2006, 2017)[^bassett2006][^bassett2017sw] review the brain literature and the **caveats**: \(\sigma\) is almost always \(>1\) on thresholded MRI graphs because density and lattice nulls are poorly specified. A small-world *claim* requires an explicit null, matched density, and preferably \(\omega\) or a generative model (Betzel et al. 2016[^betzel2016]), not a \(\sigma\) table.

### Scale-free

Barabási & Albert (1999)[^barabasi1999]: growth plus preferential attachment \(\Rightarrow P(k)\sim k^{-\gamma}\). Many early brain papers reported “scale-free connectomes.” Clauset, Shalizi & Newman (2009)[^clauset2009] showed how to test power laws properly (KS, xmin, alternative distributions). Broido & Clauset (2019)[^broido2019] conclude that **scale-free networks are rare**. Structural MRI degree distributions are typically broad-tailed, not pure power laws. Report \(P(s)\) and a fitted alternative (log-normal, truncated power law). Do not write “scale-free” because a log–log plot looked straight.

## The centrality family

“Centrality” is not one number. It is a family of answers to “which nodes matter?” (Freeman 1978; Borgatti 2005).

| Measure | Formula / idea | BCT-style name | What it asks |
|---|---|---|---|
| Degree / strength | \(k_i\) or \(s_i\) | `degrees_und` / `strengths_und` | How much connection mass? |
| Betweenness | fraction of shortest paths through \(i\) | `betweenness_bin` / `_wei` | Does traffic sit on this node? Freeman 1977[^freeman1977] |
| Closeness | \(1/\sum_j d_{ij}\) | `closeness_bin` | How near to all others? |
| Harmonic closeness | \(\sum_j 1/d_{ij}\) | — | Like closeness, defined if disconnected |
| Eigenvector | \(Ax=\lambda x\), leading \(x\) | `eigenvector_centrality_und` | Connected to other well-connected nodes? Bonacich 1987 |
| PageRank | damped random walk | `pagerank_centrality` | Brin & Page 1998 |
| Katz | \((I-\alpha A)^{-1}\) | — | Walks of all lengths |
| Participation | diversity of modules | `participation_coef` | Guimerà & Amaral 2005 |
| Flow / current-flow betweenness | electrical analogue | — | Newman; Brandes & Fleischer |

**Rich-club coefficient** \(\phi(k)\) (Colizza et al. 2006; Opsahl 2008; van den Heuvel & Sporns 2011[^vdh2011]): among nodes with degree \(>k\), what fraction of possible edges exist, relative to a degree-preserving null? A rich club is a densely linked hub core — the “structural core” of Hagmann 2008 by another name. Strength does not tell you whether a strong hippocampus sits in that core.

Only the first row is implemented in this package.

## Assortativity and mixing

**Assortativity** \(r\) (Newman 2002, 2003[^newman2002]) is the Pearson correlation of the degrees (or strengths) of nodes at two ends of an edge. Social networks are assortative (hubs link to hubs); many technological graphs are disassortative. Brain structural networks are often reported as assortative, consistent with a rich club, but the coefficient is density- and parcellation-sensitive.

Related: **matching index** (similarity of two nodes’ neighbour sets) — used as a generative-model term (Betzel 2016) more than as a biomarker.

## Null models (why a number is not a finding)

A network metric without a **null** is not evidence of organisation (Fornito, Zalesky & Breakspear 2013[^fornito2013]). Common ensembles:

| Null | What it preserves | Use |
|---|---|---|
| Erdős–Rényi \(G(n,p)\) or \(G(n,m)\) | \(n\), density | Too weak for brain graphs (destroys degree sequence) |
| Configuration model / Maslov–Sneppen rewiring | Degree sequence | Maslov & Sneppen 2002[^maslov2002]; standard for \(Q\), \(\phi(k)\), motifs |
| Weight-preserving rewiring | Strengths / weights | Weighted clustering, efficiency |
| Lattice | Spatial neighbours | Small-world \(\omega\) |
| Spatially embedded / geometric | Distance distribution | Roberts et al.; Betzel; the brain is a physical object (Bullmore & Sporns 2012) |
| Minimum spanning tree | A loop-free backbone | Stam et al. 2014[^stam2014]; avoids density by construction |
| Stochastic block model | Community labels | Inference, not only a null |

`nodestrength` does not run nulls. Strength and AI against a *clinical* control group **are** using a biological null (patients vs controls), which is a different and valid question. What you must not do is compute clustering on patients vs controls at different densities and call it “altered small-worldness.”

## Spectral graph theory (the linear-algebra half)

Let \(D=\mathrm{diag}(s_1,\ldots,s_n)\) be the strength matrix. The **combinatorial Laplacian** is

\[
L = D - W
\]

Facts used constantly (Chung 1997; Spielman; Newman):

- \(L\mathbf{1}=0\). Multiplicity of eigenvalue 0 = number of connected components.
- The Fiedler value \(\lambda_2\) (algebraic connectivity) is small when the graph has a weak cut. Cheeger’s inequality relates \(\lambda_2\) to the sparsest cut.
- The normalised Laplacian \(D^{-1/2} L D^{-1/2}\) is the basis of spectral clustering (Shi & Malik; Ng, Jordan & Weiss).
- **Connectome harmonics** (Atasoy, Donnelly & Pearson 2016[^atasoy2016]) are the eigenvectors of \(L\) on a structural connectome, used as a basis for cortical activity — graph signal processing on the brain (Shuman et al. 2013; Huang et al.; Ortega et al. 2018).

**Strength is the diagonal of \(D\)**: the *zeroth* spectral object. Eigenvector centrality, harmonics, and cuts all live in the rest of the spectrum. That is “graph theory” in the course-catalogue sense, and it is out of scope for the CLI.

## Directed, signed, temporal, higher-order

Macroscale streamline connectomes are usually treated as **undirected, positive, static, pairwise**. The rest of graph theory is a cube of generalisations (Battiston et al. 2020, 2021[^battiston2020]):

- **Directed:** in-/out-strength, reciprocity, trophic levels, cycle space.
- **Signed:** positive and negative edges (functional anticorrelations); requires signed-modularity conventions (Rubinov & Sporns 2011).
- **Temporal / time-respecting paths:** Holme & Saramäki 2012; dynamic FC sliding windows (Lurie et al. 2020 — with strong caveats from Laumann, Noble, and others on reliability).
- **Higher-order:** hypergraphs, simplicial complexes, motif-based simplices, O-information (Rosas et al.). A triangle is no longer just clustering; it is a 2-simplex.

If a paper says “we applied graph theory to the connectome,” ask **which quadrant** of that cube, **which null**, and **which edge definition**.

## What MRI papers get wrong (a short list)

Drawn from Fornito, Zalesky & Breakspear (2013)[^fornito2013], van Wijk et al. (2010)[^vanwijk2010], de Reus & van den Heuvel (2013), and Jones, Knösche & Turner (2013):

1. Thresholding two groups to the same *density* vs the same *weight cutoff* answers different questions; say which.
2. Comparing 84-node DK graphs to 1000-node Schaefer graphs as if \(C\) and \(E\) were intensive quantities.
3. Calling streamline count an axon count.
4. Reporting 40 BCT metrics × 4 scales with uncorrected \(p\).
5. “Small-world” or “scale-free” as a default adjective.
6. Treating a correlation matrix like a structural adjacency (zeros, negatives, and nulls all differ).

The honest minimal report for **this** tool is: atlas, scale, LUT order, reconstruction (det/prob, SIFT2 or not), edge weight, intra- vs whole-brain strength, AI formula, and the clinical contrast. That is already a lot. Adding clustering does not make it “more graph theory”; it makes it a different paper.

## Where to go next

- [Node strength](strength.md) — the measure we actually compute, in biological detail.
- [Graph theory beyond this tool](beyond.md) — BCT catalogue with formulas and when *not* to use each measure.
- [Connectomics](connectomics.md) — how \(W\) is born from dMRI.
- Fornito, Zalesky & Bullmore (2016), chapters 1–8[^fornito2016]; Rubinov & Sporns (2010)[^rubinov2010]; Newman (2010)[^newman2010].

[^newman2010]: Newman MEJ. *Networks: An Introduction*. Oxford University Press; 2010.
[^rubinov2010]: Rubinov M, Sporns O. Complex network measures of brain connectivity: uses and interpretations. *NeuroImage*. 2010;52:1059–1069.
[^fornito2016]: Fornito A, Zalesky A, Bullmore ET. *Fundamentals of Brain Network Analysis*. Academic Press; 2016.
[^watts1998]: Watts DJ, Strogatz SH. Collective dynamics of ‘small-world’ networks. *Nature*. 1998;393:440–442.
[^barabasi1999]: Barabási A-L, Albert R. Emergence of scaling in random networks. *Science*. 1999;286:509–512.
[^bullmore2009]: Bullmore E, Sporns O. Complex brain networks: graph theoretical analysis of structural and functional systems. *Nat Rev Neurosci*. 2009;10:186–198.
[^bullmore2012econ]: Bullmore E, Sporns O. The economy of brain network organization. *Nat Rev Neurosci*. 2012;13:336–349.
[^vdh2011]: van den Heuvel MP, Sporns O. Rich-club organization of the human connectome. *J Neurosci*. 2011;31:15775–15786.
[^vdh2013]: van den Heuvel MP, Sporns O. Network hubs in the human brain. *Trends Cogn Sci*. 2013;17:683–696.
[^vanwijk2010]: van Wijk BCM, Stam CJ, Daffertshofer A. Comparing brain networks of different size and connectivity density using graph theory. *PLoS One*. 2010;5:e13701.
[^friston2011]: Friston KJ. Functional and effective connectivity: a review. *Brain Connect*. 2011;1:13–36.
[^kivela2014]: Kivelä M et al. Multilayer networks. *J Complex Netw*. 2014;2:203–271.
[^barrat2004]: Barrat A et al. The architecture of complex weighted networks. *PNAS*. 2004;101:3747–3752.
[^opsahl2010]: Opsahl T, Agneessens F, Skvoretz J. Node centrality in weighted networks. *Soc Networks*. 2010;32:245–251.
[^sporns2007]: Sporns O, Honey CJ, Kötter R. Identification and classification of hubs in brain networks. *PLoS One*. 2007;2:e1049.
[^latora2001]: Latora V, Marchiori M. Efficient behavior of small-world networks. *Phys Rev Lett*. 2001;87:198701.
[^onnela2005]: Onnela J-P et al. Intensity and coherence of motifs in weighted complex networks. *Phys Rev E*. 2005;71:065103.
[^milo2002]: Milo R et al. Network motifs: simple building blocks of complex networks. *Science*. 2002;298:824–827.
[^spornskotter2004]: Sporns O, Kötter R. Motifs in brain networks. *PLoS Biol*. 2004;2:e369.
[^meunier2010]: Meunier D, Lambiotte R, Bullmore ET. Modular and hierarchically modular organization of brain networks. *Front Neurosci*. 2010;4:200.
[^newman2006]: Newman MEJ. Modularity and community structure in networks. *PNAS*. 2006;103:8577–8582.
[^blondel2008]: Blondel VD et al. Fast unfolding of communities in large networks. *J Stat Mech*. 2008;P10008.
[^traag2019]: Traag VA, Waltman L, van Eck NJ. From Louvain to Leiden: guaranteeing well-connected communities. *Sci Rep*. 2019;9:5233.
[^rosvall2008]: Rosvall M, Bergstrom CT. Maps of random walks on complex networks reveal community structure. *PNAS*. 2008;105:1118–1123.
[^fortunato2007]: Fortunato S, Barthélemy M. Resolution limit in community detection. *PNAS*. 2007;104:36–41.
[^lancichinetti2009]: Lancichinetti A, Fortunato S. Community detection algorithms: a comparative analysis. *Phys Rev E*. 2009;80:056117.
[^guimera2005]: Guimerà R, Nunes Amaral LA. Functional cartography of complex metabolic networks. *Nature*. 2005;433:895–900.
[^humphries2008]: Humphries MD, Gurney K. Network ‘small-world-ness’: a quantitative method for determining canonical network equivalence. *PLoS One*. 2008;3:e0002051.
[^telesford2011]: Telesford QK et al. The ubiquity of small-world networks. *Brain Connect*. 2011;1:367–375.
[^bassett2006]: Bassett DS, Bullmore E. Small-world brain networks. *Neuroscientist*. 2006;12:512–523.
[^bassett2017sw]: Bassett DS, Bullmore ET. Small-world brain networks revisited. *Neuroscientist*. 2017;23:499–516.
[^betzel2016]: Betzel RF et al. Generative models of the human connectome. *NeuroImage*. 2016;124:1054–1064.
[^clauset2009]: Clauset A, Shalizi CR, Newman MEJ. Power-law distributions in empirical data. *SIAM Rev*. 2009;51:661–703.
[^broido2019]: Broido AD, Clauset A. Scale-free networks are rare. *Nat Commun*. 2019;10:1017.
[^freeman1977]: Freeman LC. A set of measures of centrality based on betweenness. *Sociometry*. 1977;40:35–41.
[^newman2002]: Newman MEJ. Assortative mixing in networks. *Phys Rev Lett*. 2002;89:208701.
[^maslov2002]: Maslov S, Sneppen K. Specificity and stability in topology of protein networks. *Science*. 2002;296:910–913.
[^stam2014]: Stam CJ et al. The trees and the forest: characterization of complex brain networks with minimum spanning trees. *Int J Psychophysiol*. 2014;92:129–138.
[^atasoy2016]: Atasoy S, Donnelly I, Pearson J. Human brain networks function in connectome-specific harmonic waves. *Nat Commun*. 2016;7:10340.
[^battiston2020]: Battiston F et al. Networks beyond pairwise interactions: structure and dynamics. *Phys Rep*. 2020;874:1–92.
[^fornito2013]: Fornito A, Zalesky A, Breakspear M. Graph analysis of the human connectome: promise, progress, and pitfalls. *NeuroImage*. 2013;80:426–444.
