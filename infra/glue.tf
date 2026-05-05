# ---------------------------------------------------------------------------
# Glue Data Catalog database
# ---------------------------------------------------------------------------

resource "aws_glue_catalog_database" "overture" {
  name        = var.glue_database_name
  description = "Overture Maps Canada dataset (raw parquet + Iceberg tables)."
}

# ---------------------------------------------------------------------------
# Glue crawler – catalogues the raw parquet files written by the ETL pipeline
# ---------------------------------------------------------------------------

resource "aws_glue_crawler" "overture_raw" {
  name          = "${local.name_prefix}-crawler"
  database_name = aws_glue_catalog_database.overture.name
  role          = aws_iam_role.glue_execution.arn
  description   = "Crawls raw Overture Canada parquet files and updates the Glue catalog."

  s3_target {
    path = "s3://${aws_s3_bucket.raw_data.bucket}/${var.raw_s3_prefix}/"
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }

  configuration = jsonencode({
    Version = 1.0
    CrawlerOutput = {
      Partitions = { AddOrUpdateBehavior = "InheritFromTable" }
      Tables     = { AddOrUpdateBehavior = "MergeNewColumns" }
    }
    Grouping = {
      TableGroupingPolicy = "CombineCompatibleSchemas"
    }
  })

  # Optional schedule – leave empty to trigger manually.
  dynamic "schedule" {
    for_each = var.glue_crawler_schedule != "" ? [var.glue_crawler_schedule] : []
    content {
      schedule_expression = schedule.value
    }
  }
}

# ---------------------------------------------------------------------------
# Glue ETL job – converts raw parquet to Apache Iceberg tables
# ---------------------------------------------------------------------------

resource "aws_glue_job" "overture_etl" {
  name              = "${local.name_prefix}-etl"
  role_arn          = aws_iam_role.glue_execution.arn
  glue_version      = var.glue_version
  worker_type       = var.glue_worker_type
  number_of_workers = var.glue_number_of_workers
  description       = "Converts raw Overture Canada parquet to Apache Iceberg tables."

  command {
    name            = "glueetl"
    script_location = "s3://${aws_s3_bucket.scripts.bucket}/${aws_s3_object.overture_etl_script.key}"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-glue-datacatalog"     = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--datalake-formats"            = "iceberg"
    "--conf"                        = "spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions --conf spark.sql.catalog.glue_catalog=org.apache.iceberg.spark.SparkCatalog --conf spark.sql.catalog.glue_catalog.warehouse=s3://${aws_s3_bucket.raw_data.bucket}/${var.iceberg_s3_prefix}/ --conf spark.sql.catalog.glue_catalog.catalog-impl=org.apache.iceberg.aws.glue.GlueCatalog --conf spark.sql.catalog.glue_catalog.io-impl=org.apache.iceberg.aws.s3.S3FileIO"
    "--source_bucket"               = aws_s3_bucket.raw_data.bucket
    "--source_prefix"               = var.raw_s3_prefix
    "--target_bucket"               = aws_s3_bucket.raw_data.bucket
    "--target_prefix"               = var.iceberg_s3_prefix
    "--database_name"               = aws_glue_catalog_database.overture.name
    "--TempDir"                     = "s3://${aws_s3_bucket.scripts.bucket}/glue-temp/"
    "--job-bookmark-option"         = "job-bookmark-disable"
  }

  execution_property {
    max_concurrent_runs = 1
  }
}
