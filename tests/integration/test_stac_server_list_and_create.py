def test_list_items_empty_or_present(stac_test_server):
    client = stac_test_server["client"]
    rv = client.get("/collections/vancouver-subaoi-collection/items")
    assert rv.status_code == 200
    body = rv.json()
    assert body.get("type") == "FeatureCollection"


def test_create_items_feature_collection(stac_test_server):
    client = stac_test_server["client"]
    api_key = stac_test_server["api_key"]
    # create a minimal feature collection with one generated item
    fc = {"type": "FeatureCollection", "features": [{"id": "test-create-1", "type": "Feature", "properties": {}}]}
    rv = client.post(
        "/collections/vancouver-subaoi-collection/items",
        json=fc,
        headers={"X-API-Key": api_key},
    )
    assert rv.status_code in (200, 201)
    body = rv.json()
    assert "created" in body or body.get("id") == "test-create-1"


def test_get_created_item(stac_test_server):
    client = stac_test_server["client"]
    # the previous test should have created test-create-1
    rv = client.get("/collections/vancouver-subaoi-collection/items/test-create-1")
    assert rv.status_code == 200
    item = rv.json()
    assert item.get("id") == "test-create-1"
