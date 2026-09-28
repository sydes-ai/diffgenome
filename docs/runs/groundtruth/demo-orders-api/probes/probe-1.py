from unittest.mock import patch, sentinel

from app.models import OrderCreate
from app.service import create_order


def test_create_order_invokes_inventory_and_persists() -> None:
    order = OrderCreate(sku="BOOK-001", quantity=1)

    # Patch direct collaborators where they are referenced by the target
    with patch("app.service.get_stock", autospec=True) as mock_get_stock, \
         patch("app.repository.save_order", autospec=True) as mock_save_order:
        mock_get_stock.return_value = {"sku": order.sku, "stock": 10}
        mock_save_order.return_value = sentinel.saved_order

        result = create_order(order)

        mock_get_stock.assert_called_once_with(order.sku)
        mock_save_order.assert_called_once_with(order)
        assert result is sentinel.saved_order
