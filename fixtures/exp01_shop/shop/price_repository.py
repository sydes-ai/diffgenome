import sqlite3


class PriceRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def price_for(self, sku: str) -> int:
        row = self._conn.execute("SELECT cents FROM prices WHERE sku = ?", (sku,)).fetchone()
        if row is None:
            raise KeyError(sku)
        return int(row[0])
