from __future__ import annotations

from contextlib import asynccontextmanager
from io import BytesIO

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from PIL import Image, ImageCms, ImageOps, UnidentifiedImageError

from .config import MAX_GRID_CELLS, MAX_GRID_SIDE, MAX_IMAGE_PIXELS, MAX_UPLOAD_BYTES
from .generator import generate
from .registry import RegistryIndex


class InputError(ValueError):
    def __init__(self, message: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.status_code = status_code


def _standardize_image(image_bytes: bytes) -> Image.Image:
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise InputError("uploaded image exceeds 10 MiB", 413)

    try:
        with Image.open(BytesIO(image_bytes)) as opened:
            opened.load()

            if opened.width * opened.height > MAX_IMAGE_PIXELS:
                raise InputError("decoded image exceeds pixel limit", 413)

            image = ImageOps.exif_transpose(opened)
            alpha = image.getchannel("A") if "A" in image.getbands() else None

            if image.info.get("icc_profile"):
                source_profile = ImageCms.ImageCmsProfile(BytesIO(image.info["icc_profile"]))
                destination_profile = ImageCms.createProfile("sRGB")
                rgb = ImageCms.profileToProfile(
                    image.convert("RGB"), source_profile, destination_profile, outputMode="RGB"
                )

                if alpha is not None:
                    rgb.putalpha(alpha)

                return rgb.convert("RGBA")

            return image.convert("RGBA")

    except InputError:
        raise

    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as error:
        raise InputError("image cannot be decoded or converted to sRGB") from error


def _resolve_dimensions(
    image: Image.Image,
    width: int | None,
    height: int | None,
    preserve_aspect_ratio: bool,
) -> tuple[int, int, bool]:
    """Return validated dimensions and whether the image must be center-cropped."""
    if preserve_aspect_ratio:
        if width is not None and height is not None:
            raise InputError("width and height cannot both be provided when preserve_aspect_ratio is true")

        if width is None and height is None:
            raise InputError("provide exactly one of width or height when preserve_aspect_ratio is true")

        if width is not None:
            height = max(1, round(width * image.height / image.width))
        else:
            width = max(1, round(height * image.width / image.height))

        crop = False
    else:
        if width is None or height is None:
            raise InputError("width and height are required unless preserve_aspect_ratio is true")

        crop = True

    if (
        width <= 0
        or height <= 0
        or width > MAX_GRID_SIDE
        or height > MAX_GRID_SIDE
        or width * height > MAX_GRID_CELLS
    ):
        raise InputError("width and height must fit within the supported grid limits")

    return width, height, crop


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.registry = RegistryIndex.load()
    yield


app = FastAPI(title="Bead Pattern Generator", version="0.1.0", lifespan=lifespan)


@app.exception_handler(InputError)
async def input_error_handler(_: Request, error: InputError) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content={"code": "invalid_input", "message": str(error)})


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_: Request, error: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"code": "invalid_request", "message": "invalid multipart form data"})


@app.get("/api/registries")
async def list_registries(request: Request) -> list[dict[str, object]]:
    return request.app.state.registry.registries()


@app.get("/api/registries/{registry_id}/series")
async def list_series(registry_id: str, request: Request) -> list[dict[str, object]]:
    series = request.app.state.registry.series(registry_id)
    if series is None:
        raise HTTPException(status_code=404, detail="registry not found")
    return series


@app.post("/api/generate", response_class=Response)
async def generate_pattern(
    request: Request,
    image: UploadFile = File(...),
    registry_id: str = Form(...),
    series_id: str = Form(...),
    width: int | None = Form(None),
    height: int | None = Form(None),
    preserve_aspect_ratio: bool = Form(False),
) -> Response:
    palette = request.app.state.registry.get(registry_id, series_id)
    if palette is None:
        raise InputError("registry_id or series_id does not exist", 404)

    image_bytes = await image.read(MAX_UPLOAD_BYTES + 1)
    validated_image = _standardize_image(image_bytes)
    resolved_width, resolved_height, crop = _resolve_dimensions(
        validated_image, width, height, preserve_aspect_ratio
    )
    png_bytes = generate(validated_image, palette, resolved_width, resolved_height, crop=crop)

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Content-Disposition": 'attachment; filename="pattern.png"'},
    )

