# Node strength

**Node strength** is the weighted analogue of degree: the sum of edge weights incident on a node (Barrat et al. 2004[^barrat2004]; Rubinov & Sporns 2010[^rubinov2010]).

\[
s_i = \sum_{j \in V,\, j \neq i} w_{ij}
\]

For an undirected connectome we first replace \(W\) with \((W+W^\top)/2\) and set \(w_{ii}=0\). That is BCT `strengths_und`, and it is what `nodestrength compute-strength` prints.

## What it means biologically

If \(w_{ij}\) is a SIFT2-weighted streamline count, \(s_i\) is a reconstruction of **how much white-matter connection mass** parcel \(i\) participates in. It is **not**:

- the number of synapses
- a guarantee of a true anatomical projection (tractography false positives/negatives: Maier-Hein 2017[^maierhein2017])
- hubness by itself (a strong node may be a provincial hub or a rich-club hub; van den Heuvel & Sporns 2013[^vdh2013])

If \(w_{ij}\) is mean FA, \(s_i\) mixes **how many connections** with **how anisotropic those connections are** — a different construct, closer to a weighted microstructure load.

## Intrahemispheric strength

For laterality of a deep grey nucleus it is often desirable to ignore the contralateral hemisphere, so that a large callosal weight does not dominate. Mask \(w_{ij}=0\) when \(i\) and \(j\) are in opposite hemispheres, then recompute \(s_i\). Hippocampal IDEAS analyses in this repo use that mask. Whole-brain strength (used as a GAM covariate in Piper et al. 2026) does **not** mask.

## Normalisation

Raw \(s_i\) scales with:

- number of streamlines requested
- brain size / parcel volume
- reconstruction (det vs prob, SIFT vs not)

Common responses:

| Approach | Idea | Caveat |
|---|---|---|
| CountScaled | divide by volume or length | Which divisor? |
| Strength fraction | \(s_i / \sum_k s_k\) | Loses global hypoconnectivity |
| Covariate global strength | Piper 2026 GAM | Preferred when you care about residual regional effects |
| Consistency thresholding | Roberts, Perry, Roberts et al. / Buchanan | Changes topology |

Jones et al. 2013 warn against treating streamline count as axon count[^jones2013].

## Strength vs volume

Grey-matter volume of the same parcel is a **different** measurement (FreeSurfer / voxel count). Volume AI and strength AI can disagree: a small hippocampus can still be strongly wired, and vice versa. Report both when both exist (`--with-volume-ai`).

## Where it sits among BCT measures

```
Local, weighted, first-order
    degree / strength          ← this tool
    clustering (weighted)
Local, higher-order
    betweenness, closeness, PageRank
    matching index
Mesoscale
    modules, participation, rich club
Global
    efficiency, small-world σ, assortativity
```

See [Graph theory beyond this tool](beyond.md) for the rest of that list with citations.

## Implementation notes

- NaNs in \(W\) become 0 (missing edge, not infinite weight).
- Non-square matrices are rejected.
- Isolated nodes get \(s_i = 0\); they remain in the table so AI can be undefined (`L+R=0`) rather than silently dropped.

[^barrat2004]: Barrat A, Barthélemy M, Pastor-Satorras R, Vespignani A. The architecture of complex weighted networks. *PNAS*. 2004;101:3747–3752. [doi:10.1073/pnas.0400087101](https://doi.org/10.1073/pnas.0400087101)
[^rubinov2010]: Rubinov M, Sporns O. *NeuroImage*. 2010;52:1059–1069.
[^maierhein2017]: Maier-Hein KH et al. *Nat Commun*. 2017;8:1349.
[^vdh2013]: van den Heuvel MP, Sporns O. Network hubs in the human brain. *Trends Cogn Sci*. 2013;17:683–696.
[^jones2013]: Jones DK, Knösche TR, Turner R. *NeuroImage*. 2013;73:239–254.
