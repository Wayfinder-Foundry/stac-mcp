from stac_mcp.tools.get_root import handle_get_root


def test_get_root_with_client_client_to_dict():
    class Inner:
        def to_dict(self):
            return {
                "id": "inner-root",
                "title": "Inner Title",
                "links": [],
                "conformsTo": [],
            }

    class Wrapper:
        def __init__(self):
            self.client = Inner()

    res = handle_get_root(Wrapper(), {})
    assert isinstance(res, list)
    assert "Inner Title" in res[0].text


def test_get_root_with_raw_client_to_dict():
    class Raw:
        def to_dict(self):
            return {
                "id": "raw-root",
                "title": "Raw Title",
                "links": [],
                "conformsTo": [],
            }

    res = handle_get_root(Raw(), {})
    assert isinstance(res, list)
    assert "Raw Title" in res[0].text
