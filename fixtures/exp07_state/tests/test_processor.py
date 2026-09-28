import pytest
from proc import settings
from proc.processor import Processor
from proc.repository import Repository, RepositoryClosed


def test_run_enabled_persists() -> None:
    assert Processor(Repository(), enabled=True).run("item-1") == "stored:item-1"


def test_run_enabled_strict_audits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "STRICT", True)
    repo = Repository()
    assert Processor(repo, enabled=True).run("item-1") == "stored:item-1"
    assert repo.rows == ["audit:item-1", "item-1"]


def test_run_disabled_skips() -> None:
    assert Processor(Repository(), enabled=False).run("item-1") == "skipped:item-1"


def test_run_enabled_closed_repository_raises() -> None:
    repo = Repository()
    repo.closed = True
    with pytest.raises(RepositoryClosed):
        Processor(repo, enabled=True).run("item-1")
