resource "aws_ecr_repository" "orderflow" {
  for_each = toset(["orderflow-api", "orderflow-inventory-consumer", "orderflow-notification-consumer"])
  name     = each.value
}
