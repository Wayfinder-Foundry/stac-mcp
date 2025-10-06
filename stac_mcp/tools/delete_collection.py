"""Tool for deleting a STAC Collection."""

from __future__ import annotations

from typing import Any

from stac_mcp.tools.client import stac_client
from stac_mcp.tools.common import ToolInput


class DeleteCollection:
    """A tool for deleting a STAC Collection."""

    description = "Delete STAC Collection"

    @property
    def input_schema(self) -> type[ToolInput]:
        """The input schema for the tool."""

        class DeleteCollectionInput(ToolInput):
            """Input for deleting a STAC Collection."""

            collection_id: str

        return DeleteCollectionInput

    def run(self, **kwargs: Any) -> dict[str, Any] | str:
        """Run the tool."""
        return stac_client.delete_collection(**kwargs)
