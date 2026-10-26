# Bead Pattern Generation Service

Generate a PNG bead pattern with a color-code legend from an image, a palette registry, and a target grid.

See the [design specification](docs/ALGORITHM_README.md) and the [API usage guide](docs/README.md).

## Run from source

Install [uv](https://docs.astral.sh/uv/) first:

```powershell
uv sync --frozen
uv run uvicorn --app-dir src bead_pattern.main:app --host 127.0.0.1 --port 8000
```

## Run with Docker

The Docker image includes `src/` and its local palettes. The palette directory is neither mounted nor modified at runtime:

```powershell
docker compose up --build
```

The service listens at `http://127.0.0.1:8000`. Stop it with `docker compose down`.

Once running, open `http://127.0.0.1:8000/docs` to upload an image, or use:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/generate" -F "image=@C:\path\to\photo.png" -F "registry_id=perler" -F "series_id=color-chart" -F "width=50" -F "height=40" --output pattern.png
```

On success, the API returns `image/png`. Palettes live in `src/data/registries/` and are validated once at startup.

The current palettes are distributed with the source code. Future versions should download or synchronize palette registries from the cloud using the existing `registry_id`, `series_id`, `code`, `name`, and `hex` structure. A new palette must pass validation before it replaces the active one.

By default, both `width` and `height` are required, and the service center-crops the image to that ratio. To preserve the full image's aspect ratio, set the optional `preserve_aspect_ratio=true` field and provide only one dimension. The service calculates the other dimension without cropping:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/generate" -F "image=@C:\path\to\photo.png" -F "registry_id=artkal" -F "series_id=s-5mm" -F "width=100" -F "preserve_aspect_ratio=true" --output pattern.png
```

Providing both `width` and `height` with `preserve_aspect_ratio=true` returns HTTP `422`. Patterns are limited to 200 cells per side and 40,000 cells in total.

## Tests

```powershell
uv run pytest -q
```
