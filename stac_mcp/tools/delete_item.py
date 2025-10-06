"""Tool for deleting a STAC Item."""

from __future__ import annotations

from typing import Any

from stac_mcp.tools.client import stac_client
from stac_mcp.tools.common import ToolInput


class DeleteItem:
    """A tool for deleting a STAC Item."""

    description = "Delete STAC Item"

    @property
    def input_schema(self) -> type[ToolInput]:
        """The input schema for the tool."""

        class DeleteItemInput(ToolInput):
            """Input for deleting a STAC Item."""

            collection_id: str
            item_id: str

        return DeleteItemInput

    def run(self, **kwargs: Any) -> dict[str, Any] | str:
        """Run the tool."""
        return stac_client.delete_item(**kwargs)