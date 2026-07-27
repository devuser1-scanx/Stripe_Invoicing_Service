# ScanX Billing Service — Milestone 3 Deployment Commands

These files separate local development, one-time Google Cloud setup, Cloud Run deployment, post-deployment configuration, and testing.

## Correct order

1. Finish and test the FastAPI application locally.
2. Authenticate the **gcloud CLI** from CMD.
3. Enable Google Cloud APIs.
4. Create service accounts and IAM permissions.
5. Create Secret Manager secrets.
6. Create the Cloud Tasks queue.
7. Deploy the source code to Cloud Run from CMD.
8. retrieve the Cloud Run URL.
9. update `BILLING_SERVICE_URL`.
10. redeploy the service with the final URL.
11. grant Cloud Run invoker permissions.
12. test `/billing/schedule`.
13. confirm Cloud Tasks calls `/billing/process`.

## Important clarification

`gcloud auth login` and `gcloud auth application-default login` do different things:

- `gcloud auth login` authenticates your CMD session for commands such as `gcloud run deploy`.
- `gcloud auth application-default login` provides local credentials to Python Google Cloud client libraries.

You do **not** need to authenticate the FastAPI application as a deployed Cloud Run service while it is still being developed locally.

Actual Cloud Tasks delivery should be tested after Cloud Run deployment because Cloud Tasks cannot reach `127.0.0.1` on your computer.

## Files

- `01_local_development.md`
- `02_one_time_gcp_setup.md`
- `03_deploy_from_cmd.md`
- `04_post_deployment_setup.md`
- `05_test_deployed_service.md`
