# Containers

There are two different images you might meet. They are **not** interchangeable.

## Analysis image (usual)

Standalone Apptainer/Singularity image that runs **DK node strength**, AI, volume AI, and clinical PDFs — the same job as `dkt-ai-cohort`. No repo checkout or Python env required.

```
oras://index.docker.io/phindagijimana321/nodestrength:0.1.0
```

Canonical file: `nodestrength_0.1.0.sif`. Build from this repo with `bash containers/build.sh`. Details: [`containers/README.md`](https://github.com/phindagijimana/dwi-AI/blob/main/containers/README.md) in GitHub.

### Apptainer

```bash
SIF=/path/to/nodestrength_0.1.0.sif
CONNECT=/path/to/connectomes     # one folder per subject
OUT=/path/to/results
FS=/path/to/freesurfer/subjects  # optional

apptainer run --cleanenv \
  -B "$CONNECT:$CONNECT:ro" \
  -B "$OUT:$OUT" \
  ${FS:+-B "$FS:$FS:ro"} \
  "$SIF" \
  "$CONNECT" "$OUT" ${FS:+"$FS"}
```

Or copy `containers/run.sh` beside the `.sif`:

```bash
./run.sh /path/to/connectomes /path/to/results
./run.sh /path/to/connectomes /path/to/results /path/to/freesurfer/subjects
```

**Default:** strength + volume + compare + PDF. `--strength-only` or `--no-report` skip pieces.

Per-subject inputs: `dkt_connectome.csv` (required), `dk_nodes.mif` (volume AI).

## Reconstruction image (optional)

A heavier Docker image (`docker.io/phindagijimana321/nodestrength:latest` in some lab notes) based on MRtrix3 with FreeSurfer/FSL/ANTs is for **building** connectomes (`dwi2fod`, `tckgen`, SIFT2, `tck2connectome`). If QSIPrep + QSIRecon already produced matrices, you do not need it.

```bash
docker pull phindagijimana321/nodestrength:latest
docker run --rm -v /path/to/data:/data \
    phindagijimana321/nodestrength:latest recon --help
```

See [Pipeline details](pipeline.md) for the reconstruction recipe (Piper et al. 2026; MRtrix3[^tournier2019]).

## QSIPrep / QSIRecon instead

If your lab already runs [QSIPrep](https://qsiprep.readthedocs.io/) + [QSIRecon](https://qsirecon.readthedocs.io/), point `dkt-ai-cohort --root` at the connectome directory. That is the recommended path for new BIDS datasets.

[^tournier2019]: Tournier J-D, Smith R, Raffelt D, et al. MRtrix3: A fast, flexible and open software framework for medical image reconstruction and visualisation. *NeuroImage*. 2019;202:116137. [doi:10.1016/j.neuroimage.2019.116137](https://doi.org/10.1016/j.neuroimage.2019.116137)
