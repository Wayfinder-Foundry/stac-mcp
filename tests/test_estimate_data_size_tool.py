from stac_mcp.tools import MAX_ASSET_LIST
from stac_mcp.tools.estimate_data_size import handle_estimate_data_size


class FakeClient:
    def estimate_data_size(self, **kwargs):  # noqa: ARG002
        # craft a detailed estimate covering many optional fields
        assets = [
            {"asset": f"a{i}", "estimated_size_mb": 1.5, "media_type": "image/tiff"}
            for i in range(MAX_ASSET_LIST + 2)
        ]
        return {
            "item_count": 3,
            "estimated_size_bytes": 3145728,
            "estimated_size_mb": 3.0,
            "estimated_size_gb": 0.0029,
            "bbox_used": [0.0, 0.0, 1.0, 1.0],
            "temporal_extent": "2020-01-01/2020-01-02",
            "collections": ["c1", "c2"],
            "clipped_to_aoi": True,
            "data_variables": [
                {"variable": "v1", "size_mb": 1.5, "shape": [10, 10], "dtype": "uint16"}
            ],
            "spatial_dims": {"x": 10, "y": 20},
            "assets_analyzed": assets,
            "message": "Success",
        }


def test_handle_estimate_data_size_text():
    client = FakeClient()
    arguments = {"collections": ["c1"], "output_format": "text"}
    res = handle_estimate_data_size(client, arguments)
    assert isinstance(res, list)
    text = res[0].text
    assert "Items analyzed: 3" in text
    assert "Clipped to AOI: Yes" in text
    assert "Data Variables" in text
    assert "Assets Analyzed" in text
    # ensure the "... and N more assets" branch triggers
    assert "... and" in text


def test_handle_estimate_data_size_json():
    client = FakeClient()
    arguments = {"collections": ["c1"], "output_format": "json"}
    res = handle_estimate_data_size(client, arguments)
    assert isinstance(res, dict)
    assert res["type"] == "data_size_estimate"
    assert "estimate" in res
