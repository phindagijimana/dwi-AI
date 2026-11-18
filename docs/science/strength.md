# Node strength

**Node strength** is the weighted analogue of degree: the sum of edge weights incident on a node (Barrat et al. 2004[^barrat2004]; Opsahl, Agneessens & Skvoretz 2010[^opsahl2010]; Rubinov & Sporns 2010[^rubinov2010]).

\[
s_i = \sum_{j \in V,\, j \neq i} w_{ij}
\]

For an undirected connectome this package first replaces \(W\) with \((W+W^\top)/2\) and sets \(w_{ii}=0\). That is BCT `strengths_und`, and it is what `nodestrength compute-strength` and `dkt-ai-cohort` print.

If `bctpy` is installed, the canonical BCT implementation is used; otherwise an equivalent NumPy row-sum after symmetrisation. With the same \(W\), the two match to numerical precision.

## Degree versus strength versus “hub”

| Quantity | On binary \(A\) | On weighted \(W\) |
|---|---|---|
| How many neighbours? | Degree \(k_i\) | — (or count of \(w_{ij}>0\)) |
| How much connection mass? | Same as degree | **Strength** \(s_i\) |
| How central in paths / modules? | Betweenness, participation, … | Same family on a distance transform |

A node can have **low degree and high strength** (few but very heavy edges) or the reverse. Opsahl et al. (2010) interpolate with \(k_i (s_i/k_i)^\alpha\). We use \(\alpha=1\): pure strength.

**Hub** in the network-neuroscience sense (Sporns, Honey & Kötter 2007; van den Heuvel & Sporns 2013[^vdh2013]) is not strength. Provincial vs connector hubs need a community partition. Rich-club membership needs \(\phi(k)\) versus a null. Strength is necessary but not sufficient.

## What it means biologically (structural MRI)

If \(w_{ij}\) is a **SIFT2-weighted streamline count**, \(s_i\) is a reconstruction of how much white-matter connection mass parcel \(i\) participates in. It is **not**:

- the number of synapses or axons (Jones, Knösche & Turner 2013[^jones2013])
- a guarantee of a true anatomical projection (Maier-Hein 2017[^maierhein2017]; Thomas 2014)
- independent of parcel volume, reconstruction, or requested streamline count

If \(w_{ij}\) is **mean FA**, \(s_i\) mixes *how many reconstructed connections* with *how anisotropic those connections are* — a microstructure-weighted load, a different construct. If \(w_{ij}\) is **mean length**, \(s_i\) is a millimetre-sum, not wiring mass.

Always name the edge. See [Connectomics](connectomics.md#edge-weights-are-different-graphs).

## Intrahemispheric and interhemispheric strength

Let \(H(i)\) be the hemisphere of node \(i\).

**Intrahemispheric** strength (IDEAS hippocampus default):

\[
s_i^{\mathrm{intra}} = \sum_{j: H(j)=H(i),\, j\neq i} w_{ij}
\]

**Interhemispheric** strength:

\[
s_i^{\mathrm{inter}} = \sum_{j: H(j)\neq H(i)} w_{ij}
\]

`dkt-ai-cohort` writes all three (`strength`, `strength_intra`, `strength_inter`) so laterality of a deep nucleus is not dominated by the corpus callosum. Piper et al. 2026’s **global brain strength** covariate is the unmasked whole-brain sum (used in the normative GLM), not the intra mask.

Whole-brain undirected total weight is \(\frac{1}{2}\sum_i s_i\) (each edge counted twice in the \(s_i\) sum).

## Normalisation and confounds

Raw \(s_i\) scales with:

- number of streamlines requested (`tckgen -select`)
- SIFT2 on/off
- det vs prob
- brain size and **parcel volume** (bigger parcels collect more streamlines — a well-known bias)
- head motion, in some pipelines

| Approach | Idea | Caveat |
|---|---|---|
| CountScaled | divide edges or strength by volume and/or length | Which divisor? Inconsistent across labs |
| Strength fraction | \(s_i / \sum_k s_k\) | Loses a global hypo-connectivity effect |
| Covariate global strength | Piper 2026 GLM/OLS | Preferred when you care about *residual* regional effects |
| Consistency thresholding | keep edges present in a fraction of subjects | Changes topology; a different paper |
| MST | density-free backbone | Stam 2014; discards cycles |

There is no universally correct normalisation. Report the one you used. This CLI exposes raw strength (and intra/inter) and, with `--participants`, OLS residuals against controls.

## Strength versus volume

Grey-matter **volume** of the same parcel is a different measurement (FreeSurfer `aseg`/`aparc` or voxel count on `dk_nodes.mif`). In hippocampal sclerosis, volume loss is the textbook MRI finding. Connectivity strength asks whether remaining tissue is also under-wired. The two can disagree:

- small but well-connected remnant
- normal-sized but disconnected parcel (less common, but possible with reconstruction failure)

`--with-volume-ai` writes both, plus `compare/strength_vs_volume_ai.csv`. Volume AI uses the same laterality formula as strength AI ([Asymmetry](asymmetry.md)).

## Directed graphs

If you ever keep \(W\) asymmetric:

\[
s_i^{\mathrm{out}}=\sum_j w_{ij},\qquad s_i^{\mathrm{in}}=\sum_j w_{ji}
\]

BCT `strengths_dir`. Macroscale tractography polarity is not axon polarity; this package treats graphs as undirected unless you have a genuine directed measurement (tracers, some functional models).

## Implementation notes

- NaNs in \(W\) become 0 (missing edge, not infinite weight).
- Non-square matrices are rejected.
- Isolated nodes get \(s_i=0\); they remain in the table so AI can be undefined (`L+R=0`) rather than silently dropped.
- Isolated from a bad LUT (wrong row order) looks like “low strength.” Always check LUT provenance before interpreting a clinical effect.

## Where it sits among BCT measures

```
Local, weighted, first-order
    degree / strength          ← this tool
    clustering (weighted)
Local, higher-order
    betweenness, closeness, PageRank
Mesoscale
    modules, participation, rich club
Global
    efficiency, small-world, assortativity
```

Full catalogue with formulas: [Graph theory beyond this tool](beyond.md). Primer: [Graph theory](graphs.md).

[^barrat2004]: Barrat A, Barthélemy M, Pastor-Satorras R, Vespignani A. The architecture of complex weighted networks. *PNAS*. 2004;101:3747–3752. [doi:10.1073/pnas.0400087101](https://doi.org/10.1073/pnas.0400087101)
[^opsahl2010]: Opsahl T, Agneessens F, Skvoretz J. Node centrality in weighted networks. *Soc Networks*. 2010;32:245–251.
[^rubinov2010]: Rubinov M, Sporns O. *NeuroImage*. 2010;52:1059–1069.
[^vdh2013]: van den Heuvel MP, Sporns O. Network hubs in the human brain. *Trends Cogn Sci*. 2013;17:683–696.
[^jones2013]: Jones DK, Knösche TR, Turner R. *NeuroImage*. 2013;73:239–254.
[^maierhein2017]: Maier-Hein KH et al. *Nat Commun*. 2017;8:1349.
