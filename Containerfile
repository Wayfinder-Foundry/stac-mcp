# Minimal debian-based image to leverage manylinux wheels (avoids GDAL mismatch)
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
        ca-certificates \
        gdal-bin \
        libgdal-dev \
        libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files (include README and LICENSE for packaging metadata)
COPY pyproject.toml ./
COPY README.md ./
COPY LICENSE ./
COPY stac_mcp ./stac_mcp

# Install uv (Astral) for ASGI server
RUN \
    curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Install dependencies and build the package
# RUN pip install .
RUN uv sync
RUN uv build
RUN pip install dist/stac_mcp-*.whl

# Set the entry point for the application.
# Use the console script declared in pyproject.toml ([project.scripts]),
# not `python -m stac_mcp.server` - server.py only defines the FastMCP app
# and registers tools, it has no `if __name__ == "__main__":` block, so
# running it as a script just imports it and exits cleanly (exit 0) without
# ever starting the server.
ENTRYPOINT ["stac-mcp"]