"""Fetch Overture Maps data for Canada using DuckDB and the httpfs extension.

The public Overture Maps parquet files are stored on S3 (us-west-2).  This
module uses DuckDB's ``httpfs`` + ``spatial`` extensions to read from the
public bucket, filter rows to the Canada bounding box, and write parquet files
to either a local path or directly to an S3 destination bucket.

Overture bbox column convention (2024-07 release onwards): the ``bbox``
top-level struct has fields ``xmin``, ``ymin``, ``xmax``, ``ymax``.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Union

import duckdb

from etl.config import (
    CANADA_BBOX,
    OVERTURE_RELEASE,
    OVERTURE_S3_BUCKET,
    OVERTURE_S3_REGION,
    OVERTURE_THEMES,
)

logger = logging.getLogger(__name__)

# Type alias for output paths (local filesystem or s3:// URI)
OutputPath = Union[str, Path]


# ---------------------------------------------------------------------------
# DuckDB connection helpers
# ---------------------------------------------------------------------------


def create_duckdb_connection(
    *,
    aws_access_key_id: str | None = None,
    aws_secret_access_key: str | None = None,
    aws_session_token: str | None = None,
    aws_region: str | None = None,
) -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection pre-loaded with ``httpfs`` and ``spatial``.

    Credentials are read from the environment when not supplied explicitly.
    The function installs the extensions on first run; subsequent calls reuse
    the cached extension binaries.
    """
    conn = duckdb.connect()

    conn.execute("INSTALL httpfs; LOAD httpfs;")
    conn.execute("INSTALL spatial; LOAD spatial;")

    # Set the read-only region for Overture's public bucket
    region = aws_region or OVERTURE_S3_REGION
    conn.execute(f"SET s3_region='{region}';")

    # Credentials: fall back to environment / instance profile when not given
    key = aws_access_key_id or os.environ.get("AWS_ACCESS_KEY_ID", "")
    secret = aws_secret_access_key or os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    token = aws_session_token or os.environ.get("AWS_SESSION_TOKEN", "")

    if key:
        conn.execute(f"SET s3_access_key_id='{key}';")
    if secret:
        conn.execute(f"SET s3_secret_access_key='{secret}';")
    if token:
        conn.execute(f"SET s3_session_token='{token}';")

    return conn


# ---------------------------------------------------------------------------
# Path / URL builders
# ---------------------------------------------------------------------------


def build_overture_s3_glob(release: str, theme: str, type_: str) -> str:
    """Return the S3 glob pattern for a given Overture release / theme / type."""
    return (
        f"s3://{OVERTURE_S3_BUCKET}/release/{release}"
        f"/theme={theme}/type={type_}/*.parquet"
    )


def build_output_path(output_dir: OutputPath, theme: str, type_: str) -> str:
    """Return the destination file/S3 path for a theme+type combination."""
    filename = f"{theme}_{type_}.parquet"
    base = str(output_dir).rstrip("/")
    return f"{base}/{filename}"


# ---------------------------------------------------------------------------
# Core fetch logic
# ---------------------------------------------------------------------------


def fetch_canada_theme(
    conn: duckdb.DuckDBPyConnection,
    theme: str,
    type_: str,
    release: str,
    output_path: str,
) -> str:
    """Fetch a single Overture theme/type for Canada and write to *output_path*.

    The function uses bbox pushdown (reading only row-groups that overlap the
    Canada bounding box) for efficiency.

    Args:
        conn: Pre-configured DuckDB connection with httpfs loaded.
        theme: Overture theme name (e.g. ``"places"``).
        type_: Overture type within the theme (e.g. ``"place"``).
        release: Overture release string (e.g. ``"2025-01-22.0"``).
        output_path: Local file path or ``s3://`` URI to write parquet output.

    Returns:
        The *output_path* string.
    """
    min_lon, min_lat, max_lon, max_lat = CANADA_BBOX
    source = build_overture_s3_glob(release, theme, type_)

    logger.info("Fetching theme=%s type=%s from %s", theme, type_, source)

    query = f"""
        COPY (
            SELECT *
            FROM read_parquet('{source}', hive_partitioning = true)
            WHERE bbox.xmin < {max_lon}
              AND bbox.xmax > {min_lon}
              AND bbox.ymin < {max_lat}
              AND bbox.ymax > {min_lat}
        ) TO '{output_path}' (FORMAT PARQUET, COMPRESSION 'zstd')
    """

    conn.execute(query)
    logger.info("Wrote %s/%s output to %s", theme, type_, output_path)
    return output_path


def fetch_all_canada(
    output_dir: OutputPath,
    *,
    release: str | None = None,
    themes: list[tuple[str, str]] | None = None,
    conn: duckdb.DuckDBPyConnection | None = None,
) -> list[str]:
    """Fetch all configured Overture themes for Canada.

    Creates *output_dir* if it is a local path and does not yet exist.

    Args:
        output_dir: Local directory path or S3 prefix to write parquet files.
        release: Overture release string; defaults to :data:`~etl.config.OVERTURE_RELEASE`.
        themes: List of ``(theme, type)`` tuples; defaults to
            :data:`~etl.config.OVERTURE_THEMES`.
        conn: Optional pre-built DuckDB connection (useful for testing).

    Returns:
        List of output file/URI paths that were written.
    """
    release = release or OVERTURE_RELEASE
    themes = themes or OVERTURE_THEMES

    # Create local directory if needed
    output_str = str(output_dir)
    if not output_str.startswith("s3://"):
        Path(output_str).mkdir(parents=True, exist_ok=True)

    close_conn = conn is None
    if conn is None:
        conn = create_duckdb_connection()

    outputs: list[str] = []
    try:
        for theme, type_ in themes:
            dest = build_output_path(output_dir, theme, type_)
            fetch_canada_theme(conn, theme, type_, release, dest)
            outputs.append(dest)
    finally:
        if close_conn:
            conn.close()

    return outputs


def get_row_count(
    conn: duckdb.DuckDBPyConnection,
    theme: str,
    type_: str,
    release: str,
) -> int:
    """Return the approximate row count for a Canada-filtered theme/type.

    Useful for sanity-checking or progress estimation before a full fetch.
    """
    min_lon, min_lat, max_lon, max_lat = CANADA_BBOX
    source = build_overture_s3_glob(release, theme, type_)

    result = conn.execute(
        f"""
        SELECT COUNT(*) AS cnt
        FROM read_parquet('{source}', hive_partitioning = true)
        WHERE bbox.xmin < {max_lon}
          AND bbox.xmax > {min_lon}
          AND bbox.ymin < {max_lat}
          AND bbox.ymax > {min_lat}
        """
    ).fetchone()

    return int(result[0]) if result else 0
