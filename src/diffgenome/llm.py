"""The replaceable LLM seam. One narrow job: write a probe for a stated objective.

`ProbeWriter` is the whole interface. `OpenAIProbeWriter` speaks to the chat completions
endpoint over urllib; `RecordedProbeWriter` replays canned answers for tests. No provider
framework: a second provider is a second class implementing `write`.
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass
class ProbeRequest:
    objective: str  # one paragraph: what the probe must make execute, and why
    context: str  # bounded: sources, seam facts, nearby tests
    constraints: str  # the safety and unit-level rules, verbatim
    conventions: str = ""  # runtime/framework conventions from the runtime adapter
    previous_failures: list[str] = field(default_factory=list)


@dataclass
class ProbeDraft:
    filename: str
    code: str
    rationale: str
    model: str  # which model/recording produced it (provenance)


class ProbeWriter(Protocol):
    def write(self, request: ProbeRequest) -> ProbeDraft: ...


_SYSTEM = """You write one minimal, isolated unit-level test ("probe") for a repository.
The probe exists so that a specific in-repo function executes under tracing. It must:
- be a test file for the repository's own test framework (stated in the request); import
  the target through the repository's own module paths;
- execute the real in-repo target and, where possible, the real in-repo code it calls;
- keep every genuine external dependency substituted (network, model files, GPUs, disk
  outside a tmp_path, subprocesses, time-based waits): use unittest.mock / pytest fixtures;
- never contact any real service, never sleep for long, never spawn processes;
- follow the conventions visible in the nearby tests (fixtures, async style, imports);
- be deterministic and fast; prefer the smallest stimulus that reaches the target.
Reply with a single JSON object:
{"filename": "<test file name>", "code": "<file>", "rationale": "<one paragraph>"}.
The code must be a complete file; the filename is advisory (the harness places the file)."""


_KEY_FILE = Path.home() / ".config" / "diffgenome" / "openai_api_key"
_KEYCHAIN_SERVICE = "diffgenome-openai"
_PREFERRED_MODELS = ("gpt-5", "gpt-4.1", "gpt-4o")


def load_api_key() -> str:
    """Environment, then a user-only file, then the macOS Keychain. The key stays in this
    process: probes run with a scrubbed environment and no network."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    try:
        if _KEY_FILE.is_file():
            key = _KEY_FILE.read_text().strip()
            if key:
                return key
    except OSError:
        pass
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", _KEYCHAIN_SERVICE, "-w"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    raise RuntimeError(
        f"no OpenAI key: set OPENAI_API_KEY, write {_KEY_FILE} (mode 600), "
        f"or add a Keychain item '{_KEYCHAIN_SERVICE}'"
    )


class OpenAIProbeWriter:
    def __init__(
        self, model: str | None = None, api_key: str | None = None, timeout: int = 180
    ) -> None:
        self.api_key = api_key or load_api_key()
        self.timeout = timeout
        self.base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = model or os.environ.get("DIFFGENOME_OPENAI_MODEL") or self._pick_model()

    def _get(self, path: str) -> dict[str, object]:
        req = urllib.request.Request(
            f"{self.base}{path}", headers={"Authorization": f"Bearer {self.api_key}"}
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data: dict[str, object] = json.load(resp)
            return data

    def _pick_model(self) -> str:
        """Choose the first preferred family the account actually lists (exact id, else the
        newest dated variant); never guess a model name blindly."""
        try:
            listed = self._get("/models").get("data")
        except (urllib.error.URLError, RuntimeError, OSError):
            return _PREFERRED_MODELS[1]
        ids = sorted(str(m["id"]) for m in listed) if isinstance(listed, list) else []
        for family in _PREFERRED_MODELS:
            if family in ids:
                return family
            dated = [
                i for i in ids if i.startswith(family + "-") and i[len(family) + 1 :][:1].isdigit()
            ]
            if dated:
                return sorted(dated)[-1]
        return _PREFERRED_MODELS[1]

    def _post(self, path: str, body: dict[str, object]) -> dict[str, object]:
        req = urllib.request.Request(
            f"{self.base}{path}",
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data: dict[str, object] = json.load(resp)
                return data
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:500]
            raise RuntimeError(f"OpenAI HTTP {exc.code}: {detail}") from exc

    def write(self, request: ProbeRequest) -> ProbeDraft:
        user = (
            f"OBJECTIVE\n{request.objective}\n\nCONSTRAINTS\n{request.constraints}\n\n"
            f"RUNTIME AND CONVENTIONS\n{request.conventions}\n\nCONTEXT\n{request.context}\n"
        )
        if request.previous_failures:
            user += "\nPREVIOUS ATTEMPTS FAILED VERIFICATION\n" + "\n---\n".join(
                request.previous_failures
            )
            user += "\nWrite a different probe that avoids these failures.\n"
        data = self._post(
            "/chat/completions",
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
            },
        )
        choices = data.get("choices")
        assert isinstance(choices, list) and choices
        content = choices[0]["message"]["content"]
        try:
            obj = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"model returned non-JSON: {content[:200]}") from exc
        filename = str(obj.get("filename", "probe"))
        return ProbeDraft(filename, str(obj["code"]), str(obj.get("rationale", "")), self.model)


class RecordedProbeWriter:
    """Replays drafts from a directory of ``<n>.py`` files in order; for tests and for
    re-running a report without spending tokens. Records nothing itself."""

    def __init__(self, directory: Path) -> None:
        self.files = sorted(directory.glob("*.py"))
        self.calls = 0

    def write(self, request: ProbeRequest) -> ProbeDraft:
        if self.calls >= len(self.files):
            raise RuntimeError("recorded writer has no more drafts")
        file = self.files[self.calls]
        self.calls += 1
        return ProbeDraft(
            f"test_probe_{file.stem}.py", file.read_text(), f"recorded: {file.name}", "recorded"
        )
