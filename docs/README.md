# Service API Guide

The [design specification](ALGORITHM_README.md) defines service behavior, algorithms, and limits. This guide explains how to call the API.

## Start the service

Run from the project root:

```powershell
uv sync --frozen
uv run uvicorn --app-dir src bead_pattern.main:app --host 127.0.0.1 --port 8000
```

The interactive API documentation is available at `http://127.0.0.1:8000/docs`.

Alternatively, use Docker:

```powershell
docker compose up --build
```

The image includes the palette files in `src/data/registries/`; that directory is not mounted at runtime.

## Registry queries

### List all registries

```http
GET /api/registries
```

The response lists each `registry_id` and its series. Currently available:

- `artkal` / `s-5mm`
- `perler` / `color-chart`

### List series in a registry

```http
GET /api/registries/{registry_id}/series
```

An unknown registry returns `404`.

## Generate a pattern

```http
POST /api/generate
Content-Type: multipart/form-data
```

Fields:

| Field | Required | Description |
| --- | --- | --- |
| `image` | Yes | Image file content. |
| `registry_id` | Yes | Palette registry, such as `artkal`. |
| `series_id` | Yes | Series ID, such as `s-5mm`. |
| `width` | In default mode | Number of bead columns. |
| `height` | In default mode | Number of bead rows. |
| `preserve_aspect_ratio` | No | Set to `true` to retain the original image's aspect ratio. |

In default mode, supply both `width` and `height`. The service center-crops the image and creates a grid of that size.

With `preserve_aspect_ratio=true`, supply exactly one of `width` or `height`. The service calculates the other dimension from the image after EXIF orientation correction and does not crop it.

On success, the response is:

```http
200 OK
Content-Type: image/png
Content-Disposition: attachment; filename="pattern.png"
```

The response body is the complete PNG pattern, containing the color grid, cell labels, row and column coordinates, and a color-code legend.

### Default crop example

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/generate" -F "image=@C:\path\to\photo.png" -F "registry_id=artkal" -F "series_id=s-5mm" -F "width=50" -F "height=40" --output pattern.png
```

### Preserve aspect ratio example

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/generate" -F "image=@C:\path\to\photo.png" -F "registry_id=artkal" -F "series_id=s-5mm" -F "width=100" -F "preserve_aspect_ratio=true" --output pattern.png
```

## Limits and errors

Limits are defined in `src/bead_pattern/config.py`. If you change that file, restart the service and update this section.

- Maximum upload size: 10 MiB.
- Maximum decoded pixel count: 16,000,000.
- Maximum pattern size: 200 cells per side and 40,000 cells in total.
- An unknown registry or series returns `404`.
- An invalid form, undecodable image, invalid dimensions, or both dimensions in aspect-ratio mode returns `422`.

Errors use JSON:

```json
{
  "code": "invalid_input",
  "message": "..."
}
```
