import json
import urllib.request


class InventoryService:
    """Talks to a remote inventory API. Intentionally has no unit test of its own."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    def reserve(self, skus: list[str]) -> None:
        body = json.dumps({"skus": skus}).encode()
        request = urllib.request.Request(f"{self._base_url}/reservations", data=body, method="POST")
        with urllib.request.urlopen(request, timeout=5) as response:
            if response.status != 201:
                raise RuntimeError(f"reservation failed: {response.status}")
