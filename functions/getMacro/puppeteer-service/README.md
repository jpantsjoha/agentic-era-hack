# Puppeteer Screenshot Service

## Dockerfile for Puppeteer Service

First, let's create a Dockerfile for the Puppeteer service:

```dockerfile:functions/getMacro/puppeteer-service/Dockerfile
# Use Node.js LTS as the base image
FROM node:20-slim

# Set working directory
WORKDIR /app

# Install dependencies required for Puppeteer
RUN apt-get update && apt-get install -y \
    fonts-liberation \
    gconf-service \
    libappindicator1 \
    libasound2 \
    libatk1.0-0 \
    libcairo2 \
    libcups2 \
    libfontconfig1 \
    libgbm-dev \
    libgdk-pixbuf2.0-0 \
    libgtk-3-0 \
    libicu-dev \
    libjpeg-dev \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpng-dev \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    xdg-utils \
    wget \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy package.json and package-lock.json (if available)
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Expose the port the app runs on
EXPOSE 8080

# Set NODE_ENV to production
ENV NODE_ENV=production

# Command to run the application
CMD ["npm", "start"]
```

## cloudbuild.yaml for Puppeteer Service

Now, let's create a cloudbuild.yaml file for the Puppeteer service:

```yaml:functions/getMacro/puppeteer-service/cloudbuild.yaml
# Cloud Build configuration for Puppeteer Screenshot Service
steps:
  # Build the container image
  - name: "gcr.io/cloud-builders/docker"
    args:
      [
        "build",
        "-t",
        "$_REGION-docker.pkg.dev/$PROJECT_ID/$_ARTIFACT_REGISTRY_REPO_NAME/puppeteer-screenshot-service",
        "./functions/getMacro/puppeteer-service",
      ]
  
  # Push the container image to Artifact Registry
  - name: "gcr.io/cloud-builders/docker"
    args:
      [
        "push",
        "$_REGION-docker.pkg.dev/$PROJECT_ID/$_ARTIFACT_REGISTRY_REPO_NAME/puppeteer-screenshot-service",
      ]

  # Deploy to Cloud Run
  - name: "gcr.io/cloud-builders/gcloud"
    id: deploy-service
    entrypoint: gcloud
    args:
      - "run"
      - "deploy"
      - "puppeteer-screenshot-service"
      - "--image"
      - "$_REGION-docker.pkg.dev/$PROJECT_ID/$_ARTIFACT_REGISTRY_REPO_NAME/puppeteer-screenshot-service"
      - "--region"
      - "${_REGION}"
      - "--platform"
      - "managed"
      - "--allow-unauthenticated"  # Remove if you want to secure the service
      - "--memory"
      - "2Gi"  # Puppeteer needs sufficient memory
      - "--cpu"
      - "2"
      - "--concurrency"
      - "10"
      - "--timeout"
      - "300s"  # Longer timeout for screenshot operations
      - "--set-env-vars"
      - "COMMIT_SHA=${COMMIT_SHA}"

  # Fetch Service URL and log it
  - name: "gcr.io/cloud-builders/gcloud"
    id: fetch-service-url
    entrypoint: /bin/bash
    args:
      - "-c"
      - |
        echo "Puppeteer Screenshot Service deployed at: $(gcloud run services describe puppeteer-screenshot-service \
        --region ${_REGION} --format='value(status.url)')"

substitutions:
  _REGION: us-central1
  _ARTIFACT_REGISTRY_REPO_NAME: container-images

timeout: 1800s
logsBucket: gs://${PROJECT_ID}-logs-data/build-logs
options:
  substitutionOption: ALLOW_LOOSE
  machineType: 'E2_HIGHCPU_8'
```

## README.md for Puppeteer Service

Now, let's create the README.md for the puppeteer-service:

```markdown:functions/getMacro/puppeteer-service/README.md
# Puppeteer Screenshot Service

A microservice that provides webpage screenshot capabilities using Puppeteer, packaged as a containerized API.

## Overview

This service is part of the getMacro system and provides browser automation capabilities through an API. It's designed to be deployed as a standalone Cloud Run service that the main Python Cloud Function can call.

## Features

- Take full-page screenshots of any URL
- RESTful API for easy integration
- Optimized for Cloud Run deployment
- Configurable viewport and screenshot options

## API Endpoints

### GET /status

Check if the service is running.

**Response:**
```json
{
  "status": "ok",
  "service": "puppeteer-screenshot",
  "timestamp": "2024-07-20T12:00:00.000Z"
}
```

### POST /snapshot

Take a screenshot of a URL.

**Request Body:**
```json
{
  "url": "https://example.com",
  "symbol": "optional-identifier"
}
```

**Response:**
```json
{
  "url": "https://example.com",
  "symbol": "optional-identifier",
  "timestamp": "2024-07-20T12:00:00.000Z",
  "image_base64": "base64-encoded-image-data"
}
```

## Local Development

### Prerequisites

- Node.js (v16 or later)
- npm

### Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Run the service:
   ```bash
   npm start
   ```

3. Test the service:
   ```bash
   curl -X GET http://localhost:8080/status
   ```

## Docker Deployment

### Building the Docker Image

```bash:functions/getMacro/puppeteer-service/README.md
docker build -t puppeteer-screenshot-service .
```

### Running the Container Locally

```bash
docker run -p 8080:8080 puppeteer-screenshot-service
```

## Google Cloud Deployment

### Deploy to Cloud Run Using Cloud Build

1. Make sure you have the gcloud CLI installed and configured.

2. Create an Artifact Registry repository if you don't already have one:
   ```bash
   gcloud artifacts repositories create container-images \
     --repository-format=docker \
     --location=us-central1 \
     --description="Docker container images"
   ```

3. Run the Cloud Build deployment:
   ```bash
   gcloud builds submit --config cloudbuild.yaml
   ```

### Manual Deployment to Cloud Run

1. Build and push the Docker image:
   ```bash
   docker build -t us-central1-docker.pkg.dev/YOUR_PROJECT_ID/container-images/puppeteer-screenshot-service .
   docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/container-images/puppeteer-screenshot-service
   ```

2. Deploy to Cloud Run:
   ```bash
   gcloud run deploy puppeteer-screenshot-service \
     --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/container-images/puppeteer-screenshot-service \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --memory 2Gi \
     --cpu 2 \
     --timeout 300s
   ```

## Configuration Options

### Environment Variables

- `PORT`: The port the service listens on (default: 8080)
- `TIMEOUT`: Maximum time in milliseconds to wait for page load (default: 60000)
- `MAX_CONCURRENT_SESSIONS`: Maximum number of concurrent Puppeteer sessions (default: 10)
- `CHROMIUM_PATH`: Custom path to Chromium executable (optional)

## Integration with Python Cloud Function

To use this service from the Python Cloud Function:

1. Deploy this service to Cloud Run
2. Set the `PUPPETEER_SERVICE_URL` environment variable in your Python Cloud Function to the Cloud Run service URL
3. The `rate_forecast_puppeteer.py` module will automatically use this service

Example environment variable setup:
```
PUPPETEER_SERVICE_URL=https://puppeteer-screenshot-service-abcdefg-uc.a.run.app
```

## Troubleshooting

### Common Issues

- **Memory Issues**: If you see "out of memory" errors, increase the memory allocation in Cloud Run
- **Timeout Errors**: For complex pages, increase the timeout setting
- **Connection Issues**: Ensure your Cloud Run service has proper permissions to access the internet

### Monitoring

Monitor your service using Google Cloud Console:
- Cloud Run dashboard for service metrics
- Cloud Logging for service logs
- Cloud Monitoring for setting up alerts
