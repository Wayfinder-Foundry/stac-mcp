import pytest


def test_skipped_removed_debug_helpers():
    pytest.skip("Parquet/Zarr debug helpers removed in this PR")
