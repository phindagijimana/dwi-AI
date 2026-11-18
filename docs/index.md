# nodestrength

**Node strength and hemispheric asymmetry analysis for diffusion MRI connectomes.**

`nodestrength` takes a square structural connectome (the output of tractography + `tck2connectome`) and computes:

1. Per-region **connectivity strength** (Brain Connectivity Toolbox `strengths_und`)
2. Left–right **asymmetry indices** (side, SOZ-aligned, log-ratio, intrahemispheric)
3. Optional **ROI volume** and volume AI
4. Optional **normative z-scores** and mixed-design GLMs
5. Optional one-page **clinical PDF** reports

It implements the analysis layer of Piper et al., *Epilepsia* (2026)[^piper2026], and is atlas-agnostic. Built-in grids are **Lausanne + THOMAS** (the paper) and MRtrix3 **`fs_default` Desikan–Killiany** (84 nodes).

This site is modelled on the layout of [QSIPrep](https://qsiprep.readthedocs.io/): installation, data, CLI, outputs, then the science. The **Science** section is a reading path for people new to networks, connectomics, and graph theory in neuroscience, with citations into the literature.

**Source:** [github.com/phindagijimana/dwi-AI](https://github.com/phindagijimana/dwi-AI)

## What it is — and is not

| This tool | Not this tool |
|---|---|
| Analysis of **already built** connectomes | A replacement for [QSIPrep](https://qsiprep.readthedocs.io/) / [QSIRecon](https://qsirecon.readthedocs.io/) |
| Weighted **node strength** + laterality | Full BCT catalogue (clustering, efficiency, modularity, …) |
| Structural (dMRI) graphs | fMRI functional connectivity pipelines |
| Applied network neuroscience | Abstract graph-theory theorems |

QSIPrep preprocesses dMRI; QSIRecon reconstructs FODs and connectomes; **nodestrength scores those connectomes**.

```mermaid
flowchart LR
  BIDS[BIDS dMRI] --> QSIPrep
  QSIPrep --> QSIRecon
  QSIRecon --> C[connectome.csv]
  C --> NS[nodestrength]
  NS --> S[strength + AI + reports]
```

## A minimal command

DK / DKT connectomes from QSIRecon `labelconvert` (one folder per subject, `dkt_connectome.csv`):

```bash
dkt-ai-cohort \
    --root /path/to/dkt_connectomes \
    --out  /path/to/node_strength_results \
    --with-volume-ai
```

IDEAS-style preprocessed archive:

```bash
nodestrength inspect /path/to/ideas_ii
nodestrength ingest-preprocessed --archive /path/to/archive --out cohort.csv
nodestrength asymmetry --cohort cohort.csv --out ai.csv
```

See [Running](usage.md) and the [command-line reference](cli.md).

## Start here if you are new to the science

1. [Why graphs for the brain](science/networks.md)
2. [Graph theory primer](science/graphs.md)
3. [Connectomics](science/connectomics.md)
4. [Node strength](science/strength.md) — the measure this package actually computes
5. [Literature guide](science/literature.md)

## Citation

If you use this analysis, cite the methods paper and BCT:

> Piper RJ, Feng X, Chari A, et al. Thalamocortical structural connectivity in children with focal epilepsy: A diffusion MRI, case–control study. *Epilepsia*. 2026;67(4):1901–1915. [doi:10.1002/epi.70099](https://doi.org/10.1002/epi.70099)

> Rubinov M, Sporns O. Complex network measures of brain connectivity: uses and interpretations. *NeuroImage*. 2010;52(3):1059–1069. [doi:10.1016/j.neuroimage.2009.10.003](https://doi.org/10.1016/j.neuroimage.2009.10.003)

Upstream reconstruction should also cite [MRtrix3](https://www.mrtrix.org/)[^tournier2019] and, if used, QSIPrep[^cieslak2021].

[^piper2026]: Piper RJ et al. *Epilepsia* 2026;67:1901–1915. [doi:10.1002/epi.70099](https://doi.org/10.1002/epi.70099)
[^tournier2019]: Tournier J-D et al. *NeuroImage* 2019;202:116137. [doi:10.1016/j.neuroimage.2019.116137](https://doi.org/10.1016/j.neuroimage.2019.116137)
[^cieslak2021]: Cieslak M et al. *Nature Methods* 2021;18:775–778. [doi:10.1038/s41592-021-01185-5](https://doi.org/10.1038/s41592-021-01185-5)
