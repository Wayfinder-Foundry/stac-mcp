import json
from unittest.mock import MagicMock, patch


def test_get_queryables():
    """Verify get_queryables for a collection."""
    from stac_mcp.tools.client import STACClient

    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        response_json = {"queryables": {"prop1": {"type": "string"}}}
        mock_response.json.return_value = response_json
        mock_response.content = json.dumps(response_json).encode("utf-8")
        mock_get.return_value = mock_response

        client = STACClient("https://stac.example.com/")
        client._conformance = ["https://api.stacspec.org/v1.0.0/item-search#queryables"]  # noqa: SLF001
        queryables = client.get_queryables(collection_id="test-collection")

        assert "queryables" in queryables
        assert queryables["queryables"]["prop1"]["type"] == "string"
        mock_get.assert_called_once_with(
            "https://stac.example.com/collections/test-collection/queryables",
            headers={"Accept": "application/json"},
            timeout=30,
        )


def test_get_aggregations():
    """Verify get_aggregations with expanded search parameters."""
    from stac_mcp.tools.client import STACClient

    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        response_json = {
            "aggregations": [{"name": "prop1", "value": {"mean": 10}}],
            "meta": {"matched": 1},
        }
        mock_response.json.return_value = response_json
        mock_response.content = json.dumps(response_json).encode("utf-8")
        mock_post.return_value = mock_response

        client = STACClient("https://stac.example.com/")
        client._conformance = [  # noqa: SLF001
            "https://api.stacspec.org/v1.0.0/ogc-api-features-p3/conf/aggregation"
        ]
        aggregations = client.get_aggregations(
            collections=["test-collection"], fields=["prop1"]
        )

        assert "aggregations" in aggregations
        assert aggregations["aggregations"][0]["name"] == "prop1"
        assert "meta" in aggregations
        assert aggregations["meta"]["matched"] == 1

        expected_body = {
            "collections": ["test-collection"],
            "aggregations": [{"name": "prop1", "params": {}}],
        }
        mock_post.assert_called_once_with(
            "https://stac.example.com/search",
            json=expected_body,
            headers={"Accept": "application/json"},
            timeout=60,
        )
