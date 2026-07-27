# Deploying forex-ai to AWS (ECS Fargate)

Runs the FastAPI backend as a containerized service on **ECS Fargate**, with the image in
**ECR**, secrets in **Secrets Manager**, logs in **CloudWatch**, and durable artifacts
(the intraday forward-test log + stats) in **S3** via the app's boto3 integration.

```
Docker image ──► ECR ──► ECS Fargate task ──► CloudWatch logs
                                 │
                                 ├── Secrets Manager (API keys, injected as env)
                                 └── S3 (forward-test log / stats, via IAM task role)
```

## Why these services
- **ECR** — private registry for the image `push-to-ecr.sh` builds.
- **ECS Fargate** — serverless containers; no EC2 to manage. `ecs-task-definition.json` defines it.
- **Secrets Manager** — `POLYGON_API_KEY` / `OPENAI_API_KEY` / `TELEGRAM_BOT_TOKEN` are injected
  as env vars at launch (`secrets` block) — never baked into the image.
- **S3** — `app/services/aws_s3.py` (boto3) writes the paper-trading track record to
  `s3://$AWS_S3_BUCKET/forward-test/…`, so it survives task replacement. Access is granted by the
  **IAM task role** (`taskRoleArn`) — the boto3 default credential chain picks it up, no keys in code.
- **CloudWatch Logs** — container stdout via the `awslogs` driver.

## One-time setup
```bash
export AWS_REGION=ap-south-1

# S3 bucket for artifacts
aws s3 mb "s3://forex-ai-artifacts" --region "$AWS_REGION"

# Secrets (repeat per key)
aws secretsmanager create-secret --name forex-ai/POLYGON_API_KEY   --secret-string "…"
aws secretsmanager create-secret --name forex-ai/OPENAI_API_KEY    --secret-string "…"
aws secretsmanager create-secret --name forex-ai/TELEGRAM_BOT_TOKEN --secret-string "…"

# CloudWatch log group
aws logs create-log-group --log-group-name /ecs/forex-ai --region "$AWS_REGION"
```
Create two IAM roles: `ecsTaskExecutionRole` (managed policy `AmazonECSTaskExecutionRolePolicy`
+ Secrets Manager read) and `forex-ai-task-role` (an inline policy allowing `s3:PutObject`/`s3:GetObject`
on `arn:aws:s3:::forex-ai-artifacts/*`).

## Deploy
```bash
# 1. Build + push the image
AWS_REGION=$AWS_REGION ./deploy/aws/push-to-ecr.sh

# 2. Fill in <ACCOUNT_ID> / <REGION> in ecs-task-definition.json, then register it
aws ecs register-task-definition --cli-input-json file://deploy/aws/ecs-task-definition.json

# 3. Create a cluster + service (behind an ALB for the dashboard/API)
aws ecs create-cluster --cluster-name forex-ai
aws ecs create-service --cluster forex-ai --service-name forex-ai \
  --task-definition forex-ai --desired-count 1 --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-…],securityGroups=[sg-…],assignPublicIp=ENABLED}"
```

## Verify the S3 integration
Once the task role is attached, `GET /aws/status` returns `"configured": true`, and
`POST /aws/backup` pushes the forward-test log to S3. Locally (no AWS), both no-op gracefully.
