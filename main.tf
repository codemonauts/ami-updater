terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.47.0"
    }
  }
}

provider "aws" {
  profile = var.profile
  region  = var.region
}

variable "lambda_function_name" {
  default     = "ami-updater"
  type        = string
  description = "The name for the Lambda function. It will be used as prefix for roles, policies and log group."
}

variable "log_group_name" {
  default     = "/aws/lambda/ami-updater"
  type        = string
  description = "The name of the log group in CloudWatch Logs."
}

variable "keep_amis" {
  type        = number
  description = "Number of AMIs per Launch Template to be kept."
  default     = 3
}

variable "region" {
  type        = string
  description = "The region where the Lambda will be configured."
}

variable "profile" {
  type        = string
  description = "The AWS CLI profile to use. This is the AWS account to install the function."
}

data "aws_caller_identity" "current" {}

# Lambda assume policy

data "aws_iam_policy_document" "lambda_assume_role_policy" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

# Scheduler assume policy

data "aws_iam_policy_document" "scheduler_assume_role_policy" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

# Lambda logging policy

data "aws_iam_policy_document" "lambda_logging_policy" {
  statement {
    effect = "Allow"

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]

    resources = ["arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:${var.log_group_name}:*"]
  }
}

# Lambda EC2 policy

data "aws_iam_policy_document" "lambda_ec2_policy" {
  statement {
    effect = "Allow"

    actions = [
      "ec2:DeregisterImage"
    ]

    resources = ["arn:aws:ec2:${var.region}::image/*"]
  }
  statement {
    effect = "Allow"

    actions = [
      "ec2:DescribeImages",
      "ec2:DescribeLaunchTemplates",
      "ec2:DescribeLaunchTemplateVersions"
    ]

    resources = ["*"]
  }
  statement {
    effect = "Allow"

    actions = [
      "ec2:ModifyLaunchTemplate",
      "ec2:DeleteLaunchTemplateVersions",
      "ec2:CreateLaunchTemplateVersion"
    ]

    resources = ["arn:aws:ec2:${var.region}:${data.aws_caller_identity.current.account_id}:launch-template/*"]
  }
  statement {
    effect = "Allow"

    actions = [
      "ec2:DeleteSnapshot"
    ]

    resources = ["arn:aws:ec2:${var.region}::snapshot/*"]
  }
}

# Scheduler Lambda invoke policy

data "aws_iam_policy_document" "scheduler_invoke_lambda_policy" {
  statement {
    effect = "Allow"

    actions = [
      "lambda:InvokeFunction"
    ]

    resources = [aws_lambda_function.lambda_function.arn]
  }
}

# Lambda role with assume policy and inline policies for logging and EC2 access

resource "aws_iam_role" "lambda_role" {
  name               = "${var.lambda_function_name}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy.json
  inline_policy {
    name   = "logging"
    policy = data.aws_iam_policy_document.lambda_logging_policy.json
  }
  inline_policy {
    name   = "launch-template-management"
    policy = data.aws_iam_policy_document.lambda_ec2_policy.json
  }
}

# Scheduler role with assume policy and inline policies for invoking Lambda function

resource "aws_iam_role" "scheduler_role" {
  name               = "${var.lambda_function_name}-scheduler-role"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role_policy.json
  inline_policy {
    name   = "invoke-lambda-function"
    policy = data.aws_iam_policy_document.scheduler_invoke_lambda_policy.json
  }
}

# Cloudwatch log group

resource "aws_cloudwatch_log_group" "cw_log_group" {
  name              = var.log_group_name
  retention_in_days = 14
}

# Scheduler rule

resource "aws_scheduler_schedule" "scheduler_daily" {
  name        = "${var.lambda_function_name}-daily"
  description = "Update the Launch Templates every 12 hours"
  group_name  = "default"
  flexible_time_window {
    mode = "OFF"
  }
  schedule_expression = "rate(12 hours)"
  target {
    arn      = aws_lambda_function.lambda_function.arn
    role_arn = aws_iam_role.scheduler_role.arn

  }
}

# Lambda function

resource "aws_lambda_function" "lambda_function" {
  filename         = "package.zip"
  function_name    = var.lambda_function_name
  role             = aws_iam_role.lambda_role.arn
  handler          = "main.lambda_handler"
  source_code_hash = fileexists("package.zip") ? filebase64sha256("package.zip") : null

  runtime       = "python3.13"
  architectures = ["arm64"]
  timeout       = 60
  publish       = true

  environment {
    variables = {
      KEEP_AMIS = var.keep_amis
    }
  }
}