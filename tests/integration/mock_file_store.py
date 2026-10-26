from __future__ import annotations

from pathlib import Path


class MockDownstreamClient:
    """Integration-test-only HTTP client that captures the received PNG bytes."""

    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path
        self.headers: dict[str, str] | None = None

    def post(self, url: str, *, content: bytes, headers: dict[str, str]) -> "MockResponse":
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_bytes(content)
        self.headers = headers

        return MockResponse()


def load_fixture_image(name: str) -> bytes:
    return (Path(__file__).parent / "fixtures" / name).read_bytes()


class MockResponse:
    def raise_for_status(self) -> None:
        return None

