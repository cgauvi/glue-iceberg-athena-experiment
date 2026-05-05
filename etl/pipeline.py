"""Main ETL pipeline – fetch Overture Canada data then upload to S3.

This module provides both a reusable Python API and a Click CLI entry-point.

Usage (CLI)::

    python -m etl.pipeline fetch-and-upload \\
        --bucket my-bucket \\
        --prefix canada/raw \\
        --release 2025-01-22.0

Environment variables:
    TARGET_S3_BUCKET  - Destination S3 bucket name (overrides --bucket)
    TARGET_S3_PREFIX  - S3 key prefix (overrides --prefix)
    OVERTURE_RELEASE  - Overture release tag (overrides --release)
    LOCAL_DATA_DIR    - Scratch directory for local parquet files
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import boto3
import click

from etl.config import (
    LOCAL_DATA_DIR,
    OVERTURE_RELEASE,
    OVERTURE_THEMES,
    TARGET_S3_BUCKET,
    TARGET_S3_PREFIX,
)
from etl.fetch_overture import build_output_path, fetch_all_canada

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# S3 upload helpers
# ---------------------------------------------------------------------------


def upload_file_to_s3(
    local_path: str | Path,
    bucket: str,
    s3_key: str,
    s3_client=None,
) -> None:
    """Upload a single local file to S3.

    Args:
        local_path: Path to the file on disk.
        bucket: Destination S3 bucket name.
        s3_key: Destination S3 object key.
        s3_client: Optional pre-built boto3 S3 client (useful for testing).
    """
    client = s3_client or boto3.client("s3")
    logger.info("Uploading %s → s3://%s/%s", local_path, bucket, s3_key)
    client.upload_file(str(local_path), bucket, s3_key)
    logger.info("Upload complete: s3://%s/%s", bucket, s3_key)


def upload_directory_to_s3(
    local_dir: str | Path,
    bucket: str,
    prefix: str,
    s3_client=None,
) -> list[str]:
    """Upload all parquet files in *local_dir* to S3 under *prefix*.

    Returns:
        List of ``s3://bucket/key`` URIs that were uploaded.
    """
    client = s3_client or boto3.client("s3")
    local_dir = Path(local_dir)
    uploaded: list[str] = []

    for parquet_file in sorted(local_dir.glob("*.parquet")):
        s3_key = f"{prefix.rstrip('/')}/{parquet_file.name}"
        upload_file_to_s3(parquet_file, bucket, s3_key, s3_client=client)
        uploaded.append(f"s3://{bucket}/{s3_key}")

    return uploaded


# ---------------------------------------------------------------------------
# High-level pipeline steps
# ---------------------------------------------------------------------------


def run_fetch_step(
    local_dir: str | Path,
    release: str,
    themes: list[tuple[str, str]],
) -> list[str]:
    """Fetch Overture Canada data to the local scratch directory.

    Returns the list of local file paths that were written.
    """
    logger.info(
        "Fetching Overture release=%s themes=%s to %s", release, themes, local_dir
    )
    return fetch_all_canada(local_dir, release=release, themes=themes)


def run_upload_step(
    local_dir: str | Path,
    bucket: str,
    prefix: str,
    s3_client=None,
) -> list[str]:
    """Upload all parquet files in *local_dir* to S3.

    Returns the list of s3:// URIs written.
    """
    logger.info(
        "Uploading parquet files from %s to s3://%s/%s", local_dir, bucket, prefix
    )
    return upload_directory_to_s3(local_dir, bucket, prefix, s3_client=s3_client)


def run_pipeline(
    bucket: str,
    prefix: str = TARGET_S3_PREFIX,
    release: str = OVERTURE_RELEASE,
    local_dir: str | Path = LOCAL_DATA_DIR,
    themes: list[tuple[str, str]] | None = None,
    s3_client=None,
) -> dict[str, list[str]]:
    """Run the full fetch → upload ETL pipeline.

    Args:
        bucket: Destination S3 bucket name.
        prefix: S3 key prefix for the uploaded files.
        release: Overture Maps release version string.
        local_dir: Scratch directory for intermediate parquet files.
        themes: List of ``(theme, type)`` tuples to fetch.
        s3_client: Optional pre-built boto3 S3 client.

    Returns:
        A dict with keys ``"local_files"`` and ``"s3_uris"``.
    """
    themes = themes or OVERTURE_THEMES
    local_files = run_fetch_step(local_dir, release, themes)
    s3_uris = run_upload_step(local_dir, bucket, prefix, s3_client=s3_client)
    return {"local_files": local_files, "s3_uris": s3_uris}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


@click.group()
def cli() -> None:
    """Overture Maps Canada ETL pipeline."""


@cli.command("fetch")
@click.option("--output-dir", default=LOCAL_DATA_DIR, show_default=True,
              help="Local directory to write parquet files.")
@click.option("--release", default=OVERTURE_RELEASE, show_default=True,
              help="Overture release version string.")
@click.option("--theme", "theme_list", multiple=True,
              help="theme:type pair to fetch (repeatable). "
                   "Defaults to places:place, buildings:building, admins:administrative_boundary.")
@click.option("--verbose", is_flag=True, default=False)
def cmd_fetch(output_dir: str, release: str, theme_list: tuple, verbose: bool) -> None:
    """Fetch Overture Canada data to a local directory."""
    _setup_logging(verbose)
    themes = (
        [tuple(t.split(":", 1)) for t in theme_list]  # type: ignore[misc]
        if theme_list
        else OVERTURE_THEMES
    )
    paths = run_fetch_step(output_dir, release, themes)  # type: ignore[arg-type]
    click.echo(f"Fetched {len(paths)} file(s):")
    for p in paths:
        click.echo(f"  {p}")


@cli.command("upload")
@click.option("--local-dir", default=LOCAL_DATA_DIR, show_default=True,
              help="Local directory containing parquet files to upload.")
@click.option("--bucket", required=True, envvar="TARGET_S3_BUCKET",
              help="Destination S3 bucket name.")
@click.option("--prefix", default=TARGET_S3_PREFIX, show_default=True,
              envvar="TARGET_S3_PREFIX",
              help="S3 key prefix.")
@click.option("--verbose", is_flag=True, default=False)
def cmd_upload(local_dir: str, bucket: str, prefix: str, verbose: bool) -> None:
    """Upload local parquet files to S3."""
    _setup_logging(verbose)
    uris = run_upload_step(local_dir, bucket, prefix)
    click.echo(f"Uploaded {len(uris)} file(s):")
    for uri in uris:
        click.echo(f"  {uri}")


@cli.command("fetch-and-upload")
@click.option("--bucket", required=True, envvar="TARGET_S3_BUCKET",
              help="Destination S3 bucket name.")
@click.option("--prefix", default=TARGET_S3_PREFIX, show_default=True,
              envvar="TARGET_S3_PREFIX",
              help="S3 key prefix.")
@click.option("--release", default=OVERTURE_RELEASE, show_default=True,
              envvar="OVERTURE_RELEASE",
              help="Overture release version string.")
@click.option("--local-dir", default=LOCAL_DATA_DIR, show_default=True,
              help="Scratch directory for intermediate parquet files.")
@click.option("--theme", "theme_list", multiple=True,
              help="theme:type pair to fetch (repeatable).")
@click.option("--verbose", is_flag=True, default=False)
def cmd_fetch_and_upload(
    bucket: str,
    prefix: str,
    release: str,
    local_dir: str,
    theme_list: tuple,
    verbose: bool,
) -> None:
    """Fetch Overture Canada data then upload to S3 (full pipeline)."""
    _setup_logging(verbose)
    themes = (
        [tuple(t.split(":", 1)) for t in theme_list]  # type: ignore[misc]
        if theme_list
        else None
    )
    result = run_pipeline(
        bucket=bucket,
        prefix=prefix,
        release=release,
        local_dir=local_dir,
        themes=themes,  # type: ignore[arg-type]
    )
    click.echo(f"Pipeline complete – {len(result['s3_uris'])} file(s) on S3:")
    for uri in result["s3_uris"]:
        click.echo(f"  {uri}")


if __name__ == "__main__":
    cli()
