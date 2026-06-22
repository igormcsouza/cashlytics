# Cashlytics

Cashlytics helps you track, analyze, and optimize your finances in one place—giving you clear insights into your spending, income, and net worth.

## Features

- Create, view, edit, and delete expenses
- See the total sum of all expenses
- Mark expenses as recurrent or one-time
- Confirmation popup before deletion

## Tech Stack

- **Backend**: Python + FastAPI (managed with [uv](https://docs.astral.sh/uv/))
- **Frontend**: Next.js (App Router) + Tailwind CSS
- **Database**: DynamoDB (DynamoDB Local for development)
- **Containerization**: Docker + docker-compose

## Running Locally

The local environment mirrors production: the backend runs as the **Lambda
container image** via the AWS Lambda Runtime Interface Emulator, fronted by a
small **API Gateway proxy** (HTTP → Lambda events), persisting to **DynamoDB
Local**. No MongoDB.

**Prerequisites**: [Docker](https://docs.docker.com/get-docker/) (+ Compose v2).
`python3` is used to run the smoke test.

```bash
# Bring up DynamoDB Local + backend Lambda + API proxy, and create the table
make up

# Exercise create → list → edit → delete end to end
make smoke

# Optional: run the Next.js frontend too (http://localhost:3000)
make ui

# Reset local data / tear everything down
make down
```

Endpoints once up:

- Backend REST API (via the proxy): <http://localhost:5000> (e.g. `/expenses`)
- Backend RIE invocations endpoint: <http://localhost:9000>
- DynamoDB Local: <http://localhost:8000>
- Frontend (with `make ui`): <http://localhost:3000>

For CI, `make e2e` brings the stack up, runs the smoke test, and tears it down.
Configuration lives in `.env.example`; the same env vars are used in AWS by
changing only their values (e.g. unset `DYNAMODB_ENDPOINT_URL`).

## Backend development (uv)

The backend is a FastAPI app managed with [uv](https://docs.astral.sh/uv/).
Dependencies are defined in `backend/pyproject.toml` and pinned in
`backend/uv.lock` (uv is the source of truth; there is no `requirements.txt`).

```bash
cd backend

# Install dependencies (incl. dev/test group)
uv sync

# Point at DynamoDB Local for development, then create the table
export ENVIRONMENT=dev # table name -> "dev-expenses"
export AWS_REGION=us-east-1
export DYNAMODB_ENDPOINT_URL=http://localhost:8000
uv run python -m database.bootstrap

# Run the API locally
uv run uvicorn app:app --reload --port 5000

# Run the test suite (DynamoDB is mocked with moto — no database needed)
uv run pytest
```

Interactive OpenAPI docs are served at <http://localhost:5000/docs>.

Configuration comes from environment variables:

- `ENVIRONMENT` — deployment environment prefixed to table names (default
  `dev`), e.g. `prod` gives the table `prod-expenses`
- `AWS_REGION` — AWS region (default `us-east-1`)
- `DYNAMODB_ENDPOINT_URL` — endpoint override for DynamoDB Local in dev; leave
  **unset** in AWS so the SDK uses the real DynamoDB endpoint

## Backend as a Lambda container

The backend deploys to AWS Lambda as a container image. The same FastAPI `app`
is wrapped with [Mangum](https://mangum.io/) in `backend/lambda_function.py`
(entrypoint `lambda_function.handler`).

```bash
cd backend

# Build the Lambda image (AWS Python base image, runtime deps only via uv)
docker build -t cashlytics-backend:lambda .

# Invoke locally with the Lambda Runtime Interface Emulator
docker run --rm -p 9000:8080 \
  -e ENVIRONMENT=dev \
  -e AWS_REGION=us-east-1 \
  -e DYNAMODB_ENDPOINT_URL=http://host.docker.internal:8000 \
  cashlytics-backend:lambda

# In another shell, send an API Gateway HTTP API event
curl -s "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{"version":"2.0","rawPath":"/expenses","requestContext":{"http":{"method":"GET","path":"/expenses"}},"isBase64Encoded":false}'
```

The same image runs in AWS purely by changing configuration: leave
`DYNAMODB_ENDPOINT_URL` unset so the SDK targets real DynamoDB.

## Frontend (Next.js + Tailwind)

The product UI is a Next.js (App Router) + Tailwind CSS app in `frontend/`. It
calls the backend through `NEXT_PUBLIC_API_BASE_URL`. (The old Vue page served
by the backend is superseded; the backend now exposes a JSON health route at
`/`.)

```bash
cd frontend
npm install

# Point at the backend API
cp .env.example .env.local   # edit NEXT_PUBLIC_API_BASE_URL if needed

npm run dev     # http://localhost:3000
npm run build   # production build
npm test        # component tests (Vitest + React Testing Library)
```

Environment variable:

- `NEXT_PUBLIC_API_BASE_URL` — base URL of the backend API (dev: the local
  backend; prod: the Lambda / API Gateway URL).

## Infrastructure (AWS CDK — Python)

Infrastructure is defined as code with the AWS CDK (Python) in `infra/`.
Stacks are suffixed with the deployment environment (`dev` or `prod`):

- `CashlyticsDatabase-{env}` — DynamoDB expenses table (`id` partition key)
- `CashlyticsBackend-{env}` — backend Lambda (container image) behind a
  function URL; granted least-privilege read/write on the table
- `CashlyticsFrontend-{env}` — Next.js SSR Lambda (via OpenNext) + S3 bucket
  for static assets, served through a CloudFront distribution:

```
Browser → CloudFront
              ├── /_next/static/*  → S3 (JS/CSS, long-lived cache)
              └── everything else  → Lambda Function URL (SSR)
```

Resource names and env var keys live in `infra/stacks/config.py`.

```bash
cd infra
pip install -r requirements.txt

cdk synth                        # synthesize CloudFormation for all stacks
cdk deploy --all -c environment=dev   # deploy dev (requires cdk bootstrap)
cdk deploy --all -c environment=prod  # deploy prod
```

## CI / CD

Two GitHub Actions workflows handle deployments automatically:

- **`deploy-dev.yml`** — triggers on every PR opened/updated against `main`:
  runs CI (backend + frontend tests), then deploys the `dev` stacks and posts
  the CloudFront and API URLs as a PR comment.
- **`deploy-prod.yml`** — triggers on merge to `main`: runs CI, then deploys
  the `prod` stacks and sets the GitHub *production* environment URL.

Required GitHub Actions secrets: `AWS_ACCOUNT_ID`, `AWS_REGION`,
`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`.
