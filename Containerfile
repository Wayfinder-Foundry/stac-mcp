# Minimal debian-based image to leverage manylinux wheels (avoids GDAL mismatch)
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
        gdal-bin \
        libgdal-dev \
        libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files (include README and LICENSE for packaging metadata)
COPY pyproject.toml ./
COPY README.md ./
COPY LICENSE ./
COPY stac_mcp ./stac_mcp

# Install dependencies and build the package
RUN pip install --upgrade pip wheel hatchling \
    && pip install .

# Set the entry point for the application
ENTRYPOINT ["python", "-m", "stac_mcp.server"]
CMD ["--help"]