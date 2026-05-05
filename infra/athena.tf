# ---------------------------------------------------------------------------
# Athena workgroup
# ---------------------------------------------------------------------------

resource "aws_athena_workgroup" "overture" {
  name        = var.athena_workgroup_name
  description = "Workgroup for querying Overture Canada data via Iceberg."

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.bucket}/query-results/"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }

    bytes_scanned_cutoff_per_query = var.athena_bytes_scanned_cutoff

    # Enable Iceberg table support in Athena
    engine_version {
      selected_engine_version = "Athena engine version 3"
    }
  }
}

# ---------------------------------------------------------------------------
# Named queries – convenience queries pre-loaded in the workgroup
# ---------------------------------------------------------------------------

resource "aws_athena_named_query" "list_tables" {
  name        = "list-overture-tables"
  workgroup   = aws_athena_workgroup.overture.name
  database    = aws_glue_catalog_database.overture.name
  description = "List all tables in the Overture Canada database."
  query       = "SHOW TABLES IN ${var.glue_database_name};"
}

resource "aws_athena_named_query" "preview_places" {
  name        = "preview-places"
  workgroup   = aws_athena_workgroup.overture.name
  database    = aws_glue_catalog_database.overture.name
  description = "Preview the first 100 rows of the Overture Canada places table."
  query       = <<-SQL
    SELECT
        id,
        names.primary AS name,
        categories.primary AS category,
        confidence,
        ST_AsText(ST_GeomFromBinary(geometry)) AS wkt_geom
    FROM "${var.glue_database_name}"."places_place"
    LIMIT 100;
  SQL
}

resource "aws_athena_named_query" "preview_buildings" {
  name        = "preview-buildings"
  workgroup   = aws_athena_workgroup.overture.name
  database    = aws_glue_catalog_database.overture.name
  description = "Preview the first 100 rows of the Overture Canada buildings table."
  query       = <<-SQL
    SELECT
        id,
        height,
        num_floors,
        class,
        ST_AsText(ST_GeomFromBinary(geometry)) AS wkt_geom
    FROM "${var.glue_database_name}"."buildings_building"
    LIMIT 100;
  SQL
}

resource "aws_athena_named_query" "count_by_theme" {
  name        = "count-by-theme"
  workgroup   = aws_athena_workgroup.overture.name
  database    = aws_glue_catalog_database.overture.name
  description = "Row counts for all Overture Canada tables."
  query       = <<-SQL
    SELECT 'places' AS theme,       COUNT(*) AS row_count FROM "${var.glue_database_name}"."places_place"
    UNION ALL
    SELECT 'buildings' AS theme,    COUNT(*) AS row_count FROM "${var.glue_database_name}"."buildings_building"
    UNION ALL
    SELECT 'admins' AS theme,       COUNT(*) AS row_count FROM "${var.glue_database_name}"."admins_administrative_boundary"
    ORDER BY row_count DESC;
  SQL
}
