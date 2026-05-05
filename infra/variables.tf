variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "ca-central-1"
}

variable "project_name" {
  description = "Short name used as a prefix for all resources."
  type        = string
  default     = "overture-canada"
}

variable "environment" {
  description = "Deployment environment label (e.g. dev, staging, prod)."
  type        = string
  default     = "dev"
}

# ---------------------------------------------------------------------------
# S3
# ---------------------------------------------------------------------------

variable "raw_data_bucket_suffix" {
  description = "Optional suffix appended to the raw-data bucket name to ensure global uniqueness. Defaults to the AWS account ID."
  type        = string
  default     = ""
}

variable "force_destroy_buckets" {
  description = "Allow Terraform to destroy non-empty S3 buckets. Only set true in non-production environments."
  type        = bool
  default     = false
}

# ---------------------------------------------------------------------------
# Overture / ETL
# ---------------------------------------------------------------------------

variable "overture_release" {
  description = "Overture Maps release tag (e.g. 2025-01-22.0)."
  type        = string
  default     = "2025-01-22.0"
}

variable "raw_s3_prefix" {
  description = "S3 key prefix for raw Overture parquet files."
  type        = string
  default     = "canada/raw"
}

variable "iceberg_s3_prefix" {
  description = "S3 key prefix for the Iceberg warehouse."
  type        = string
  default     = "canada/iceberg"
}

# ---------------------------------------------------------------------------
# Glue
# ---------------------------------------------------------------------------

variable "glue_database_name" {
  description = "Name of the Glue Data Catalog database."
  type        = string
  default     = "overture_canada"
}

variable "glue_version" {
  description = "AWS Glue version for the ETL job."
  type        = string
  default     = "4.0"
}

variable "glue_worker_type" {
  description = "Glue worker type for the ETL job."
  type        = string
  default     = "G.1X"
}

variable "glue_number_of_workers" {
  description = "Number of Glue workers for the ETL job."
  type        = number
  default     = 2
}

variable "glue_crawler_schedule" {
  description = "Cron schedule for the Glue crawler (leave empty to disable)."
  type        = string
  default     = ""
}

# ---------------------------------------------------------------------------
# Athena
# ---------------------------------------------------------------------------

variable "athena_workgroup_name" {
  description = "Name of the Athena workgroup."
  type        = string
  default     = "overture-canada"
}

variable "athena_bytes_scanned_cutoff" {
  description = "Maximum bytes scanned per Athena query (cost control). Default: 10 GB."
  type        = number
  default     = 10737418240
}
