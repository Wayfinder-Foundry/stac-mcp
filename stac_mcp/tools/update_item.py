"""Tool for updating a STAC Item."""

from __future__ import annotations

from typing import Any

from stac_mcp.tools.client import stac_client
from stac_mcp.tools.common import ToolInput


class UpdateItem:
    """A tool for updating a STAC Item."""

    description = "Update STAC Item"

    @property
    def input_schema(self) -> type[ToolInput]:
        """The input schema for the tool."""

        class UpdateItemInput(ToolInput):
            """Input for updating a STAC Item."""

            item: dict[str, Any]

        return UpdateItemInput

    def run(self, **kwargs: Any) -> dict[str, Any] | str:
        """Run the tool."""
        return stac_client.update_item(**kwargs)
