# Command-line reference

Installed scripts: **`nodestrength`**, **`dkt-ai-cohort`**, and alias **`dk-ai-cohort`**.

This page is the QSIPrep-style flag list. Conceptual walkthrough: [Running](usage.md).

## `nodestrength`

```text
nodestrength [-h]
    {run-subject,compute-strength,fit-normative,analyze,
     ingest-ideas,ingest-preprocessed,inspect,asymmetry}
    ...
```

```text
-h, --help     show this help message and exit
```

### `run-subject`

Full FreeSurfer / THOMAS / MRtrix3 reconstruction **plus** analysis for one subject. Requires the reconstruction stack on `PATH` (or the container). For connectomes you already have, use `dkt-ai-cohort` or `compute-strength` instead.

```text
nodestrength run-subject SUBJECT_ID \
    --t1 PATH --dwi PATH --bvec PATH --bval PATH \
    --rpe-b0 PATH \
    --subjects-dir DIR \
    --out-dir DIR \
    [--dry-run]
```

| Flag | Required | Meaning |
|---|---|---|
| `SUBJECT_ID` | yes | FreeSurfer / BIDS id |
| `--t1` | yes | T1w NIfTI |
| `--dwi`, `--bvec`, `--bval` | yes | dMRI |
| `--rpe-b0` | yes | Reverse-phase-encode b0 |
| `--subjects-dir` | yes | `SUBJECTS_DIR` |
| `--out-dir` | yes | Derivatives |
| `--dry-run` | no | Print planned steps only |

### `compute-strength`

Per-nucleus strength and volume from an already-built connectome and a Lausanne+THOMAS lookup.

```text
nodestrength compute-strength \
    --subject-id ID \
    --connectome PATH \
    --lookup PATH \
    --labels PATH \
    --out PATH
```

| Flag | Meaning |
|---|---|
| `--connectome` | Square MRtrix3 connectome CSV |
| `--lookup` | Node-lookup table (row order of the matrix) |
| `--labels` | Merged Lausanne+THOMAS label NIfTI (volumes) |
| `--out` | Output CSV |

The matrix is loaded as a square numeric array; undirected strength is BCT `strengths_und` (via `bctpy` if installed).

### `fit-normative`

Fit per-(nucleus, side) OLS models on a **control** long-form cohort and pickle them (Piper et al. 2026 covariates: age, sex, mean ROI strength, motion; volume models use ICV).

```text
nodestrength fit-normative --controls PATH --out PATH.pkl
```

### `analyze`

Mixed-design GLM: Pillai’s trace and partial η² (`nodestrength.stats`).

```text
nodestrength analyze \
    --cohort PATH \
    --within nucleus side \
    --between group \
    --value strength \
    --out glm.csv \
    [--subject-col subject]
```

| Flag | Default | Meaning |
|---|---|---|
| `--cohort` | required | Long-form table |
| `--within` | required | One or more within-subject factors |
| `--between` | required | One or more between-subject factors |
| `--value` | required | Outcome column |
| `--subject-col` | `subject` | Subject id column |
| `--out` | required | Result CSV |

### `ingest-ideas`

Walk an IDEAS **raw BIDS** root and write a subject manifest.

```text
nodestrength ingest-ideas --bids DIR --out PATH [--participants TSV] [--include ID ...]
```

### `ingest-preprocessed`

Build a long-form cohort from an IDEAS II **pre-processed** archive (skips recon-all / THOMAS / MRtrix3).

```text
nodestrength ingest-preprocessed \
    --archive DIR \
    --out PATH \
    [--participants TSV] \
    [--include ID ...]
```

### `inspect`

Readiness probe: raw BIDS, pre-processed archive, or a mixed tree.

```text
nodestrength inspect PATH [--json PATH]
```

Prints subjects found, ROI-name sanity, `participants.tsv` column map, and a single verdict: `READY` / `PARTIAL` / `NOTHING_FOUND`. Exit status is 0 only when the verdict starts with `READY`.

### `asymmetry`

Collapse a long-form cohort into per-(subject, nucleus) AI (side, SOZ-aligned, log).

```text
nodestrength asymmetry \
    --cohort PATH \
    --out PATH \
    [--value strength] \
    [--soz-side-col soz_side]
```

`--value` can be `strength` or `volume` (or any numeric column). `--soz-side-col` is `L`/`R` per patient.

There is **no** `nodestrength report` subcommand. Clinical PDFs are written by `dkt-ai-cohort` (on by default; `--no-report` to skip).

## `dkt-ai-cohort`

DK / DKT (MRtrix `fs_default` 84-node) cohort runner.

```text
dkt-ai-cohort --root DIR --out DIR
              [--fs-root DIR]
              [--include ID ...]
              [--with-volume-ai]
              [--report | --no-report]
              [--participants TSV]
              [--normative-model PATH.pkl]
              [--control-group control]
```

| Argument | Default | Meaning |
|---|---|---|
| `--root` | required | One folder per subject containing `dkt_connectome.csv` |
| `--out` | required | `node_strength_results` directory (created) |
| `--fs-root` | none | FreeSurfer `SUBJECTS_DIR` (find `dk_nodes.mif`) |
| `--include` | all | Restrict subject IDs (`sub-` prefix optional) |
| `--with-volume-ai` | off | Volumes from `dk_nodes.mif` + volume AI + `compare/` |
| `--report` | **on** | Clinical PDF + figure gallery |
| `--no-report` | off | Skip PDFs |
| `--participants` | none | `participants.tsv` (SOZ, group, covariates) |
| `--normative-model` | fit from controls | Pre-fitted DK strength OLS pickle |
| `--control-group` | `control` | Label of control rows in `--participants` |

Legacy filenames `dk_connectome.csv` and `connectome.csv` are still discovered. Exit status `2` if no subjects are found; `1` on unsupported matrix shape.

## Research helpers (not installed as scripts)

The `research/` tree in the git clone contains study-specific runners (Lausanne LUT extraction, IDEAS hippocampus AI/ROC). Those are **not** the public CLI.

## Environment

| Variable | Effect |
|---|---|
| `SUBJECTS_DIR` | FreeSurfer subjects (also pass `--fs-root` / `--subjects-dir`) |
| `MPLBACKEND` | Set to `Agg` on HPC without X11 when writing PDFs |
