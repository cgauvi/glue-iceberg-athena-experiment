"""Configuration constants for the Overture Maps Canada ETL pipeline."""

from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Overture Maps release
# ---------------------------------------------------------------------------
# Latest stable release – override via OVERTURE_RELEASE env var.
DEFAULT_OVERTURE_RELEASE = "2025-01-22.0"
OVERTURE_RELEASE: str = os.environ.get("OVERTURE_RELEASE", DEFAULT_OVERTURE_RELEASE)

# Public Overture Maps S3 bucket (us-west-2, no auth required)
OVERTURE_S3_BUCKET = "overturemaps-us-west-2"
OVERTURE_S3_REGION = "us-west-2"

# ---------------------------------------------------------------------------
# Canada bounding box  (WGS-84 lon/lat)
# ---------------------------------------------------------------------------
# Approximate mainland + island bounding box for Canada.
# (min_lon, min_lat, max_lon, max_lat)
CANADA_BBOX: tuple[float, float, float, float] = (-141.0, 41.7, -52.6, 83.1)

# ---------------------------------------------------------------------------
# Overture themes / types to fetch
# ---------------------------------------------------------------------------
# Each tuple is (theme, type) corresponding to the S3 path partitioning:
#   s3://overturemaps-us-west-2/release/<version>/theme=<theme>/type=<type>/
OVERTURE_THEMES: list[tuple[str, str]] = [
    ("places", "place"),
    ("buildings", "building"),
    ("admins", "administrative_boundary"),
]

# ---------------------------------------------------------------------------
# Local data directory (used when OUTPUT_DIR env var is not set)
# ---------------------------------------------------------------------------
DEFAULT_LOCAL_DATA_DIR = "data/raw"
LOCAL_DATA_DIR: str = os.environ.get("LOCAL_DATA_DIR", DEFAULT_LOCAL_DATA_DIR)

# ---------------------------------------------------------------------------
# S3 destination
# ---------------------------------------------------------------------------
# Target S3 bucket – must be set via env var or passed explicitly.
TARGET_S3_BUCKET: str = os.environ.get("TARGET_S3_BUCKET", "")
TARGET_S3_PREFIX: str = os.environ.get("TARGET_S3_PREFIX", "canada/raw")
