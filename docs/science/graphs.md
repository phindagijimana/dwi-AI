# Graph theory primer

This page is the vocabulary. It is not a substitute for Bondy & Murty or Newman’s *Networks* (2010)[^newman2010], but it is enough to read a connectomics paper without drowning.

## The object

A **graph** \(G = (V, E)\) has a node set \(V\) and an edge set \(E \subseteq V \times V\).

| Adjective | Meaning in MRI |
|---|---|
| Undirected | \(w_{ij} = w_{ji}\). Typical structural connectome after symmetrisation. |
| Directed | Tractography *can* be directed but usually is not trusted as axon direction. |
| Weighted | \(w_{ij} \in \mathbb{R}_+\). Streamline count, SIFT2, mean FA, mean length. |
| Binary | \(a_{ij} \in \{0,1\}\). A thresholded skeleton. |
| Simple | No self-loops. We zero the diagonal. |
| Multigraph | Multiple edge types (Count and FA as layers) — a **multiplex** / multilayer graph (Kivelä et al. 2014[^kivela2014]; Battiston et al. 2017[^battiston2017]). |

The **adjacency matrix** \(A\) (binary) or **weight matrix** \(W\) is how we store \(G\). Row \(i\) is “from node \(i\)”. For undirected graphs \(W = W^\top\).

## Degree and strength

**Degree** \(k_i = \sum_j a_{ij}\) — number of neighbours.

**Strength** \(s_i = \sum_j w_{ij}\) — weighted degree (Barrat et al. 2004[^barrat2004]; Opsahl, Agneessens & Skvoretz 2010[^opsahl2010]; Rubinov & Sporns 2010[^rubinov2010]).

That is the entire core of this repository. In BCT the function is `strengths_und`. High strength means “this parcel participates in a large total weight of reconstructed connections,” **not** “this parcel is a topological hub” — hubs usually combine degree with *where* those edges go (betweenness, participation; Sporns, Honey & Kötter 2007[^sporns2007]; van den Heuvel & Sporns 2011, 2013[^vdh2011][^vdh2013]).

## Paths, distance, efficiency

A **walk** is a sequence of edges. A **path** does not repeat nodes. **Shortest-path length** on a weighted brain graph is usually computed on a *distance* transform such as \(d_{ij} = 1/w_{ij}\) (Rubinov & Sporns 2010). **Global efficiency** is the mean inverse shortest path (Latora & Marchiori 2001[^latora2001]). `nodestrength` does **not** compute these.

## Clustering and transitivity

**Clustering coefficient**: fraction of a node’s neighbours that are themselves connected (Watts & Strogatz 1998[^watts1998]; Onnela et al. 2005 weighted version[^onnela2005]). High clustering = local triangles = segregation.

## Modularity and communities

Partition \(V\) into modules that maximise Newman’s \(Q\) (Newman 2006[^newman2006]; Blondel et al. 2008 Louvain[^blondel2008]; Lancichinetti & Fortunato 2009[^lancichinetti2009]). Brain networks are modular (Meunier, Lambiotte & Bullmore 2010[^meunier2010]).

## Small-world and scale-free

**Small-world**: high clustering *and* short paths relative to a random graph (Watts–Strogatz 1998). Reported widely in brain data (Bassett & Bullmore 2006, 2017[^bassett2006][^bassett2017sw]) with the caveat that the null model and density matter (Humphries & Gurney 2008; Fornito et al. 2013).

**Scale-free**: \(P(k) \sim k^{-\gamma}\). Structural brain graphs are **not** unambiguously scale-free (for a critical view, Broido & Clauset 2019[^broido2019]). Prefer reporting the empirical degree/strength distribution.

## Centrality family

| Measure | Intuition | Ref |
|---|---|---|
| Degree / strength | How much connection mass | Barrat 2004 |
| Betweenness | How many shortest paths sit on this node | Freeman 1977[^freeman1977] |
| Eigenvector / PageRank | Connected to other well-connected nodes | Bonacich 1987; Brin & Page 1998 |
| Participation coefficient | Edges spread across modules | Guimerà & Amaral 2005[^guimera2005] |
| Rich-club coefficient | Hubs linking to hubs | Colizza 2006; van den Heuvel & Sporns 2011 |

