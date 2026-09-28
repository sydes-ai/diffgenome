from unittest.mock import MagicMock, patch

import app.repository as repository


def test_get_stock_reads_from_inventory() -> None:
    mock_inventory = MagicMock(spec=dict)
    mock_inventory.get.return_value = 7

    with patch.object(repository, "_INVENTORY", mock_inventory):
        result = repository.get_stock("SKU-123")

    assert result == 7
    mock_inventory.get.assert_called_once_with("SKU-123")
