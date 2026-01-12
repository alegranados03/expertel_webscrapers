# =============================================================================
# NOTIFICATIONS MODULE
# =============================================================================
# SNS Topic + Lambda function for multi-channel notifications
# Supports: Email (SES), Slack, Microsoft Teams
# =============================================================================

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

# -----------------------------------------------------------------------------
# SNS TOPIC
# -----------------------------------------------------------------------------

resource "aws_sns_topic" "scraper_notifications" {
  name = "${var.app_name}-${var.environment}-notifications"

  tags = var.tags
}

# -----------------------------------------------------------------------------
# SNS TOPIC POLICY
# -----------------------------------------------------------------------------

resource "aws_sns_topic_policy" "default" {
  arn = aws_sns_topic.scraper_notifications.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowEC2Publish"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action   = "sns:Publish"
        Resource = aws_sns_topic.scraper_notifications.arn
      },
      {
        Sid    = "AllowLambdaPublish"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action   = "sns:Publish"
        Resource = aws_sns_topic.scraper_notifications.arn
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# EMAIL SUBSCRIPTION (Direct SNS)
# -----------------------------------------------------------------------------

resource "aws_sns_topic_subscription" "email" {
  count     = length(var.notification_emails)
  topic_arn = aws_sns_topic.scraper_notifications.arn
  protocol  = "email"
  endpoint  = var.notification_emails[count.index]
}

# -----------------------------------------------------------------------------
# LAMBDA FUNCTION FOR SLACK/TEAMS
# -----------------------------------------------------------------------------

resource "aws_iam_role" "lambda_notifications" {
  name = "${var.app_name}-${var.environment}-lambda-notifications"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "lambda_notifications" {
  name = "${var.app_name}-${var.environment}-lambda-notifications-policy"
  role = aws_iam_role.lambda_notifications.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = [
          "arn:aws:ssm:${var.aws_region}:${var.aws_account_id}:parameter/${var.app_name}/${var.environment}/slack/*",
          "arn:aws:ssm:${var.aws_region}:${var.aws_account_id}:parameter/${var.app_name}/${var.environment}/teams/*"
        ]
      }
    ]
  })
}

# Lambda function code
data "archive_file" "lambda_notifications" {
  type        = "zip"
  output_path = "${path.module}/lambda_notifications.zip"

  source {
    content  = <<-EOF
import json
import urllib.request
import urllib.error
import boto3
import os

ssm = boto3.client('ssm')

def get_webhook_url(param_name):
    """Get webhook URL from SSM Parameter Store."""
    try:
        response = ssm.get_parameter(Name=param_name, WithDecryption=True)
        return response['Parameter']['Value']
    except Exception as e:
        print(f"Error getting parameter {param_name}: {e}")
        return None

def send_slack(webhook_url, message, subject):
    """Send notification to Slack."""
    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f":robot_face: {subject}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Environment:* {os.environ.get('ENVIRONMENT', 'unknown')}"
                    }
                ]
            }
        ]
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(webhook_url, data=data, headers={'Content-Type': 'application/json'})

    try:
        with urllib.request.urlopen(req) as response:
            return response.status == 200
    except urllib.error.URLError as e:
        print(f"Slack error: {e}")
        return False

def send_teams(webhook_url, message, subject):
    """Send notification to Microsoft Teams."""
    # Determine color based on subject
    color = "0076D7"  # Default blue
    if "error" in subject.lower() or "failed" in subject.lower():
        color = "FF0000"  # Red for errors
    elif "success" in subject.lower() or "completed" in subject.lower():
        color = "00FF00"  # Green for success

    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": color,
        "summary": subject,
        "sections": [
            {
                "activityTitle": f"ExpertelIQ2 Scraper - {subject}",
                "facts": [
                    {
                        "name": "Environment",
                        "value": os.environ.get('ENVIRONMENT', 'unknown')
                    },
                    {
                        "name": "Message",
                        "value": message
                    }
                ],
                "markdown": True
            }
        ]
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(webhook_url, data=data, headers={'Content-Type': 'application/json'})

    try:
        with urllib.request.urlopen(req) as response:
            return response.status == 200
    except urllib.error.URLError as e:
        print(f"Teams error: {e}")
        return False

def handler(event, context):
    """Lambda handler for SNS notifications."""
    print(f"Received event: {json.dumps(event)}")

    app_name = os.environ.get('APP_NAME', 'experteliq2-scraper')
    environment = os.environ.get('ENVIRONMENT', 'unknown')

    results = {
        'slack': False,
        'teams': False
    }

    for record in event.get('Records', []):
        sns_message = record.get('Sns', {})
        subject = sns_message.get('Subject', 'Scraper Notification')
        message = sns_message.get('Message', '')

        print(f"Processing notification: {subject}")

        # Send to Slack
        slack_webhook = get_webhook_url(f"/{app_name}/{environment}/slack/webhook-url")
        if slack_webhook:
            results['slack'] = send_slack(slack_webhook, message, subject)
            print(f"Slack notification: {'sent' if results['slack'] else 'failed'}")

        # Send to Teams
        teams_webhook = get_webhook_url(f"/{app_name}/{environment}/teams/webhook-url")
        if teams_webhook:
            results['teams'] = send_teams(teams_webhook, message, subject)
            print(f"Teams notification: {'sent' if results['teams'] else 'failed'}")

    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }
EOF
    filename = "index.py"
  }
}

resource "aws_lambda_function" "notifications" {
  function_name = "${var.app_name}-${var.environment}-notifications"
  role          = aws_iam_role.lambda_notifications.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 30

  filename         = data.archive_file.lambda_notifications.output_path
  source_code_hash = data.archive_file.lambda_notifications.output_base64sha256

  environment {
    variables = {
      APP_NAME    = var.app_name
      ENVIRONMENT = var.environment
    }
  }

  tags = var.tags
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_notifications" {
  name              = "/aws/lambda/${aws_lambda_function.notifications.function_name}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# SNS Subscription for Lambda
resource "aws_sns_topic_subscription" "lambda" {
  topic_arn = aws_sns_topic.scraper_notifications.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.notifications.arn
}

# Lambda permission for SNS
resource "aws_lambda_permission" "sns" {
  statement_id  = "AllowSNSInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.notifications.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.scraper_notifications.arn
}
