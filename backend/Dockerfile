# Lambda-ready image for the Cashlytics backend.
# Runs identically locally (via the Lambda Runtime Interface Emulator / SAM) and
# in AWS Lambda; behavior is driven entirely by environment variables.
FROM public.ecr.aws/lambda/python:3.12

# Bring in uv to resolve/install the uv-managed dependencies.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR ${LAMBDA_TASK_ROOT}

# Install runtime-only dependencies (no dev/test, no caches) into the task root.
COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --no-emit-project -o requirements.txt \
    && uv pip install --no-cache -r requirements.txt --target "${LAMBDA_TASK_ROOT}" \
    && rm requirements.txt

# Copy the application code (same app object used locally and in tests).
COPY . ${LAMBDA_TASK_ROOT}

CMD ["lambda_function.handler"]
