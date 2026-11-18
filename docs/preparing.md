# Preparing data

`nodestrength` never sees raw DICOM. It consumes **square connectome matrices** plus an atlas that names the rows.

## Option A — QSIRecon Desikan–Killiany (recommended for DKT)

After QSIPrep + QSIRecon `mrtrix_multishell_msmt_ACT-hsvs` (or equivalent `tck2connectome` with `labelconvert` to `fs_default.txt`), one folder per subject:

```
<dkt_root>/
  sub-001/dkt_connectome.csv      # 84 × 84 SIFT2, no header
  sub-001/dk_nodes.mif            # optional, volume AI
  sub-002/dkt_connectome.csv
  ...
```

Legacy names `dk_connectome.csv` and `connectome.csv` are still discovered.

```bash
dkt-ai-cohort --root <dkt_root> --out results/ --with-volume-ai
```

The 84-node `fs_default` order is FreeSurfer’s default lookup (cortical DK + subcortical, both hemispheres). `nodestrength` pairs homologous left/right labels automatically. Whole thalamus is `Thalamus-Proper` — DK does **not** split THOMAS nuclei.

!!! note "Connectome weights"
    Piper et al. used SIFT2-weighted streamline counts. QSIRecon can write `count`, `sift2`, `mean_length`, or FA-weighted matrices. **Do not mix weights** in one cohort. See [Connectomics](science/connectomics.md) for why Count vs MeanFA vs Length are different graphs.

## Option B — Lausanne 2008 (IDEAS / MICA-MICs)

IDEAS-style `networks/` trees store, per subject and scale:

- `*_connectome_scale250_Count.csv`
- `*_connectome_scale250_CountScaled.csv`
- `*_connectome_scale250_MeanFA.csv`
- `*_connectome_scale250_MD.csv`
- `*_connectome_scale250_Length.csv`

and the same for scales 33/36, 60, 125. Node **order** is LUT order (GraphML → connectome), **not** FreeSurfer `FreeSurferColorLUT.txt` order. That LUT is documented in [Pipeline details](pipeline.md).

Ingest:

```bash
nodestrength ingest-preprocessed --archive /path/to/networks --out cohort.csv
nodestrength inspect /path/to/networks
```

## Option C — Single subject, any atlas

```bash
nodestrength run-subject \
    --connectome sub-001_connectome.csv \
    --atlas lthomascort \
    --out-dir sub-001_out
```

`--atlas` chooses the built-in pairing table (`lthomascort` or `fs_default`). Custom atlases: pass a pairing CSV (`left_label,right_label`).

## Clinical covariates (optional)

For SOZ-aligned AI, epilepsy vs control grouping, and ROC:

| Column | Meaning |
|---|---|
| `subject` | BIDS id |
| `group` | `control` / `epilepsy` / `HS` / … |
| `soz_side` | `L` / `R` / `bilateral` / empty |
| `age`, `sex` | for GAM covariates |
| `motion` | e.g. mean FD |
| `isControl` | 1/0 for ROC against patients |

## What not to feed the CLI

- Unsymmetric “upper triangle only” matrices (the code expects a full square array; undirected graphs are symmetrised internally)
- Matrices whose row order does not match the atlas labels
- Mix of deterministic and probabilistic Count matrices in one ROC table without labelling the reconstruction
