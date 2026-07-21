# Brain Connectivity Toolbox (BCT) — reference for this project

This document explains what the **Brain Connectivity Toolbox** is, how its
graph-theoretic measures work, and **exactly how `nodestrength` uses BCT** to
compute node strength from diffusion connectomes.

Related docs: [`paper.md`](paper.md) (Piper et al. 2026), [`nodestrength.md`](nodestrength.md) §4 Stage 2 and §12, [`node.md`](node.md) (implementation notes).

---

## 1. What is BCT?

The **Brain Connectivity Toolbox (BCT)** is a widely used library for computing
**graph-theoretic metrics** on brain networks represented as adjacency matrices.
It was introduced by Rubinov and Sporns and is standard in structural and
functional connectivity research.

| Resource | URL |
|----------|-----|
| Original paper | Rubinov M, Sporns O. *Complex network measures of brain connectivity: uses and interpretations.* **NeuroImage** 2010;52(3):1059–1069 |
| BCT website | https://sites.google.com/site/bctnet |
| MATLAB toolbox | Download from BCT website |
| Python port (`bctpy`) | https://github.com/aestrivex/bctpy |

**In one line:** BCT turns a connectome matrix into summary statistics — how
connected is each region, how clustered is the network, how efficient are paths,
and so on.

---

## 2. Brain networks as graphs

A connectome is a **graph**:

| Graph term | Brain mapping |
|------------|---------------|
| **Node (vertex)** | Brain region / ROI (e.g. DK node, thalamic nucleus) |
| **Edge** | Structural or functional link between two regions |
| **Weight** | Connection strength (here: SIFT2-weighted streamline count) |
| **Adjacency matrix `W` or `CIJ`** | N×N matrix; entry `W[i,j]` = weight from node i to node j |

### Conventions in this project

| Property | Our connectomes |
|----------|-----------------|
| **Weighted** | Yes — SIFT2 streamline counts (not just 0/1) |
| **Undirected** | Yes — `tck2connectome -symmetric`; we symmetrise on load if needed |
| **Self-loops** | No — `-zero_diagonal`; diagonal excluded from strength sums |
| **Sign** | Non-negative weights |

---

## 3. Node strength — the measure we use

### Definition

For an **undirected weighted** network, the **node strength** of node `i` is the
sum of weights on all edges incident to `i`:

```
    s_i = Σ_j W_ij
```

If the diagonal is zero (no self-connection), this equals the row sum (or column
sum, since `W` is symmetric):

```
    s_i = Σ_{j ≠ i} W_ij
```

**Interpretation:** Total “connection mass” reaching node `i` from the rest of
the network. Higher strength = more streamline-weighted connectivity between
that ROI and all other ROIs.

In Piper et al. 2026 this is called **connectivity strength** — the primary
per-ROI scalar analysed after normative z-scoring ([`paper.md`](paper.md)).

### BCT function: `strengths_und`

| Item | Detail |
|------|--------|
| **Name** | `strengths_und` — strengths, **und**irected |
| **Input** | N×N weighted adjacency matrix `CIJ` |
| **Output** | Length-N vector; `s[i]` = strength of node `i` |
| **Implementation** | `sum(CIJ, axis=0)` in MATLAB/Python (row sum) |

This is the **only BCT function required** for the Gugger Lab DK cohort runner
(`scripts/run_dk_ai_cohort.py`). All 84 DK node strengths come from one call.

### Worked example (3 nodes)

```
W = [  0   2   1 ]
     [  2   0   3 ]
     [  1   3   0 ]

strengths_und(W) = [3, 5, 4]
```

Node 0: edges to 1 and 2 → 2 + 1 = 3. Node 1: 2 + 3 = 5. Node 2: 1 + 3 = 4.

---

## 4. Piper paper: masking before summation

For **thalamic nuclei** (Lausanne + THOMAS path), Piper et al. sum SIFT2 weights
with two exclusions ([`nodestrength/connectome.py`](nodestrength/connectome.py)):

1. **Self-connections** — diagonal zeroed (standard).
2. **Inter-thalamic edges** — drop connections between thalamic nuclei (Figure 2
   caption: “Discounting the inter-thalamic nuclei connections…”).

Implementation: build a boolean **keep mask**, zero excluded edges, then call
`strengths_und` on the masked matrix:

```python
from nodestrength.connectome import StrengthConfig, compute_nucleus_strength

cfg = StrengthConfig(exclude_self=True, exclude_inter_thalamic=True)
strengths = compute_nucleus_strength(W, node_lookup, config=cfg)
```

### DK cohort (Gugger Lab)

`run_dk_ai_cohort.py` applies **`strengths_und` to the full 84×84 matrix** with
no inter-thalamic mask (DK has one thalamus node per hemisphere, not THOMAS
subnuclei). Diagonal is already zero from `tck2connectome`.

---

## 5. Other BCT measures (overview)

BCT implements dozens of metrics. **This project does not compute them by
default**, but they are available in the full toolbox for extensions:

### Local (nodewise) measures

| Measure | BCT function (typical) | Meaning |
|---------|------------------------|---------|
| **Degree** | `degrees_und` | Count of non-zero edges (binary or thresholded) |
| **Strength** | `strengths_und` | **Sum of edge weights** ← *we use this* |
| **Clustering coefficient** | `clustering_coef_wu` | How tightly a node's neighbours connect to each other |
| **Local efficiency** | `efficiency_wei` (local) | Robustness of local subgraph communication |
| **Participation coefficient** | `participation_coef` | How evenly a node splits between modules |
| **Within-module degree z-score** | `module_degree_zscore` | Hub-ness within a community |

