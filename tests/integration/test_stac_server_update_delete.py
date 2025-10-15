def test_update_and_delete_item(stac_test_server):
    client = stac_test_server["client"]
    api_key = stac_test_server["api_key"]
    # ensure item exists
    rv = client.get("/collections/vancouver-subaoi-collection/items/test-create-1")
    if rv.status_code != 200:  # noqa: PLR2004
        # create it first
        client.post(
            "/collections/vancouver-subaoi-collection/items",
            json={"id": "test-create-1", "type": "Feature", "properties": {}},
            headers={"X-API-Key": api_key},
        )
    # update
    updated = {"id": "test-create-1", "type": "Feature", "properties": {"foo": "bar"}}
    rv = client.put(
        "/collections/vancouver-subaoi-collection/items/test-create-1",
        json=updated,
        headers={"X-API-Key": api_key},
    )
    assert rv.status_code == 200  # noqa: PLR2004
    assert rv.json().get("updated") == "test-create-1"
    # delete
    rv = client.delete(
        "/collections/vancouver-subaoi-collection/items/test-create-1",
        headers={"X-API-Key": api_key},
    )
    assert rv.status_code == 200  # noqa: PLR2004
    assert rv.json().get("deleted") == "test-create-1"
    # verify gone
    rv = client.get("/collections/vancouver-subaoi-collection/items/test-create-1")
    assert rv.status_code == 404  # noqa: PLR2004
