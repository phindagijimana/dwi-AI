# Analysis layer: node strength + interhemispheric AI + volume AI (default).
# Mount host paths to dk_connectomes/ and node_strength_results/ at run time.
#
# Volume AI uses dk_nodes.mif on the tractography grid (pure Python .mif reader).
#
# Build:
#   docker build -t dwi-ai-analysis:latest .
#
# Run (strength + volume + compare/):
#   docker run --rm \
#     -v /mnt/nfs/Gugger_Lab/NIR/dwi_test2/dk_connectomes:/data/connectomes:ro \
#     -v /mnt/nfs/Gugger_Lab/NIR/dwi_test2/node_strength_results:/data/out \
#     dwi-ai-analysis:latest \
#     --root /data/connectomes --out /data/out
#
# Strength only (skip volume/ and compare/):
#     ... dwi-ai-analysis:latest --root ... --out ... --strength-only

FROM python:3.11-slim-bookworm

LABEL org.opencontainers.image.title="nodestrength"
LABEL org.opencontainers.image.description="DK node strength + strength AI + volume AI (standalone analysis container)"
LABEL org.opencontainers.image.source="https://github.com/phindagijimana/dwi-AI"
LABEL org.opencontainers.image.version="0.1.0"

ENV NODESTRENGTH_VERSION=0.1.0 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install package + BCT backend + CLI entry point.
COPY pyproject.toml node.md README.md ./
COPY nodestrength/ nodestrength/
RUN pip install --upgrade pip && pip install -e ".[bct]"

COPY scripts/ scripts/
COPY containers/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY BCT.md paper.md nodestrength.md other_analysis.md ./
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Default: strength + volume AI + compare/ (use --strength-only to skip volume).
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["--help"]
