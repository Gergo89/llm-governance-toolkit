variable "aws_region" {
  description = "AWS region for Terraform state."
  type        = string
  default     = "eu-central-1"
}

variable "bucket_name" {
  description = "Globally unique S3 bucket name for Terraform state."
  type        = string
}

