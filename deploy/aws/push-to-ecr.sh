#!/usr/bin/env bash
# Build the backend image and push it to Amazon ECR.
#
# Prereqs: AWS CLI v2 configured (`aws configure`) and Docker running.
# Usage:   AWS_REGION=ap-south-1 ./deploy/aws/push-to-ecr.sh
set -euo pipefail

AWS_REGION="${AWS_REGION:-ap-south-1}"
REPO="forex-ai"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
ECR="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# 1. Create the ECR repo if it doesn't exist yet.
aws ecr describe-repositories --repository-names "$REPO" --region "$AWS_REGION" >/dev/null 2>&1 \
  || aws ecr create-repository --repository-name "$REPO" --region "$AWS_REGION" >/dev/null

# 2. Authenticate Docker to ECR.
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR"

# 3. Build, tag, push (run from the repo root so the Dockerfile context is correct).
docker build -t "${REPO}:latest" .
docker tag "${REPO}:latest" "${ECR}/${REPO}:latest"
docker push "${ECR}/${REPO}:latest"

echo "✅ Pushed ${ECR}/${REPO}:latest"
