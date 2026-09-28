class RepositoryClosed(RuntimeError):
    pass


class Repository:
    def __init__(self) -> None:
        self.rows: list[str] = []
        self.closed = False

    def save(self, item: str) -> int:
        if self.closed:
            raise RepositoryClosed(item)
        self.rows.append(item)
        return len(self.rows)
