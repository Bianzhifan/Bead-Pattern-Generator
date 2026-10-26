from __future__ import annotations

from typing import Protocol


class HttpClient(Protocol):
    def post(self, url: str, *, content: bytes, headers: dict[str, str]): ...


class DownstreamDeliveryError(RuntimeError):
    pass


def send_to_downstream(client: HttpClient, target: str, png_bytes: bytes, request_id: str) -> None:
    """Send an already-generated PNG unchanged to an integration-provided endpoint."""
    try:
        response = client.post(
            target,
            content=png_bytes,
            headers={"Content-Type": "image/png", "X-Request-ID": request_id},
        )
        response.raise_for_status()

    except Exception as error:
        raise DownstreamDeliveryError(f"downstream delivery failed: {error}") from error

