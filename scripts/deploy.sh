#!/bin/bash
# MRI Deploy Script — Builds, pushes, and deploys the API + frontend
# Usage: bash scripts/deploy.sh
set -e

REGION="ap-south-1"
TF_DIR="terraform/environments/dev"

echo "=== MRI Deployment Pipeline ==="
echo ""

# Step 0: Get Terraform outputs
echo "[0/5] Reading Terraform outputs..."
cd $TF_DIR
ECR_URL=$(terraform output -raw ecr_repository_url)
CLUSTER=$(terraform output -raw ecs_cluster_name)
SERVICE=$(terraform output -raw ecs_service_name)
FRONTEND_BUCKET=$(terraform output -raw frontend_bucket_name)
CF_DIST_ID=$(terraform output -raw cloudfront_distribution_id)
cd - > /dev/null

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "  ECR: $ECR_URL"
echo "  Cluster: $CLUSTER"
echo "  Service: $SERVICE"
echo "  Frontend Bucket: $FRONTEND_BUCKET"
echo ""

# Step 1: Build Docker image
echo "[1/5] Building API Docker image..."
docker build -f Dockerfile.api -t mri-api:latest .

# Step 2: Push to ECR
echo "[2/5] Pushing to ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URL
docker tag mri-api:latest $ECR_URL:latest
docker push $ECR_URL:latest

# Step 3: Force new ECS deployment
echo "[3/5] Deploying new ECS task..."
aws ecs update-service \
  --cluster $CLUSTER \
  --service $SERVICE \
  --force-new-deployment \
  --region $REGION \
  --no-cli-pager

# Step 4: Build and deploy frontend
echo "[4/5] Building and deploying frontend..."
cd frontend
npm install
npm run build
aws s3 sync dist/ s3://$FRONTEND_BUCKET/ --delete --region $REGION
cd ..

# Step 5: Invalidate CloudFront cache
echo "[5/5] Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
  --distribution-id $CF_DIST_ID \
  --paths "/*" \
  --region us-east-1 \
  --no-cli-pager

echo ""
echo "=== Deployment Complete! ==="
echo "  API:      http://$(cd $TF_DIR && terraform output -raw alb_dns_name)"
echo "  Frontend: https://$(cd $TF_DIR && terraform output -raw cloudfront_domain)"
