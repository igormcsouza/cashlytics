# Local environment that mirrors production (Lambda + DynamoDB Local).
.PHONY: up ui seed smoke logs down e2e

CORE := dynamodb-local cognito-local backend apigw

## Build & start the core stack (DynamoDB Local, cognito-local, backend Lambda,
## API proxy), then create the table and the Cognito user pool/admins.
up:
	docker compose up -d --build $(CORE)
	./local/setup.sh

## Start the Next.js frontend too (http://localhost:3000). Reads the Cognito
## client id `make up` wrote to local/.cognito.env.
ui:
	set -a; . local/.cognito.env; set +a; \
	docker compose --profile ui up -d --build frontend

## Create/seed the DynamoDB table and the Cognito user pool (idempotent).
seed:
	docker compose exec -T backend python -m src.core.bootstrap
	docker compose exec -T backend python -m src.auth.bootstrap

## Run the end-to-end smoke test against the running stack.
smoke:
	python3 local/smoke_test.py

## Tail logs.
logs:
	docker compose logs -f

## Stop and remove everything (including volumes).
down:
	docker compose --profile ui down -v --remove-orphans

## One-shot for CI: bring the stack up, smoke test, tear down.
e2e:
	$(MAKE) up
	$(MAKE) smoke
	$(MAKE) down
