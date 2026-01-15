# =============================================================================
# SCRAPER INSTANCE MODULE - OUTPUTS
# =============================================================================

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.scraper.id
}

output "instance_private_ip" {
  description = "Private IP of the scraper instance"
  value       = aws_instance.scraper.private_ip
}

output "instance_public_ip" {
  description = "Public IP of the scraper instance"
  value       = var.create_elastic_ip ? aws_eip.scraper[0].public_ip : aws_instance.scraper.public_ip
}

output "security_group_id" {
  description = "Security group ID"
  value       = aws_security_group.scraper.id
}

output "iam_role_arn" {
  description = "IAM role ARN"
  value       = aws_iam_role.scraper.arn
}

output "iam_instance_profile_name" {
  description = "IAM instance profile name"
  value       = aws_iam_instance_profile.scraper.name
}

output "novnc_url" {
  description = "URL to access noVNC"
  value       = "https://${var.create_elastic_ip ? aws_eip.scraper[0].public_ip : aws_instance.scraper.public_ip}/vnc/"
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i ${var.key_name}.pem ubuntu@${var.create_elastic_ip ? aws_eip.scraper[0].public_ip : aws_instance.scraper.public_ip}"
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.scraper.name
}
