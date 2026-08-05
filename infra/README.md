# S3 bucket for CategoryRAG document storage
#
# Usage:
#   cd infra
#   terraform init
#   terraform apply
#
# Put outputs into .env:
#   S3_BUCKET=<bucket_name>
#   AWS_REGION=<aws_region>
#
# Also set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY (or use an IAM role).
