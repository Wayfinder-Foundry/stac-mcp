import pytest


def test_skipped_removed_tabular_helpers():
    pytest.skip("Parquet/Zarr fallback and helpers removed in this PR")
