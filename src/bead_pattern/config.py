"""Static service limits.

This module deliberately does not read environment variables. Change these
constants in source code when changing the supported request contract.
"""

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
MAX_GRID_SIDE = 200
MAX_GRID_CELLS = 40_000
