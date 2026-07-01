output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "ecr_repository_urls" {
  value = { for k, v in aws_ecr_repository.orderflow : k => v.repository_url }
}

output "github_actions_role_arn" {
  value = aws_iam_role.github_actions.arn
}
