#!/bin/bash
set -e

echo "🔧 Setting up STAC MCP development environment..."

# Install system dependencies required for GDAL/rasterio
echo "📦 Installing GDAL and PROJ system libraries..."
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    libproj-dev \
    build-essential \
    ca-certificates \
    curl

# Clean up apt cache
sudo rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, and wheel
echo "⬆️  Upgrading pip, setuptools, and wheel..."
python -m pip install --upgrade pip setuptools wheel

# Install the package in development mode with dev dependencies
echo "📚 Installing stac-mcp in development mode..."
pip install -e ".[dev]"

# Install additional useful development tools
echo "🛠️  Installing additional development tools..."
pip install ipython coverage

# Configure git (if not already configured)
if [ -z "$(git config --global user.email)" ]; then
    echo "⚙️  Configuring git..."
    git config --global user.email "codespace@github.com"
    git config --global user.name "GitHub Codespace"
fi

# Set up pre-commit hooks (optional but recommended)
echo "🪝 Setting up git configuration..."
git config --local core.autocrlf input

# Create zsh history file if it doesn't exist
touch /home/vscode/.zsh_history

# Display project information
echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Project Information:"
echo "  - Python version: $(python --version)"
echo "  - Project: stac-mcp"
echo "  - Repository: Wayfinder-Foundry/stac-mcp"
echo ""
echo "🧪 Quick Start Commands:"
echo "  - Run tests:          pytest -v"
echo "  - Format code:        black stac_mcp/ tests/ examples/"
echo "  - Lint code:          ruff check stac_mcp/ tests/ examples/"
echo "  - Run server:         stac-mcp"
echo "  - Test server:        python examples/example_usage.py"
echo "  - Coverage report:    coverage run -m pytest -q && coverage report -m"
echo ""
echo "📚 Documentation:"
echo "  - README.md:          Main documentation"
echo "  - AGENTS.md:          Contributor guide"
echo "  - architecture/:      Architecture Decision Records"
echo ""
echo "🔗 Useful Links:"
echo "  - STAC Spec:          https://stacspec.org/"
echo "  - MCP Protocol:       https://modelcontextprotocol.io/"
echo ""
