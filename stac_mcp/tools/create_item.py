"""Tool for creating a STAC Item."""

from __future__ import annotations

from typing import Any

from stac_mcp.tools.client import stac_client
from stac_mcp.tools.common import ToolInput


class CreateItem:
    """A tool for creating a STAC Item."""

    description = "Create STAC Item"

    @property
    def input_schema(self) -> type[ToolInput]:
        """The input schema for the tool."""

        class CreateItemInput(ToolInput):
            """Input for creating a STAC Item."""

            collection_id: str
            item: dict[str, Any]

        return CreateItemInput

    def run(self, **kwargs: Any) -> dict[str, Any] | str:
        """Run the tool."""
        return stac_client.create_item(**kwargs)
