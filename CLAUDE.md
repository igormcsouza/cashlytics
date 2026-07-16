# Cashlytics — Project Standards

Expense tracker: FastAPI backend on AWS Lambda (container image) + DynamoDB, Next.js frontend on CloudFront, AWS CDK (Python) infra, all env-var driven.

## Backend architecture (follow strictly)

The backend uses a **domain-package layout** per [zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices):

```
backend/src/
├── main.py        # FastAPI app: CORS, health route, router includes only
├── core/          # global: config.py (env vars, table_name), database.py (DynamoDB connection), bootstrap.py (local table creation)
├── shared/        # global: Repository Protocol + generic DynamoDBRepository
└── expense/       # domain package
    ├── models.py        # Pydantic models (request bodies + stored shapes), no logic
    ├── exceptions.py    # ALL domain exceptions live here (e.g. ExpenseNotFoundError)
    ├── repositories.py  # factory binding the generic repository to the domain's table
    ├── services.py      # business logic; raises domain exceptions
    └── controllers.py   # APIRouter + DI; thin: parse, call service, map exceptions to HTTP
```

Rules:

- **New domain = new sibling package** (e.g. `auth/`) with the same five files. Never create global `models/`, `services/`, `controllers/` layer folders.
- **Protocol over inheritance**: services depend on the `Repository` `Protocol` from `src/shared/repository.py` (structural typing), never on `DynamoDBRepository` directly. Domain `repositories.py` exposes a factory returning `Repository`.
- **Thin controllers**: no business rules in routes. Services own the rules and raise domain exceptions; controllers translate them to `HTTPException`.
- `lambda_function.py` stays at `backend/` root — the Docker CMD is `lambda_function.handler`. Don't move it.
- Configuration is entirely env-var driven (`ENVIRONMENT`, `AWS_REGION`, `DYNAMODB_ENDPOINT_URL`); table names come from `table_name()` in `src/core/config.py`.

## Testing (100% coverage, enforced)

- `backend/tests/` **mirrors the `src/` layout** (`tests/expense/test_services.py` ↔ `src/expense/services.py`).
- Coverage is enforced at **100%** via pytest-cov (`--cov-fail-under=100` in `pyproject.toml` addopts) — any new code needs tests in the same PR or CI fails.
- Service tests use an in-memory fake implementing the `Repository` protocol — no moto/boto3. Repository/API/handler tests use moto (`dynamodb_table` fixture in `conftest.py`).
- Only truly unreachable lines get excluded: `if __name__ == "__main__":` blocks (via `exclude_also`) and Protocol stubs (`# pragma: no cover`).

Run: `cd backend && uv run pytest` (unit + coverage) · `make e2e` (full docker stack + smoke test).

## Branches

Format: `<type>/<issue-number>-<short-kebab-description>`, issue number omitted when there is none.

- Types: `feat/` (new features), `bug-fix/` (bug fixes), `ci/` (CI/CD, infra pipelines).
- Examples: `feat/13-domain-packages`, `bug-fix/27-paid-toggle`, `ci/cache-uv-deps`, `feat/expense-filters` (no issue).

## Pull requests

- **Title: meaningful, describes the change, NO issue number in it.** Bad: `Fix #13`, `refactor: restructure backend (#13)`. Good: `Restructure backend into domain packages`.
- Reference the issue in the **body** instead (`Closes #13`).
- Body explains what changed, key design decisions, and how it was verified (tests, `make e2e`).

## Commits

Conventional Commits style (`feat:`, `fix:`, `refactor:`, `ci:`, `docs:`). Subject ≤ 72 chars; body explains why when not obvious.

## Tooling

- Backend deps: **uv only** (`backend/pyproject.toml` + `uv.lock`; no requirements.txt).
- Local stack: `make up` / `make ui` / `make smoke` / `make down`; table bootstrap is `python -m src.core.bootstrap`.
- Frontend: npm (`frontend/`); infra: CDK Python (`infra/`).
