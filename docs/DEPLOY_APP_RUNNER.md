# AWS App Runner Deployment Guide

This guide walks you through deploying LinkNodes to AWS App Runner using Docker containers. App Runner provides a fully managed service to run containerized web applications and APIs.

## Architecture Overview

LinkNodes on App Runner runs as **two separate services**:
- **Backend Service** — FastAPI engine serving the Chainlink API (`/v1/*` endpoints)
- **Frontend Service** — Static React SPA served via nginx

Each service runs in its own App Runner instance with independent scaling and monitoring.

## Prerequisites

1. **AWS Account** with appropriate IAM permissions (App Runner, ECR)
2. **AWS CLI** configured with your credentials
3. **Docker** installed locally
4. **Git** repository cloned locally

## Step 1: Prepare Docker Images

### Backend Image

1. Build the backend image:
```bash
cd backend
docker build -t linknodes-backend .
```

2. Test locally (optional):
```bash
docker run -p 8080:8080 -e PORT=8080 linknodes-backend
curl http://localhost:8080/healthz
```

### Frontend Image

1. Build the frontend image with the backend API URL:
```bash
cd frontend
docker build \
  --build-arg VITE_API_BASE_URL=https://your-backend-service.app-runner.aws.dev \
  -t linknodes-frontend .
```

**Important:** Replace `your-backend-service.app-runner.aws.dev` with your actual backend App Runner URL (see Step 3).

2. Test locally (optional):
```bash
docker run -p 8080:8080 -e PORT=8080 linknodes-frontend
```

## Step 2: Push Images to Amazon ECR

### Create ECR Repositories

```bash
# Create backend repository
aws ecr create-repository \
  --repository-name linknodes-backend \
  --region us-east-1

# Create frontend repository
aws ecr create-repository \
  --repository-name linknodes-frontend \
  --region us-east-1
```

### Authenticate with ECR

```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
```

Replace `<YOUR_AWS_ACCOUNT_ID>` with your actual AWS account ID.

### Tag and Push Images

```bash
# Backend
docker tag linknodes-backend:latest \
  <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/linknodes-backend:latest
docker push \
  <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/linknodes-backend:latest

# Frontend (after rebuilding with correct backend URL)
docker tag linknodes-frontend:latest \
  <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/linknodes-frontend:latest
docker push \
  <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/linknodes-frontend:latest
```

## Step 3: Create App Runner Services

### Backend Service

1. Open the AWS App Runner console
2. Click **Create service**
3. Select **Container registry** → **Amazon ECR**
4. Choose your backend ECR repository and tag (`latest`)
5. Configure deployment settings:
   - **ECR access role:** Create new or select existing
6. Configure service:
   - **Service name:** `linknodes-backend`
   - **Port:** `8080` (automatically detected from Dockerfile)
   - **Environment variables:** None required (PORT is auto-set by App Runner)
7. Configure health check:
   - **Path:** `/healthz`
   - **Interval:** 10 seconds
   - **Timeout:** 5 seconds
   - **Healthy threshold:** 1
   - **Unhealthy threshold:** 5
8. Configure auto scaling (optional):
   - **Max concurrency:** 100 (default)
   - **Min/Max instances:** 1-10
9. Review and **Create & deploy**

**Note the service URL** — something like `https://xyz123.us-east-1.awsapprunner.com`

### Frontend Service

**Important:** Before creating the frontend service, rebuild and repush the frontend image with the correct backend URL from Step 3.

```bash
cd frontend
docker build \
  --build-arg VITE_API_BASE_URL=https://xyz123.us-east-1.awsapprunner.com \
  -t linknodes-frontend .
docker tag linknodes-frontend:latest \
  <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/linknodes-frontend:latest
docker push \
  <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/linknodes-frontend:latest
```

Then create the service:

1. Open the AWS App Runner console
2. Click **Create service**
3. Select **Container registry** → **Amazon ECR**
4. Choose your frontend ECR repository and tag (`latest`)
5. Configure deployment settings:
   - **ECR access role:** Use same as backend
6. Configure service:
   - **Service name:** `linknodes-frontend`
   - **Port:** `8080`
7. Configure health check:
   - **Path:** `/`
   - **Interval:** 10 seconds
8. Review and **Create & deploy**

The frontend service URL is your **production URL** for LinkNodes.

## Step 4: Configure Custom Domain (Optional)

### Backend Domain

1. In the App Runner console, select your backend service
2. Go to **Custom domains**
3. Click **Link domain**
4. Enter your domain (e.g., `api.linknodes.io`)
5. Follow DNS verification steps (add CNAME records to your DNS provider)

### Frontend Domain

1. Select your frontend service
2. Go to **Custom domains**
3. Click **Link domain**
4. Enter your domain (e.g., `www.linknodes.io` or `linknodes.io`)
5. Follow DNS verification steps

### Rebuild Frontend with Custom Domain

After setting up the backend custom domain, rebuild the frontend to use it:

```bash
cd frontend
docker build \
  --build-arg VITE_API_BASE_URL=https://api.linknodes.io \
  -t linknodes-frontend .
docker tag linknodes-frontend:latest \
  <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/linknodes-frontend:latest
docker push \
  <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/linknodes-frontend:latest
```