Only the first row is implemented here.

## Null models (why they matter)

A number without a null is not a network finding. Common nulls: Erdős–Rényi, Maslov–Sneppen degree-preserving rewiring (Maslov & Sneppen 2002[^maslov2002]), weight-preserving variants, and the **minimum spanning tree** (Stam et al. 2014[^stam2014]). `nodestrength` does not run nulls; if you add clustering or efficiency, you must.

## Linear algebra one-liners

- Laplacian \(L = D - W\). Spectrum encodes cuts and synchronisation (Chung 1997; Spielman).
- Normalised Laplacian used in spectral clustering.
- Graph harmonics / connectome harmonics (Atasoy et al. 2016[^atasoy2016]) are this Laplacian’s eigenvectors on a structural graph.

These are “graph theory” in the strong sense, and they are **out of scope** for the CLI.

[^newman2010]: Newman MEJ. *Networks: An Introduction*. Oxford University Press; 2010.
[^kivela2014]: Kivelä M et al. Multilayer networks. *J Complex Netw*. 2014;2:203–271.
[^battiston2017]: Battiston F et al. The physics of multilayer networks. *Phys Rep*. later reviews; see also Boccaletti 2014.
[^barrat2004]: Barrat A et al. The architecture of complex weighted networks. *PNAS*. 2004;101:3747–3752.
[^opsahl2010]: Opsahl T, Agneessens F, Skvoretz J. Node centrality in weighted networks. *Soc Networks*. 2010;32:245–251.
[^rubinov2010]: Rubinov M, Sporns O. *NeuroImage*. 2010;52:1059–1069.
[^sporns2007]: Sporns O, Honey CJ, Kötter R. Identification and classification of hubs in brain networks. *PLoS One*. 2007;2:e1049.
[^vdh2011]: van den Heuvel MP, Sporns O. Rich-club organization of the human connectome. *J Neurosci*. 2011;31:15775–15786.
[^vdh2013]: van den Heuvel MP, Sporns O. Network hubs in the human brain. *Trends Cogn Sci*. 2013;17:683–696.
[^latora2001]: Latora V, Marchiori M. Efficient behavior of small-world networks. *Phys Rev Lett*. 2001;87:198701.
[^watts1998]: Watts DJ, Strogatz SH. *Nature*. 1998;393:440–442.
[^onnela2005]: Onnela J-P et al. Intensity and coherence of motifs in weighted complex networks. *Phys Rev E*. 2005;71:065103.
[^newman2006]: Newman MEJ. Modularity and community structure in networks. *PNAS*. 2006;103:8577–8582.
[^blondel2008]: Blondel VD et al. Fast unfolding of communities in large networks. *J Stat Mech*. 2008;2008:P10008.
[^lancichinetti2009]: Lancichinetti A, Fortunato S. Community detection algorithms: a comparative analysis. *Phys Rev E*. 2009;80:056117.
[^meunier2010]: Meunier D, Lambiotte R, Bullmore ET. Modular and hierarchically modular organization of brain networks. *Front Neurosci*. 2010;4:200.
[^bassett2006]: Bassett DS, Bullmore E. Small-world brain networks. *Neuroscientist*. 2006;12:512–523.
[^bassett2017sw]: Bassett DS, Bullmore ET. Small-world brain networks revisited. *Neuroscientist*. 2017;23:499–516.
[^broido2019]: Broido AD, Clauset A. Scale-free networks are rare. *Nat Commun*. 2019;10:1017.
[^freeman1977]: Freeman LC. A set of measures of centrality based on betweenness. *Sociometry*. 1977;40:35–41.
[^guimera2005]: Guimerà R, Nunes Amaral LA. Functional cartography of complex metabolic networks. *Nature*. 2005;433:895–900.
[^maslov2002]: Maslov S, Sneppen K. Specificity and stability in topology of protein networks. *Science*. 2002;296:910–913.
[^stam2014]: Stam CJ et al. The trees and the forest: characterization of complex brain networks with minimum spanning trees. *Int J Psychophysiol*. 2014;92:129–138.
[^atasoy2016]: Atasoy S, Donnelly I, Pearson J. Human brain networks function in connectome-specific harmonic waves. *Nat Commun*. 2016;7:10340.
