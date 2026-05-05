# ---------------------------------------------------------------------------
# IAM role for Glue jobs and crawlers
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "glue_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "glue_execution" {
  name               = "${local.name_prefix}-glue-execution-role"
  assume_role_policy = data.aws_iam_policy_document.glue_assume_role.json
}

# Attach AWS managed policy for common Glue permissions
resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# ---------------------------------------------------------------------------
# Custom policy: S3 access to the three project buckets
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "glue_s3" {
  statement {
    sid    = "ReadWriteRawData"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.raw_data.arn,
      "${aws_s3_bucket.raw_data.arn}/*",
    ]
  }

  statement {
    sid    = "ReadScripts"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.scripts.arn,
      "${aws_s3_bucket.scripts.arn}/*",
    ]
  }

  statement {
    sid    = "WriteAthenaResults"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.athena_results.arn,
      "${aws_s3_bucket.athena_results.arn}/*",
    ]
  }
}

resource "aws_iam_role_policy" "glue_s3" {
  name   = "glue-s3-access"
  role   = aws_iam_role.glue_execution.id
  policy = data.aws_iam_policy_document.glue_s3.json
}

# ---------------------------------------------------------------------------
# Glue Data Catalog permissions (read/write tables)
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "glue_catalog" {
  statement {
    sid    = "GlueCatalogAccess"
    effect = "Allow"
    actions = [
      "glue:GetDatabase",
      "glue:GetDatabases",
      "glue:CreateDatabase",
      "glue:UpdateDatabase",
      "glue:GetTable",
      "glue:GetTables",
      "glue:CreateTable",
      "glue:UpdateTable",
      "glue:DeleteTable",
      "glue:BatchCreatePartition",
      "glue:BatchDeletePartition",
      "glue:GetPartition",
      "glue:GetPartitions",
      "glue:CreatePartition",
    ]
    resources = [
      "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:catalog",
      "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:database/${var.glue_database_name}",
      "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${var.glue_database_name}/*",
    ]
  }
}

resource "aws_iam_role_policy" "glue_catalog" {
  name   = "glue-catalog-access"
  role   = aws_iam_role.glue_execution.id
  policy = data.aws_iam_policy_document.glue_catalog.json
}

# ---------------------------------------------------------------------------
# CloudWatch Logs (for Glue job logs)
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "glue_logs" {
  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [
      "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws-glue/*",
    ]
  }
}

resource "aws_iam_role_policy" "glue_logs" {
  name   = "glue-cloudwatch-logs"
  role   = aws_iam_role.glue_execution.id
  policy = data.aws_iam_policy_document.glue_logs.json
}
