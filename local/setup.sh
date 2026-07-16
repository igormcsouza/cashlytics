#!/usr/bin/env bash
# Wait for the local stack to be reachable, then create the DynamoDB table and
# the Cognito user pool/client/admin users.
set -euo pipefail

echo "Waiting for DynamoDB Local on :8000 ..."
for _ in $(seq 1 60); do
  if curl -s -o /dev/null http://localhost:8000; then break; fi
  sleep 1
done

echo "Creating the expenses table (idempotent) ..."
docker compose exec -T backend python -m database.bootstrap

echo "Waiting for cognito-local on :9229 ..."
for _ in $(seq 1 60); do
  if curl -s -o /dev/null http://localhost:9229; then break; fi
  sleep 1
done

echo "Creating the Cognito user pool, admin group, and dev admins (idempotent) ..."
docker compose exec -T backend python -m auth_bootstrap

echo "Waiting for the backend via the API gateway proxy on :5000 ..."
for _ in $(seq 1 60); do
  # Any response (even 401, before login) means the whole chain is up.
  if curl -s -o /dev/null http://localhost:5000/; then break; fi
  sleep 1
done

echo "Local stack ready. Log in with admin@cashlytics.dev / password."
