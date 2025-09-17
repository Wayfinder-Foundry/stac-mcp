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
COPY stac_mcp/ ./stac_mcp/

# Install the package and dependencies to a local directory
RUN pip install --no-cache-dir --user .

# Stage 2: Final runtime stage using distroless
FROM gcr.io/distroless/python3-debian12:latest

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application source code
WORKDIR /app
COPY stac_mcp/ ./stac_mcp/

# Set environment variables for Python path
ENV PATH="/root/.local/bin:${PATH}"
ENV PYTHONPATH="/root/.local/lib/python3.12/site-packages:/app"

# Use non-root user for security (distroless provides 'nonroot' user)
USER nonroot

# Expose no ports (MCP uses stdio transport)
# Set the entrypoint to run the STAC MCP server
ENTRYPOINT ["python", "-m", "stac_mcp.server"]
CMD []