# Outputs

All analysis outputs are tabular (CSV) plus optional PDF/PNG. Nothing is written into the BIDS raw tree.

## `dkt-ai-cohort`

```
<out>/
  manifest.json
  README.md
  strength/
    per_subject/
      sub-XXX_strength.csv
      sub-XXX_ai.csv
      sub-XXX_strength_intra.csv
      sub-XXX_ai_intra.csv
      sub-XXX_strength_inter.csv
      sub-XXX_ai_inter.csv
    node_strength_cohort.csv
    asymmetry_index_cohort.csv
    node_strength_intra_cohort.csv
    asymmetry_index_intra_cohort.csv
    node_strength_inter_cohort.csv
    asymmetry_index_inter_cohort.csv
    cohort_summary.csv
    cohort_intra_summary.csv
    cohort_inter_summary.csv
  volume/                         # --with-volume-ai
    per_subject/
      sub-XXX_volume.csv
      sub-XXX_volume_ai.csv
    node_volume_cohort.csv
    volume_asymmetry_index_cohort.csv
    cohort_volume_summary.csv
  compare/                        # --with-volume-ai
    strength_vs_volume_ai.csv
  reports/                        # default on
    sub-XXX/report.pdf
    sub-XXX/figures/
```

`--participants` additionally writes research tables such as SOZ-aligned AI and normative strength z-scores (see `manifest.json`). Those research CSVs are **not** shown in the clinical PDF.

### Strength tables

| Column (typical) | Description |
|---|---|
| `subject` | Id |
| `name` / `roi_name` | Parcel |
| `side` | `L` / `R` / midline |
| `region_type` | cortex / subcortex |
| `strength` | \(\sum_j w_{ij}\) after undirected `strengths_und` |
| `strength_intra` | Same, contralateral edges zeroed |
| `strength_inter` | Opposite: only cross-hemisphere edges |

### AI tables

| Column | Description |
|---|---|
| `roi_name` | Homologous pair without L/R |
| `side_ai` | \((L - R) / (L + R)\) |
| `log_ai` | \(\ln(L / R)\) |
| `L_*`, `R_*` | The two values used |

Volume AI uses the same formulae on mm³ from `dk_nodes.mif`.

## `nodestrength inspect`

Human-readable stdout plus optional `--json` diagnostic (`READY` / `PARTIAL` / `NOTHING_FOUND`).

## `ingest-preprocessed` / `ingest-ideas`

A manifest or long-form cohort CSV (`subject`, paths, optional `group`). Feed it to `asymmetry` and `analyze`.

## `analyze`

One GLM table: Pillai’s trace, approximate F, df, p, partial η² per effect (within, between, mixed). These are the Python analogue of SPSS `GLM` multivariate tests in Piper et al. 2026. Exact SAS/SPSS numbers will not match to machine precision.

## What “success” looks like

- Matrix is square; 84×84 for `fs_default` DKT, or LUT length for Lausanne+THOMAS
- Global strength is finite and > 0
- Homologous pairs found (warnings list unpaired nodes)
- `side_ai` in \([-1, 1]\) except `log_ai`
- `manifest.json` lists warnings instead of dropping subjects silently
