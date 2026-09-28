from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.main import create_order
from app.models import OrderCreate
from app.service import UnknownSkuError


def test_probe_create_order_executes_and_handles_unknown_sku() -> None:
    order = OrderCreate(sku="BOOK-123", quantity=1)

    with patch("app.main.create_order_service", autospec=True) as mock_service:
        # Successful path: returns whatever the service returns
        sentinel_result = object()
        mock_service.return_value = sentinel_result
        result = create_order(order)
        assert result is sentinel_result
        mock_service.assert_called_once_with(order)

        # Error path: service raises an UnknownSkuError (via a harmless subclass)
        mock_service.reset_mock()

        class DummyUnknownSkuError(UnknownSkuError):
            def __init__(self):  # make construction arg-less and safe
                pass

        mock_service.side_effect = DummyUnknownSkuError()
        with pytest.raises(HTTPException) as exc:
            create_order(order)
        assert exc.value.status_code == 404
        assert exc.value.detail == "SKU not found"
        mock_service.assert_called_once_with(order)
