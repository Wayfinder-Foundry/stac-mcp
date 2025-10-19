import pytest


@pytest.mark.asyncio
async def test_update_and_delete_item(stac_test_server, default_catalog_url):
    api_key = stac_test_server["api_key"]
    client = stac_test_server["client"]
    # ensure item exists
    async with client:
        result = await client.call_tool(
            "get_item",
            {
                "collection_id": "vancouver-subaoi-collection",
                "item_id": "test-create-1",
                "catalog_url": default_catalog_url,
            },
            raise_on_error=False,
        )
        if result.is_error:
            # create it first
            create_result = await client.call_tool(
                "create_item",
                {
                    "collection_id": "vancouver-subaoi-collection",
                    "item": {
                        "id": "test-create-1",
                        "type": "Feature",
                        "properties": {},
                    },
                    "api_key": api_key,
                    "catalog_url": default_catalog_url,
                },
            )
            assert create_result.is_error is False
        # update
        updated = {
            "id": "test-create-1",
            "type": "Feature",
            "properties": {"foo": "bar"},
            "collection": "vancouver-subaoi-collection",
        }
        result = await client.call_tool(
            "update_item",
            {
                "collection_id": "vancouver-subaoi-collection",
                "item": updated,
                "api_key": api_key,
                "catalog_url": default_catalog_url,
            },
        )
        assert result.is_error is False
        assert "test-create-1" in result.content[0].text
        # delete
        result = await client.call_tool(
            "delete_item",
            {
                "collection_id": "vancouver-subaoi-collection",
                "item_id": "test-create-1",
                "api_key": api_key,
                "catalog_url": default_catalog_url,
            },
        )
        assert result.is_error is False
        assert "test-create-1" in result.content[0].text
        # verify gone
        result = await client.call_tool(
            "get_item",
            {
                "collection_id": "vancouver-subaoi-collection",
                "item_id": "test-create-1",
                "catalog_url": default_catalog_url,
            },
            raise_on_error=False,
        )
        assert result.is_error is True
