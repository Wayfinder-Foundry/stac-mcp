# Multi-stage build for security and minimal size
# Stage 1: Builder stage with full Python environment
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml ./
COPY stac_mcp ./stac_mcp

# Install dependencies and build the package
RUN pip install --upgrade pip setuptools wheel \
    && pip install .

# Set the entry point for the application
ENTRYPOINT ["python", "-m", "stac_mcp.server"]
CMD ["--help"]