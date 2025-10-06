"""Tool for updating a STAC Collection."""

from __future__ import annotations

from typing import Any

from stac_mcp.tools.client import stac_client
from stac_mcp.tools.common import ToolInput


class UpdateCollection:
    """A tool for updating a STAC Collection."""

    description = "Update STAC Collection"

    @property
    def input_schema(self) -> type[ToolInput]:
        """The input schema for the tool."""

        class UpdateCollectionInput(ToolInput):
            """Input for updating a STAC Collection."""

            collection: dict[str, Any]

        return UpdateCollectionInput

    def run(self, **kwargs: Any) -> dict[str, Any] | str:
        """Run the tool."""
        return stac_client.update_collection(**kwargs)
