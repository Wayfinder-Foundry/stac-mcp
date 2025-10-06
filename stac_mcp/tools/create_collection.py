"""Tool for creating a STAC Collection."""

from __future__ import annotations

from typing import Any

from stac_mcp.tools.client import stac_client
from stac_mcp.tools.common import ToolInput


class CreateCollection:
    """A tool for creating a STAC Collection."""

    description = "Create STAC Collection"

    @property
    def input_schema(self) -> type[ToolInput]:
        """The input schema for the tool."""

        class CreateCollectionInput(ToolInput):
            """Input for creating a STAC Collection."""

            collection: dict[str, Any]

        return CreateCollectionInput

    def run(self, **kwargs: Any) -> dict[str, Any] | str:
        """Run the tool."""
        return stac_client.create_collection(**kwargs)
