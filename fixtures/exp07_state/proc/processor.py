from proc import settings
from proc.repository import Repository


class Processor:
    def __init__(self, repo: Repository, enabled: bool = True) -> None:
        self.repo = repo
        self.enabled = enabled
        self.seen = 0

    def run(self, item: str) -> str:
        self.seen += 1
        if not self.enabled:
            return self.skip(item)
        self.validate(item)
        if settings.STRICT:
            self.audit(item)
        return self.persist(item)

    def skip(self, item: str) -> str:
        return f"skipped:{item}"

    def validate(self, item: str) -> None:
        if not item:
            raise ValueError("empty item")

    def audit(self, item: str) -> None:
        self.repo.save(f"audit:{item}")

    def persist(self, item: str) -> str:
        self.repo.save(item)
        return f"stored:{item}"