### Global (network-wide) measures

| Measure | BCT function (typical) | Meaning |
|---------|------------------------|---------|
| **Global efficiency** | `efficiency_wei` | Average inverse shortest path length |
| **Characteristic path length** | `distance_wei` + path stats | Typical steps between nodes |
| **Modularity** | `modularity_und` | Community structure strength |
| **Small-worldness** | Compare to random null | σ, clustering vs random graph |
| **Rich-club coefficient** | `rich_club_wu` | High-degree nodes preferentially connect |

### Binary vs weighted

| Type | When to use |
|------|-------------|
| **Weighted (`*_wu`, `*_und` with weights)** | Streamline counts, correlation magnitudes — **our case** |
| **Binary (`*_bu`, thresholded)** | Presence/absence of connection above a threshold |

Thresholding discards weight information; Piper et al. keep SIFT2 weights, so
**weighted strength** is appropriate.

### Directed vs undirected

| Type | BCT suffix | Notes |
|------|------------|-------|
| Undirected | `_und`, `_wu` | One strength per node — **our connectomes** |
| Directed | `_dir`, `_wd` | Separate in-strength and out-strength |

MRtrix `-symmetric` connectomes are treated as undirected.

---

## 6. How `nodestrength` uses BCT

### Python backend: `bctpy`

```bash
pip install -e .[bct]    # installs bctpy>=0.5
```

| Code path | Behaviour |
|-----------|-----------|
| `bctpy` installed | `nodestrength.connectome._strengths_und` → `bct.strengths_und(W)` |
| `bctpy` missing | Fallback `W.sum(axis=0)` — **bit-identical** for non-negative symmetric `W` |

Check at runtime:

```python
from nodestrength.connectome import uses_bctpy
print(uses_bctpy())   # True if bctpy active
```

`manifest.json` in `node_strength_results/` records `"bct_backend": true/false`.

### Code reference

```35:44:nodestrength/connectome.py
def _strengths_und(W: np.ndarray) -> np.ndarray:
    """Undirected weighted node strength.

    Identical to BCT's ``strengths_und`` (which is ``np.sum(CIJ, axis=0)``).
    Uses ``bctpy`` if installed (auditable to the canonical source), otherwise
    the equivalent pure-numpy expression. Returns a 1-D array of length N.
    """
    if _HAS_BCT:
        return np.asarray(_bct.strengths_und(W))
    return W.sum(axis=0)
```

### Outputs that use BCT strength

| Output | BCT usage |
|--------|-----------|
| `strength/per_subject/sub-XXX_strength.csv` | `strengths_und` on full DK connectome |
| `strength/per_subject/sub-XXX_ai.csv` | AI formulas on L/R strength pairs (not a BCT function) |
| `strength/node_strength_cohort.csv` | Cohort stack of strength tables |
| `volume/per_subject/sub-XXX_volume.csv` | Not BCT — voxel counts from `dk_nodes.mif` |
| `compare/strength_vs_volume_ai.csv` | Merged strength AI + volume AI (not a BCT function) |
| THOMAS / IDEAS path | `compute_nucleus_strength` with optional inter-thalamic mask |

**Folder layout:** strength outputs under `strength/`; volume under `volume/`;
cross-modality under `compare/` (see [`nodestrength.md`](nodestrength.md) §11.2).

See [`nodestrength.md`](nodestrength.md) §12 for CSV column definitions and sources.

---

## 7. Validation in this repo

| Test | File | What it checks |
|------|------|----------------|
| BCT parity | `tests/test_connectome.py` | `_strengths_und(W) == bct.strengths_und(W)` when bctpy installed |
| Manual row sum | `tests/test_connectome.py` | Strength matches hand-computed masked sum |
| Inter-thalamic mask | `tests/test_connectome.py` | Excluding thalamic–thalamic edges reduces strength |
| End-to-end DK | `tests/test_dk_atlas.py` | 84-node ordering and L/R pairing |

Run: `pytest tests/test_connectome.py -q`

---

## 8. Common questions

**Q: Is node strength the same as degree?**
A: No. **Degree** counts edges (often binary). **Strength** sums **weights**.
A hub with few heavy connections can have low degree but high strength.

**Q: Why use BCT if it is just a row sum?**
A: For undirected weighted graphs, `strengths_und` *is* the row sum — BCT
provides the **named, citable, standard definition** Piper et al. reference.
Using `bctpy` makes the audit trail match the paper and the broader connectivity
literature.

**Q: Can we use other BCT metrics on our connectomes?**
A: Yes — load `W` with `load_connectome`, then call any `bctpy` function. Future
extensions (modularity, rich-club, edge-wise stats) are not in the default
pipeline but are compatible with the same matrices.

**Q: Does BCT compute asymmetry index?**
A: No. BCT produces nodewise metrics. **Interhemispheric AI** `(L−R)/(L+R)` is
computed in `nodestrength.asymmetry` *after* strength is extracted.

---

## 9. References

- Rubinov M, Sporns O. *Complex network measures of brain connectivity: uses and interpretations.* NeuroImage 2010;52(3):1059–1069.
- Rubinov M, Sporns O. Brain Connectivity Toolbox. https://sites.google.com/site/bctnet
- Faivre A et al. `bctpy` — Python port. https://github.com/aestrivex/bctpy
- Piper RJ et al. Application of BCT strength to thalamic nuclei. *Epilepsia* 2026 — [`paper.md`](paper.md)
- Tournier J-D et al. MRtrix3 connectome construction. *NeuroImage* 2019
