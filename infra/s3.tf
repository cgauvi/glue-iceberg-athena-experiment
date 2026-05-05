# ---------------------------------------------------------------------------
# Locals – shared bucket naming
# ---------------------------------------------------------------------------

locals {
  # Use account ID as default suffix to guarantee global uniqueness.
  bucket_suffix = var.raw_data_bucket_suffix != "" ? var.raw_data_bucket_suffix : data.aws_caller_identity.current.account_id
  name_prefix   = "${var.project_name}-${var.environment}"
}

# ---------------------------------------------------------------------------
# Raw Overture data bucket
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "raw_data" {
  bucket        = "${local.name_prefix}-raw-${local.bucket_suffix}"
  force_destroy = var.force_destroy_buckets
}

resource "aws_s3_bucket_versioning" "raw_data" {
  bucket = aws_s3_bucket.raw_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw_data" {
  bucket = aws_s3_bucket.raw_data.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "raw_data" {
  bucket                  = aws_s3_bucket.raw_data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ---------------------------------------------------------------------------
# Athena query results bucket
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "athena_results" {
  bucket        = "${local.name_prefix}-athena-results-${local.bucket_suffix}"
  force_destroy = var.force_destroy_buckets
}

resource "aws_s3_bucket_server_side_encryption_configuration" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "athena_results" {
  bucket                  = aws_s3_bucket.athena_results.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle: expire query results after 30 days to control storage costs.
resource "aws_s3_bucket_lifecycle_configuration" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id
  rule {
    id     = "expire-query-results"
    status = "Enabled"
    expiration {
      days = 30
    }
  }
}

# ---------------------------------------------------------------------------
# Glue job scripts bucket
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "scripts" {
  bucket        = "${local.name_prefix}-scripts-${local.bucket_suffix}"
  force_destroy = var.force_destroy_buckets
}

resource "aws_s3_bucket_server_side_encryption_configuration" "scripts" {
  bucket = aws_s3_bucket.scripts.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "scripts" {
  bucket                  = aws_s3_bucket.scripts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Upload the Glue PySpark script
resource "aws_s3_object" "overture_etl_script" {
  bucket = aws_s3_bucket.scripts.id
  key    = "glue_jobs/overture_etl.py"
  source = "${path.module}/../glue_jobs/overture_etl.py"
  etag   = filemd5("${path.module}/../glue_jobs/overture_etl.py")
}
