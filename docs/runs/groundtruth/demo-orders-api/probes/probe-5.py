from unittest.mock import patch

from app.main import read_inventory


def test_read_inventory_calls_get_stock_and_returns_item() -> None:
    # Patch the direct in-repo collaborator used by read_inventory
    with patch("app.main.get_stock", autospec=True, return_value=7) as mock_get_stock:
        item = read_inventory("SKU-123")

    # Ensure the seam is exercised
    mock_get_stock.assert_called_once_with("SKU-123")

    # Validate the real in-repo model was constructed as expected
    assert item.sku == "SKU-123"
    assert item.stock == 7