App Runner will automatically deploy the updated image.

## Step 5: Monitor & Scale

### CloudWatch Logs

Both services automatically send logs to CloudWatch Logs:
- Backend: Check `/healthz` responses and API request logs
- Frontend: Check nginx access logs

### Metrics

App Runner provides built-in metrics:
- Request count and latency
- Active instances
- CPU/Memory utilization
- HTTP status codes (2xx, 4xx, 5xx)

### Auto Scaling

App Runner automatically scales based on:
- **Concurrent requests** (default: 100 per instance)
- **Instance count** (configured min/max)

For the free-tier LinkNodes setup:
- Backend: 1-3 instances (scales with API load)
- Frontend: 1-2 instances (mostly static content)

## Deployment Architecture

```
┌─────────────────────────────────────────────┐
│              Users / Internet               │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│  App Runner: Frontend Service                │
│  • nginx serving static React SPA            │
│  • VITE_API_BASE_URL → backend service       │
│  • Port 8080, auto-scaled                    │
└──────────────────┬───────────────────────────┘
                   │
                   │ API calls (/v1/*)
                   ▼
┌──────────────────────────────────────────────┐
│  App Runner: Backend Service                 │
│  • FastAPI + uvicorn                         │
│  • /healthz health check                     │
│  • Port 8080, auto-scaled                    │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
         Public RPC nodes (read-only)
```

## Cost Estimate

**App Runner Pricing (us-east-1):**
- **Compute:** $0.064/vCPU-hour + $0.007/GB-memory-hour
- **Build:** None (using pre-built ECR images)
- **Data transfer:** $0.09/GB out (after 100 GB/month free tier)

**Estimated Monthly Cost:**
- Backend (0.25 vCPU, 0.5 GB): ~$5-15/month (with free tier: ~$0-10)
- Frontend (0.25 vCPU, 0.5 GB): ~$3-8/month (mostly idle)
- **Total:** ~$8-23/month depending on traffic

**Free Tier:**
- First 6 vCPU-hours/day (25% of 1 vCPU for 24h = free)
- First 12 GB-hours/day (0.5 GB for 24h = free)

For low-traffic production: **~$10-15/month total**

## Continuous Deployment

### Option 1: Manual Updates

Rebuild and push images to ECR. App Runner detects changes and redeploys automatically.

### Option 2: GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to App Runner

on:
  push:
    branches: [main]

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      - uses: aws-actions/amazon-ecr-login@v2
      - name: Build and push backend
        run: |
          cd backend
          docker build -t ${{ secrets.ECR_REGISTRY }}/linknodes-backend:latest .
          docker push ${{ secrets.ECR_REGISTRY }}/linknodes-backend:latest

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      - uses: aws-actions/amazon-ecr-login@v2
      - name: Build and push frontend
        run: |
          cd frontend
          docker build \
            --build-arg VITE_API_BASE_URL=${{ secrets.BACKEND_URL }} \
            -t ${{ secrets.ECR_REGISTRY }}/linknodes-frontend:latest .
          docker push ${{ secrets.ECR_REGISTRY }}/linknodes-frontend:latest
```

Add secrets to your GitHub repository:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `ECR_REGISTRY` (e.g., `123456789012.dkr.ecr.us-east-1.amazonaws.com`)
- `BACKEND_URL` (your App Runner backend URL)

### Option 3: App Runner Source Connection

App Runner can build and deploy directly from GitHub (via Dockerfile):

1. Create service → **Source code repository**
2. Connect GitHub account
3. Select repository and branch
4. Configure build with Dockerfile path
5. Auto-deploys on every push

## Troubleshooting

### Backend Health Check Fails

Check CloudWatch logs:
```bash
aws logs tail /aws/apprunner/linknodes-backend/application --follow
```

Verify `/healthz` responds:
```bash
curl https://your-backend.awsapprunner.com/healthz
```

### Frontend Shows "Engine Unreachable"

1. Verify backend URL in frontend build args
2. Check CORS settings in `backend/main.py` (should allow all origins)
3. Test backend API directly:
```bash
curl https://your-backend.awsapprunner.com/v1/registry
```

### Slow Cold Starts

App Runner keeps at least 1 instance warm. If experiencing cold starts:
- Increase min instances to 2
- Consider keeping connections alive with health checks

## Security Recommendations

1. **Enable VPC:** Connect App Runner to VPC for private database access (if adding a DB later)
2. **WAF:** Add AWS WAF for DDoS protection on the frontend service
3. **Secrets:** Store sensitive config in AWS Secrets Manager (none required for LinkNodes currently)
4. **IAM Roles:** Use least-privilege IAM roles for ECR access

## Further Reading

- [AWS App Runner Documentation](https://docs.aws.amazon.com/apprunner/)
- [App Runner Pricing](https://aws.amazon.com/apprunner/pricing/)
- [App Runner Best Practices](https://docs.aws.amazon.com/apprunner/latest/dg/best-practices.html)
