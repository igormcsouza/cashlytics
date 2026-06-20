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
export EXPENSES_TABLE=expenses
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

- `EXPENSES_TABLE` — DynamoDB table name (default `expenses`)
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
  -e EXPENSES_TABLE=expenses \
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

## Infrastructure (AWS CDK)

Infrastructure is defined as code with the AWS CDK (TypeScript) in `infra/`:

- `CashlyticsDatabase` — the DynamoDB expenses table (`id` partition key)
- `CashlyticsBackend` — the backend Lambda (container image, `lambda_function.handler`)
  behind a function URL, granted least-privilege read/write on the table
- `CashlyticsFrontend` — the Next.js SSR Lambda + an S3 bucket for static assets

Resource names and env var keys live in `infra/lib/config.ts` and match the
application code.

```bash
cd infra
npm install

npm test          # CDK assertion tests (Vitest + aws-cdk-lib/assertions)
npx cdk synth     # synthesize CloudFormation for all stacks
npx cdk deploy --all   # deploy (requires AWS credentials + `cdk bootstrap`)
```
