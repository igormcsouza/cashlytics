#!/usr/bin/env bash
# Wait for the local stack to be reachable, then create the DynamoDB table.
set -euo pipefail

echo "Waiting for DynamoDB Local on :8000 ..."
for _ in $(seq 1 60); do
  if curl -s -o /dev/null http://localhost:8000; then break; fi
  sleep 1
done

echo "Creating the expenses table (idempotent) ..."
docker compose exec -T backend python -m src.core.bootstrap

echo "Waiting for the backend via the API gateway proxy on :5000 ..."
for _ in $(seq 1 60); do
  if curl -fsS -o /dev/null http://localhost:5000/expenses; then break; fi
  sleep 1
done

echo "Local stack ready."
