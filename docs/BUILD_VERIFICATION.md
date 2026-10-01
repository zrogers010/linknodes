# Docker Build Verification

This document provides commands to verify that both Docker images build successfully.

## Prerequisites

- Docker installed and running
- Sufficient disk space for image builds

## Backend Build

```bash
cd backend
docker build -t linknodes-backend:test .
```

Expected output:
- Successfully installs Python dependencies from `requirements.txt`
- Copies application files (`main.py`, `registry.json`, `operators.json`, `build_registry.py`)
- Creates non-root user `appuser`
- Sets `PORT=8080` environment variable
- Image built successfully

### Test Backend Locally

```bash
docker run -p 8080:8080 linknodes-backend:test
```

Then in another terminal:
```bash
# Test health endpoint
curl http://localhost:8080/healthz

# Expected output:
# {"status":"ok","registry_version":"...","networks":13,"feeds":1400,"cache_entries":0}

# Test registry endpoint
curl http://localhost:8080/v1/registry | jq '.version'

# Test a feed query
curl http://localhost:8080/v1/query/ethereum/eth-usd | jq '.payload.price'
```

## Frontend Build

### Build with Empty API URL (for local docker-compose)

```bash
cd frontend
docker build -t linknodes-frontend:test .
```

### Build with Specific API URL (for production)

```bash
cd frontend
docker build \
  --build-arg VITE_API_BASE_URL=https://api.example.com \
  -t linknodes-frontend:prod .
```

Expected output:
- Installs npm dependencies
- Builds Vite/React application
- Multi-stage build copies dist to nginx container
- Creates non-root user `appuser`
- Sets up nginx template with `$PORT` support
- Image built successfully

### Test Frontend Locally

```bash
# Test with local API (requires backend running)
docker run -p 8080:8080 -e PORT=8080 linknodes-frontend:test
```

Open browser to http://localhost:8080

Expected behavior:
- Homepage loads with Chainlink branding
- Navigation works (Data Feeds, CCIP, Functions, VRF, Automation)
- If backend is running: Feed catalog loads successfully
- If backend is NOT running: Shows "Engine unreachable" error (expected)

## Docker Compose Build

Test the complete local setup:

```bash
cd /path/to/linknodes
docker compose up --build
```

Expected output:
- Both backend and frontend images build successfully
- Backend starts on port 8080 (internal)
- Frontend starts and proxies to backend
- Frontend accessible at http://localhost:8080

Test the complete stack:
```bash
# Should show feed catalog
curl http://localhost:8080/v1/registry | jq '.version'

# Should show homepage HTML
curl http://localhost:8080/
```

## Build Size Reference

Approximate image sizes:

- **Backend:** ~180-200 MB
  - Base: `python:3.12-slim` (~130 MB)
  - Dependencies: ~50-70 MB (FastAPI, uvicorn, web3.py)

- **Frontend:** ~40-45 MB
  - Base: `nginx:1.27-alpine` (~40 MB)
  - Static assets: ~2-5 MB (Vite production build)

## Common Build Issues

### Backend: pip install fails
- Check network connectivity
- Verify `requirements.txt` is present
- Try updating pip: `pip install --upgrade pip`

### Frontend: npm ci fails
- Delete `node_modules` and `package-lock.json`, then retry
- Check Node.js version compatibility (requires Node 22)

### Frontend: Build stage fails
- Check for TypeScript errors: `npm run build` locally first
- Verify all imports are correct

### Permission denied
- Ensure Docker daemon is running
- Check file permissions in the repository

## CI/CD Build Verification

For CI environments, add build checks:

```bash
# Backend
docker build --progress=plain -t test-backend ./backend

# Frontend (production)
docker build --progress=plain \
  --build-arg VITE_API_BASE_URL=https://api.example.com \
  -t test-frontend ./frontend

# Both should exit with code 0
echo "Build verification passed!"
```

## Next Steps

After verifying builds locally:
1. Tag images with ECR repository URIs
2. Push to Amazon ECR
3. Create App Runner services
4. See `DEPLOY_APP_RUNNER.md` for full deployment guide
