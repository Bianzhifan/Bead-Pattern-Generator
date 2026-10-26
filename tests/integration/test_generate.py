from __future__ import annotations

from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from bead_pattern.image_processing import area_average_in_linear_rgb
from bead_pattern.main import InputError, _resolve_dimensions, _standardize_image, app
from bead_pattern.transport import send_to_downstream
from tests.integration.mock_file_store import MockDownstreamClient


def _test_image(width: int = 4, height: int = 4) -> bytes:
    image = Image.new("RGBA", (width, height), "#FFFFFF")
    image.putpixel((0, 0), (0, 0, 0, 128))
    output = BytesIO()
    image.save(output, format="PNG")

    return output.getvalue()


def test_generate_and_transmit_png() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/generate",
            files={"image": ("fixture.png", _test_image(), "image/png")},
            data={"registry_id": "perler", "series_id": "color-chart", "width": "2", "height": "2"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(BytesIO(response.content)) as result:
        assert result.width > 0 and result.height > 0
    output = Path("tests/integration/output/pattern.png")
    downstream = MockDownstreamClient(output)
    send_to_downstream(downstream, "https://mock-downstream.local/patterns", response.content, "test-request")

    assert output.read_bytes() == response.content
    assert downstream.headers == {"Content-Type": "image/png", "X-Request-ID": "test-request"}


def test_unknown_palette_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/generate",
            files={"image": ("fixture.png", _test_image(), "image/png")},
            data={"registry_id": "missing", "series_id": "missing", "width": "2", "height": "2"},
        )

    assert response.status_code == 404
    assert response.json()["code"] == "invalid_input"


def test_200_by_200_grid_is_supported() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/generate",
            files={"image": ("fixture.png", _test_image(), "image/png")},
            data={"registry_id": "artkal", "series_id": "s-5mm", "width": "200", "height": "200"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_non_square_grid_preserves_height_then_width_order() -> None:
    image = Image.new("RGBA", (6, 4), "#FFFFFF")
    grid = area_average_in_linear_rgb(image, width=3, height=2, crop=True)

    assert grid.shape == (2, 3, 3)


def test_preserved_aspect_ratio_calculates_missing_side_without_crop() -> None:
    image = Image.new("RGBA", (8, 4), "#FFFFFF")
    width, height, crop = _resolve_dimensions(image, width=60, height=None, preserve_aspect_ratio=True)

    assert (width, height, crop) == (60, 30, False)


def test_preserved_aspect_ratio_rejects_two_dimensions() -> None:
    image = Image.new("RGBA", (8, 4), "#FFFFFF")
    try:
        _resolve_dimensions(image, width=60, height=30, preserve_aspect_ratio=True)
    except InputError as error:
        assert "cannot both" in str(error)
    else:
        raise AssertionError("two dimensions must be rejected when preserve_aspect_ratio is true")


def test_api_preserves_aspect_ratio_with_one_dimension() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/generate",
            files={"image": ("fixture.png", _test_image(8, 4), "image/png")},
            data={
                "registry_id": "perler",
                "series_id": "color-chart",
                "width": "60",
                "preserve_aspect_ratio": "true",
            },
        )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_api_rejects_two_dimensions_when_preserving_aspect_ratio() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/generate",
            files={"image": ("fixture.png", _test_image(8, 4), "image/png")},
            data={
                "registry_id": "perler",
                "series_id": "color-chart",
                "width": "60",
                "height": "30",
                "preserve_aspect_ratio": "true",
            },
        )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_input"


def test_generated_image_preserves_aspect_ratio_without_rotation() -> None:
    screenshot = _test_image(200, 98)
    width, height, crop = _resolve_dimensions(
        _standardize_image(screenshot), width=100, height=None, preserve_aspect_ratio=True
    )
    assert (width, height, crop) == (100, 49, False)
    with TestClient(app) as client:
        response = client.post(
            "/api/generate",
            files={"image": ("screenshot.png", screenshot, "image/png")},
            data={
                "registry_id": "artkal",
                "series_id": "s-5mm",
                "width": "100",
                "preserve_aspect_ratio": "true",
            },
        )
    assert response.status_code == 200
    with Image.open(BytesIO(response.content)) as pattern:
        assert pattern.format == "PNG"

