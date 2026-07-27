# 3. Deploy the FastAPI Application to Cloud Run from CMD

Run these commands inside the project root—the directory containing:

```text
app\
Dockerfile
requirements.txt
alembic.ini
migrations\
```

## Step 1 — Set values

```cmd
set PROJECT_ID=vernal-maker-473121-k4
set REGION=us-central1
set SERVICE_NAME=scanx-billing
set RUNTIME_SA=scanx-billing-runtime@%PROJECT_ID%.iam.gserviceaccount.com
set TASKS_SA=scanx-cloud-tasks-invoker@%PROJECT_ID%.iam.gserviceaccount.com
set INSTANCE_CONNECTION_NAME=%PROJECT_ID%:%REGION%:scanx-postgres-db
```

## Step 2 — Confirm active account and project

```cmd
gcloud auth list
```

```cmd
gcloud config get-value project
```

The selected project must be:

```text
vernal-maker-473121-k4
```

## Step 3 — First deployment from source

The first deployment uses a temporary placeholder URL because the final Cloud Run URL does not exist yet.

```cmd
gcloud run deploy %SERVICE_NAME% --source=. --region=%REGION% --project=%PROJECT_ID% --service-account=%RUNTIME_SA% --no-allow-unauthenticated --min-instances=0 --max-instances=10 --concurrency=10 --cpu=1 --memory=1Gi --timeout=120 --set-env-vars="APP_NAME=ScanX Billing Service,APP_VERSION=0.3.0,ENVIRONMENT=production,LOG_LEVEL=INFO,INSTANCE_CONNECTION_NAME=%INSTANCE_CONNECTION_NAME%,DB_USER=postgres,DB_NAME=scanx_app,DB_IP_TYPE=PUBLIC,DB_POOL_SIZE=5,DB_MAX_OVERFLOW=2,DB_POOL_RECYCLE_SECONDS=1800,USE_TCP_DATABASE=false,STRIPE_DEFAULT_CURRENCY=usd,STRIPE_INVOICE_COLLECTION_METHOD=send_invoice,GCP_PROJECT_ID=%PROJECT_ID%,GCP_REGION=%REGION%,CLOUD_TASKS_QUEUE=scanx-invoice-primary,BILLING_SERVICE_URL=https://placeholder.invalid,CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT=%TASKS_SA%,INVOICE_DELAY_SECONDS=600" --set-secrets="DB_PASSWORD=scanx-db-password:latest,STRIPE_SECRET_KEY=scanx-stripe-secret-key:latest"
```

Cloud Run will use Cloud Build to build the Dockerfile and deploy the resulting container.

## Step 4 — Retrieve the service URL

```cmd
for /f "delims=" %i in ('gcloud run services describe %SERVICE_NAME% --region=%REGION% --project=%PROJECT_ID% --format^="value(status.url)"') do set SERVICE_URL=%i
```

Display it:

```cmd
echo %SERVICE_URL%
```

Expected format:

```text
https://scanx-billing-xxxxxxxxxx-uc.a.run.app
```

## Step 5 — Update the service with the real URL

```cmd
gcloud run services update %SERVICE_NAME% --region=%REGION% --project=%PROJECT_ID% --update-env-vars="BILLING_SERVICE_URL=%SERVICE_URL%"
```

## Step 6 — Confirm deployment

```cmd
gcloud run services describe %SERVICE_NAME% --region=%REGION% --project=%PROJECT_ID%
```

## Step 7 — View revisions

```cmd
gcloud run revisions list --service=%SERVICE_NAME% --region=%REGION% --project=%PROJECT_ID%
```

## Step 8 — View logs

```cmd
gcloud run services logs read %SERVICE_NAME% --region=%REGION% --project=%PROJECT_ID% --limit=100
```

## Redeploy after code changes

From the same project directory:

```cmd
gcloud run deploy %SERVICE_NAME% --source=. --region=%REGION% --project=%PROJECT_ID% --service-account=%RUNTIME_SA% --no-allow-unauthenticated
```

Cloud Run retains settings not explicitly changed, but review the deployed configuration after each major change.
