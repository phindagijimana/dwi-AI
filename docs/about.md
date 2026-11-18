# About this project

**nodestrength** is a Python analysis layer for **already reconstructed** structural connectomes. It implements the node-strength and laterality design of Piper et al., *Epilepsia* (2026)[^piper2026], and is maintained by **Philbert Ndagijimana**.

- Author: Philbert Ndagijimana
- Contact: [phindagijimana@gmail.com](mailto:phindagijimana@gmail.com)
- Documentation: [phindagijimana.github.io/dwi-AI](https://phindagijimana.github.io/dwi-AI/)
- Source: [github.com/phindagijimana/dwi-AI](https://github.com/phindagijimana/dwi-AI)
- Container: `docker.io/phindagijimana321/nodestrength`

## Scientific claim of the software

Given a square weighted adjacency matrix and an atlas:

1. Compute undirected **node strength** (BCT `strengths_und`; Rubinov & Sporns 2010).
2. Pair homologous regions and compute **asymmetry indices**.
3. Optionally residualise against a control GAM and run mixed-design GLMs.

It does not claim a new graph-theoretic invariant. It claims a **reproducible implementation** of a published epilepsy connectomics analysis, plus a documented CLI.

## Relation to QSIPrep

This documentation site is organised like [QSIPrep’s](https://qsiprep.readthedocs.io/) (install → prepare data → run → CLI → outputs → pipeline) because that is how neuroimaging users already read tools. **nodestrength is not QSIPrep.** QSIPrep preprocesses dMRI (Cieslak et al. 2021); this package scores connectomes.

## Relation to IDEAS / Lausanne analyses

Research scripts under `research/` in the GitHub repository apply the same strength+AI maths to IDEAS I/II Lausanne connectomes (hippocampus, scales 36–250, Count/FA/Length, det vs prob). Those scripts are study-specific. They are not the public CLI. Do not commit identified clinical tables to the public repo.

## Licence and citation

MIT licence (see `LICENSE` in the repository).

Cite the software as **Ndagijimana P., 2026** (contact [phindagijimana@gmail.com](mailto:phindagijimana@gmail.com)), plus Piper et al. 2026 and Rubinov & Sporns 2010; cite MRtrix3 / QSIPrep / the atlas when those were used. Ready-to-paste APA, BibTeX, and `CITATION.cff`: [Citing and contact](citing.md). See also [Literature](science/literature.md) §8.

[^piper2026]: Piper RJ, Feng X, Chari A, Owen TW, Assendorp N, Brkic M, et al. Thalamocortical structural connectivity in children with focal epilepsy: A diffusion MRI, case–control study. *Epilepsia*. 2026;67(4):1901–1915. [doi:10.1002/epi.70099](https://doi.org/10.1002/epi.70099)
