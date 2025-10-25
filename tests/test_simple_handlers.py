from stac_mcp.tools.get_conformance import handle_get_conformance
from stac_mcp.tools.get_item import handle_get_item
from stac_mcp.tools.get_root import handle_get_root


class FakeClientRoot:
    def get_root_document(self):
        return {
            "id": "root-id",
            "title": "Root Title",
            "description": "A test root",
            "links": [1, 2, 3],
            "conformsTo": [f"c{i}" for i in range(8)],
        }


def test_handle_get_root_text_and_json():
    client = FakeClientRoot()
    text = handle_get_root(client, {})
    assert isinstance(text, list)
    assert "Root Title" in text[0].text
    # JSON mode
    j = handle_get_root(client, {"output_format": "json"})
    assert isinstance(j, dict)
    assert j["type"] == "root"


class FakeClientConformance:
    def get_conformance(self, check=None):  # noqa: ARG002
        return {"conformsTo": ["a", "b"], "checks": {"a": True, "b": False}}


def test_handle_get_conformance_text_and_json():
    client = FakeClientConformance()
    text = handle_get_conformance(client, {})
    assert "Conformance Classes (2)" in text[0].text
    # JSON
    j = handle_get_conformance(client, {"output_format": "json"})
    assert isinstance(j, dict)
    assert j["type"] == "conformance"


def test_handle_get_item_various_fields():
    class FakeClientItem:
        def get_item(self, collection_id, item_id):  # noqa: ARG002
            return {
                "id": "i1",
                "collection": collection_id,
                "datetime": "2020-01-01T00:00:00Z",
                "bbox": [0, 0, 10, 10],
                "properties": {"a": "b", "c": 1},
                "assets": {
                    "thumb": {"title": "Thumb", "type": "image/png", "href": "http://x"}
                },
            }

    client = FakeClientItem()
    res = handle_get_item(client, {"collection_id": "col", "item_id": "it"})
    assert "Item: i1" in res[0].text
    assert "Assets (1)" in res[0].text
    # JSON output
    j = handle_get_item(
        client, {"collection_id": "col", "item_id": "it", "output_format": "json"}
    )
    assert isinstance(j, dict)
    assert j["type"] == "item"
