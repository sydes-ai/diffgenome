from unittest.mock import patch

from app.service import get_stock


def test_get_stock_calls_repository_and_returns_value() -> None:
    sku = "PROBE-SKU"
    with patch("app.service.repository.get_stock", autospec=True, return_value=7) as mock_get:
        result = get_stock(sku)

    assert result == 7
    mock_get.assert_called_once_with(sku)
