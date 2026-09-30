# Quick Start: AWS App Runner Deployment

This is a condensed version of the full deployment guide. For detailed explanations, see [DEPLOY_APP_RUNNER.md](DEPLOY_APP_RUNNER.md).

## Prerequisites
- AWS Account with CLI configured
- Docker installed locally

## Step 1: Set Your AWS Account ID
```bash
export AWS_ACCOUNT_ID=123456789012  # Replace with your actual account ID
export AWS_REGION=us-east-1
```

## Step 2: Create ECR Repositories
```bash
aws ecr create-repository --repository-name linknodes-backend --region $AWS_REGION
aws ecr create-repository --repository-name linknodes-frontend --region $AWS_REGION
```

## Step 3: Build and Push Backend
```bash
cd backend
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

docker build -t linknodes-backend .
docker tag linknodes-backend:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/linknodes-backend:latest
docker push \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/linknodes-backend:latest
```

## Step 4: Create Backend App Runner Service

**Via AWS Console:**
1. Open App Runner → Create service
2. Source: ECR → `linknodes-backend:latest`
3. Port: `8080`
4. Health check path: `/healthz`
5. Create & Deploy

**Or via AWS CLI:**
```bash
# First, create an IAM role for App Runner to access ECR
# See DEPLOY_APP_RUNNER.md for role creation details

aws apprunner create-service \
  --service-name linknodes-backend \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "'$AWS_ACCOUNT_ID'.dkr.ecr.'$AWS_REGION'.amazonaws.com/linknodes-backend:latest",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "8080"
      }
    },
    "AutoDeploymentsEnabled": true,
    "AuthenticationConfiguration": {
      "AccessRoleArn": "arn:aws:iam::'$AWS_ACCOUNT_ID':role/AppRunnerECRAccessRole"
    }
  }' \
  --health-check-configuration '{
    "Protocol": "HTTP",
    "Path": "/healthz",
    "Interval": 10,
    "Timeout": 5,
    "HealthyThreshold": 1,
    "UnhealthyThreshold": 5
  }' \
  --region $AWS_REGION
```

**Save the backend service URL** (e.g., `https://xyz123.us-east-1.awsapprunner.com`)

## Step 5: Build and Push Frontend

```bash
export BACKEND_URL=https://xyz123.us-east-1.awsapprunner.com  # Use your actual backend URL

cd ../frontend
docker build \
  --build-arg VITE_API_BASE_URL=$BACKEND_URL \
  -t linknodes-frontend .
docker tag linknodes-frontend:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/linknodes-frontend:latest
docker push \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/linknodes-frontend:latest
```

## Step 6: Create Frontend App Runner Service

**Via AWS Console:**
1. Open App Runner → Create service
2. Source: ECR → `linknodes-frontend:latest`
3. Port: `8080`
4. Health check path: `/`
5. Create & Deploy

**Or via AWS CLI:**
```bash
aws apprunner create-service \
  --service-name linknodes-frontend \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "'$AWS_ACCOUNT_ID'.dkr.ecr.'$AWS_REGION'.amazonaws.com/linknodes-frontend:latest",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "8080"
      }
    },
    "AutoDeploymentsEnabled": true,
    "AuthenticationConfiguration": {
      "AccessRoleArn": "arn:aws:iam::'$AWS_ACCOUNT_ID':role/AppRunnerECRAccessRole"
    }
  }' \
  --health-check-configuration '{
    "Protocol": "HTTP",
    "Path": "/",
    "Interval": 10,
    "Timeout": 5,
    "HealthyThreshold": 1,
    "UnhealthyThreshold": 5
  }' \
  --region $AWS_REGION
```

## Step 7: Test Your Deployment

```bash
# Get frontend URL
export FRONTEND_URL=$(aws apprunner describe-service \
  --service-arn $(aws apprunner list-services --query 'ServiceSummaryList[?ServiceName==`linknodes-frontend`].ServiceArn' --output text) \
  --query 'Service.ServiceUrl' --output text)

# Test backend health
curl $BACKEND_URL/healthz

# Test backend API
curl $BACKEND_URL/v1/registry | jq '.version'

# Open frontend
open https://$FRONTEND_URL
```

## Done!

Your LinkNodes application is now running on AWS App Runner:
- **Backend API:** `$BACKEND_URL`
- **Frontend:** `https://$FRONTEND_URL`

## Next Steps

- **Custom Domain:** See [DEPLOY_APP_RUNNER.md](DEPLOY_APP_RUNNER.md) for domain setup
- **CI/CD:** Add GitHub Actions for automatic deployments
- **Monitoring:** Check CloudWatch Logs and App Runner metrics

## Cost Estimate

With low traffic (< 100 requests/day):
- ~$10-15/month total
- Free tier covers ~25% of 1 vCPU for 24h/day

## Troubleshooting

### Backend health check fails
```bash
aws logs tail /aws/apprunner/linknodes-backend/application --follow
```

### Frontend shows "Engine unreachable"
- Verify backend URL was set during frontend build
- Check CORS is enabled in backend (it is by default)
- Test backend API directly: `curl $BACKEND_URL/v1/registry`

### Need to update frontend with new backend URL?
Rebuild and repush frontend image (Step 5) with the new URL.
