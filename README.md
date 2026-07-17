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
small **API Gateway proxy** (HTTP → Lambda events, including the Cognito JWT
authorizer step) persisting to **DynamoDB Local**, authenticated against
**[cognito-local](https://github.com/jagregory/cognito-local)** — the same
role the real Cognito user pool plays in AWS. No MongoDB, no auth bypass.

**Prerequisites**: [Docker](https://docs.docker.com/get-docker/) (+ Compose v2).
`python3` is used to run the smoke test.

```bash
# Bring up DynamoDB Local + cognito-local + backend Lambda + API proxy;
# create the table and the Cognito user pool/admin users
make up

# Exercise login -> create -> list -> edit -> delete end to end
make smoke

# Run the Next.js frontend too (http://localhost:3000) — reads the Cognito
# client id `make up` wrote to local/.cognito.env
make ui

# Reset local data / tear everything down
make down
```

Endpoints once up:

- Backend REST API (via the proxy): <http://localhost:5000> (e.g. `/expenses`)
- Backend RIE invocations endpoint: <http://localhost:9000>
- DynamoDB Local: <http://localhost:8000>
- cognito-local: <http://localhost:9229>
- Frontend (with `make ui`): <http://localhost:3000> — log in with
  `admin@cashlytics.dev` / `password`

For CI, `make e2e` brings the stack up, runs the smoke test, and tears it down;
`make e2e-full` additionally starts the frontend and runs the Playwright
browser suite (`frontend/e2e/`). The pipelines gate on these: pull requests run
CI → smoke → deploy dev, and pushes to main run CI → smoke + full E2E → deploy
prod.
Configuration lives in `.env.example`; the same env vars are used in AWS by
changing only their values (e.g. unset `DYNAMODB_ENDPOINT_URL`,
point Cognito at the real user pool instead of cognito-local).

## Backend development (uv)

The backend is a FastAPI app managed with [uv](https://docs.astral.sh/uv/).
Dependencies are defined in `backend/pyproject.toml` and pinned in
`backend/uv.lock` (uv is the source of truth; there is no `requirements.txt`).

The code follows a domain-package layout (see
[zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices)):

```text
backend/src/
├── main.py        # FastAPI app: CORS, health route, router includes
├── core/          # config (env vars, table names), DynamoDB connection, local bootstrap
├── shared/        # Repository protocol + generic DynamoDBRepository
└── expense/       # expense domain: models, exceptions, repositories, services, controllers
```

Each domain lives in its own package with `models.py`, `exceptions.py`,
`repositories.py`, `services.py`, and `controllers.py`; a future domain (e.g.
`auth/`) is a sibling package with the same files. Tests under `backend/tests/`
mirror this layout, and coverage is enforced at 100% (`--cov-fail-under=100`).

```bash
cd backend

# Install dependencies (incl. dev/test group)
uv sync

# Point at DynamoDB Local for development, then create the table
# (also seeds sample data from src/core/seed_data.json — dev/local envs only)
export ENVIRONMENT=dev # table name -> "dev-expenses"
export AWS_REGION=sa-east-1
export DYNAMODB_ENDPOINT_URL=http://localhost:8000
uv run python -m src.core.bootstrap

# Run the API locally
uv run uvicorn src.main:app --reload --port 5000

# Run the test suite (DynamoDB is mocked with moto — no database needed)
uv run pytest
```

Interactive OpenAPI docs are served at <http://localhost:5000/docs>.

Configuration comes from environment variables:

- `ENVIRONMENT` — deployment environment prefixed to table names (default
  `dev`), e.g. `prod` gives the table `prod-expenses`
- `AWS_REGION` — AWS region (default `sa-east-1`)
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
  -e AWS_REGION=sa-east-1 \
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
- `CashlyticsBackend-{env}` — backend Lambda (container image) behind an
  API Gateway HTTP API protected by a Cognito JWT authorizer, plus the
  Cognito user pool itself; granted least-privilege read/write on the table
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

## Authentication (Amazon Cognito)

All access — UI and API — requires login. The pieces:

- **Cognito user pool** (per environment, defined in `CashlyticsBackend-{env}`):
  email + password sign-in only, self-sign-up disabled. Two administrator
  users are created at deploy time and added to the `admin` group.
- **API Gateway JWT authorizer**: every backend route rejects requests without
  a valid Cognito token before they reach the Lambda. The FastAPI app then
  trusts the claims API Gateway forwards (`backend/src/auth/services.py`) and
  enforces the `admin` role — it never validates tokens itself.
- **Frontend**: `middleware.ts` redirects to `/login` whenever the auth cookies
  are missing; `lib/auth.ts` talks to Cognito directly (login, first-login
  password change, silent token refresh) and `lib/api.ts` sends the id token as
  a `Bearer` header. A logout icon button sits next to “+ Add Expense”.

Admin users:

- **Prod** — `igormcsouza@gmail.com` and `eilawoman@hotmail.com` by default
  (override with the `ADMIN_EMAILS` repository variable, comma-separated, or
  `-c admin_emails=...` when deploying manually). On the first deploy Cognito
  emails each user a **temporary password**; the login page then asks them to
  choose their own (`NEW_PASSWORD_REQUIRED` flow). Prod password policy:
  12+ chars with upper/lower/digit/symbol.
- **PR / dev environments** — `admin@cashlytics.dev` / `password` (plus
  `admin2@cashlytics.dev`). The deploy workflow sets this as a permanent
  password right after the backend deploy so reviewers can log in without any
  email round-trip; the PR comment repeats the credentials.

Useful operations (user pool id is in the `CashlyticsBackend-{env}` stack
outputs):

```bash
# Re-send an expired invitation (temporary passwords last 7 days)
aws cognito-idp admin-create-user --user-pool-id <POOL_ID> \
  --username user@example.com --message-action RESEND

# Reset a password manually
aws cognito-idp admin-set-user-password --user-pool-id <POOL_ID> \
  --username user@example.com --password '<NewPassword123!>' --permanent
```

Locally, docker-compose runs **cognito-local** instead of real Cognito (see
"Running Locally" above); the backend and API gateway proxy trust its tokens
exactly as they trust real Cognito tokens in AWS — no bypass. The backend
*test suite* (`uv run pytest`) doesn't start any stack, so it simulates the
authorizer directly: `tests/conftest.py`'s `WithGatewayClaims` wraps the app
with fake forwarded claims, the same shape API Gateway attaches in production.

## CI / CD

Two GitHub Actions workflows handle deployments automatically:

- **`deploy-dev.yml`** — triggers on every PR opened/updated against `main`:
  runs CI (backend + frontend tests), then the E2E smoke test (docker stack +
  `make smoke`), then deploys the `dev` stacks and posts the CloudFront and
  API URLs as a PR comment.
- **`deploy-prod.yml`** — triggers on merge to `main`: runs CI, then the E2E
  smoke test plus the full Playwright browser suite, then deploys the `prod`
  stacks and sets the GitHub *production* environment URL.

Both reuse `e2e.yml` (`workflow_call`), which brings up the docker-compose
stack on the runner; the `full` input adds the frontend container and the
Playwright run.

Required GitHub Actions secrets: `AWS_ACCOUNT_ID`, `AWS_REGION`,
`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`.
