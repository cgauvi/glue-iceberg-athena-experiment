output "raw_data_bucket" {
  description = "Name of the S3 bucket that stores raw Overture parquet files."
  value       = aws_s3_bucket.raw_data.id
}

output "raw_data_bucket_arn" {
  description = "ARN of the raw-data S3 bucket."
  value       = aws_s3_bucket.raw_data.arn
}

output "athena_results_bucket" {
  description = "Name of the S3 bucket used for Athena query results."
  value       = aws_s3_bucket.athena_results.id
}

output "scripts_bucket" {
  description = "Name of the S3 bucket that hosts Glue job scripts."
  value       = aws_s3_bucket.scripts.id
}

output "glue_database_name" {
  description = "Name of the Glue Data Catalog database."
  value       = aws_glue_catalog_database.overture.name
}

output "glue_job_name" {
  description = "Name of the Glue ETL job (parquet → Iceberg)."
  value       = aws_glue_job.overture_etl.name
}

output "glue_crawler_name" {
  description = "Name of the Glue crawler for raw parquet data."
  value       = aws_glue_crawler.overture_raw.name
}

output "glue_role_arn" {
  description = "ARN of the IAM role used by Glue jobs and crawlers."
  value       = aws_iam_role.glue_execution.arn
}

output "athena_workgroup_name" {
  description = "Name of the Athena workgroup."
  value       = aws_athena_workgroup.overture.name
}

output "etl_pipeline_command" {
  description = "Example CLI command to run the fetch-and-upload pipeline."
  value = join(" ", [
    "python -m etl.pipeline fetch-and-upload",
    "--bucket", aws_s3_bucket.raw_data.id,
    "--prefix", var.raw_s3_prefix,
    "--release", var.overture_release,
  ])
}
