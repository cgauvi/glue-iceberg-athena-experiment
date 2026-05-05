"""AWS Glue PySpark job – convert raw Overture parquet to Apache Iceberg tables.

This script is designed to run as an AWS Glue 4.0 job with the
``--datalake-formats iceberg`` flag enabled.  It reads the raw parquet files
uploaded by the Python ETL pipeline (``etl/pipeline.py``) from the raw S3
bucket, applies basic transformations, and writes the result as Iceberg tables
registered in the Glue Data Catalog.

Job parameters (``--key value`` in Glue console or Terraform):
    JOB_NAME          - Glue job name (injected automatically)
    source_bucket     - S3 bucket containing raw parquet files
    source_prefix     - S3 key prefix for raw parquet files (default: canada/raw)
    target_bucket     - S3 bucket for Iceberg data (may equal source_bucket)
    target_prefix     - S3 key prefix for Iceberg warehouse (default: canada/iceberg)
    database_name     - Glue Data Catalog database to create/use
"""

from __future__ import annotations

import sys

from awsglue.context import GlueContext  # type: ignore[import]
from awsglue.job import Job  # type: ignore[import]
from awsglue.utils import getResolvedOptions  # type: ignore[import]
from pyspark.context import SparkContext  # type: ignore[import]
from pyspark.sql import functions as F  # type: ignore[import]

# ---------------------------------------------------------------------------
# Job bootstrap
# ---------------------------------------------------------------------------

args = getResolvedOptions(
    sys.argv,
    [
        "JOB_NAME",
        "source_bucket",
        "source_prefix",
        "target_bucket",
        "target_prefix",
        "database_name",
    ],
)

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

# ---------------------------------------------------------------------------
# Spark / Iceberg configuration
# ---------------------------------------------------------------------------

WAREHOUSE = f"s3://{args['target_bucket']}/{args['target_prefix']}"

spark.conf.set(
    "spark.sql.extensions",
    "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
)
spark.conf.set("spark.sql.catalog.glue_catalog", "org.apache.iceberg.spark.SparkCatalog")
spark.conf.set("spark.sql.catalog.glue_catalog.warehouse", WAREHOUSE)
spark.conf.set(
    "spark.sql.catalog.glue_catalog.catalog-impl",
    "org.apache.iceberg.aws.glue.GlueCatalog",
)
spark.conf.set(
    "spark.sql.catalog.glue_catalog.io-impl",
    "org.apache.iceberg.aws.s3.S3FileIO",
)

# ---------------------------------------------------------------------------
# Ensure the Glue catalog database exists
# ---------------------------------------------------------------------------

DB = args["database_name"]
spark.sql(f"CREATE DATABASE IF NOT EXISTS glue_catalog.`{DB}`")

# ---------------------------------------------------------------------------
# Theme definitions – must match the filenames written by etl/fetch_overture.py
# ---------------------------------------------------------------------------

THEMES: list[tuple[str, str]] = [
    ("places", "place"),
    ("buildings", "building"),
    ("admins", "administrative_boundary"),
]


def _source_path(theme: str, type_: str) -> str:
    bucket = args["source_bucket"]
    prefix = args["source_prefix"].strip("/")
    return f"s3://{bucket}/{prefix}/{theme}_{type_}.parquet"


# ---------------------------------------------------------------------------
# Process each theme
# ---------------------------------------------------------------------------

for theme, type_ in THEMES:
    source = _source_path(theme, type_)
    table_name = f"{theme}_{type_}"
    full_table = f"glue_catalog.`{DB}`.`{table_name}`"

    print(f"[INFO] Processing {source} → {full_table}")

    df = spark.read.parquet(source)

    # Basic transformation: add an ingestion timestamp column
    df = df.withColumn("_ingested_at", F.current_timestamp())

    # Write as an Iceberg table (create or replace)
    (
        df.writeTo(full_table)
        .using("iceberg")
        .tableProperty("write.format.default", "parquet")
        .tableProperty("write.target-file-size-bytes", "536870912")
        .tableProperty("write.parquet.compression-codec", "zstd")
        .createOrReplace()
    )

    print(f"[INFO] Finished writing {full_table}")

# ---------------------------------------------------------------------------
# Commit the Glue job
# ---------------------------------------------------------------------------

job.commit()
