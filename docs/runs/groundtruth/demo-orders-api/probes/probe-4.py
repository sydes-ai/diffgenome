from unittest.mock import patch

import app.repository as repo
from app.models import OrderCreate


def test_probe_save_order_spies_on_order_ctor_and_appends(monkeypatch) -> None:
    # Isolate repository state
    monkeypatch.setattr(repo, "_ORDERS", [])

    original_order_cls = repo.Order
    order_in = OrderCreate(sku="BOOK-001", quantity=2)

    # Spy on the Order constructor while still executing real construction
    with patch("app.repository.Order", wraps=original_order_cls) as order_spy:
        result = repo.save_order(order_in)

        # Verify constructor was called with expected arguments
        assert order_spy.call_count == 1
        assert order_spy.call_args.kwargs == {
            "id": 1,
            "sku": "BOOK-001",
            "quantity": 2,
        }

    # Verify returned object and in-memory persistence behavior
    assert isinstance(result, original_order_cls)
    assert result.id == 1
    assert result.sku == "BOOK-001"
    assert result.quantity == 2
    assert repo._ORDERS == [result]
