variable "aws_region" {
  default = "us-east-1"
}

variable "cluster_name" {
  default = "orderflow-eks"
}

variable "github_repo" {
  description = "GitHub repo allowed to assume the CI/CD role, format: org/repo"
  default     = "ARIESH-git/Orderflow-Project-Repo"
}
