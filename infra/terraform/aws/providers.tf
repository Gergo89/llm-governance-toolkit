provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.tags
  }
}

provider "random" {}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

