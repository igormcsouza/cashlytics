"""Minimal API Gateway emulator for local development.

Translates incoming HTTP requests into API Gateway HTTP API (v2) events,
forwards them to the backend Lambda container's Runtime Interface Emulator
(RIE) invocations endpoint, and returns the Lambda's HTTP response. This is the
same translation API Gateway / a function URL performs in AWS, giving the
frontend and the smoke test a real REST endpoint backed by the production
Lambda handler.

It also emulates the Cognito JWT authorizer that protects the HTTP API in
AWS: requests without a Bearer token (except CORS preflights and "/", the
public health route) are rejected with 401, and the token's claims are
forwarded to the Lambda in ``requestContext.authorizer.jwt.claims`` — the
exact shape the backend trusts in production. The token comes from
cognito-local; only its expiry is checked here (signature verification is API
Gateway's job in AWS, and this proxy is a dev-only tool that keeps to the
standard library).

Standard library only — no third-party dependencies.

Environment:
    LAMBDA_RIE_URL  Full invocations URL of the backend RIE
                    (default: http://backend:8080/2015-03-31/functions/function/invocations)
    PORT            Port to listen on (default: 8080)
"""

import base64
import json
import os
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

LAMBDA_RIE_URL = os.environ.get(
    "LAMBDA_RIE_URL",
    "http://backend:8080/2015-03-31/functions/function/invocations",
)
PORT = int(os.environ.get("PORT", "8080"))


def _decode_claims(headers) -> dict | None:
    """Claims from the Bearer token, or None when missing/expired/malformed."""
    auth = headers.get("Authorization") or headers.get("authorization") or ""
    if not auth.startswith("Bearer "):
        return None
    token = auth[len("Bearer ") :].strip()
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception:
        return None
    if claims.get("exp") and claims["exp"] < time.time():
        return None
    # The real authorizer flattens list claims into "[a b]" strings; mirror
    # that exactly. Decoded by backend/src/auth/services.py's
    # groups_from_claims, which is the actual source of truth for this
    # format (it must match what AWS really sends) — keep this in sync with
    # it if either side changes.
    return {
        key: f"[{' '.join(map(str, value))}]" if isinstance(value, list) else value
        for key, value in claims.items()
    }


def _build_event(
    method: str,
    raw_path: str,
    query: str,
    headers,
    body: bytes,
    claims: dict | None,
) -> dict:
    request_context = {
        "http": {
            "method": method,
            "path": raw_path,
            "protocol": "HTTP/1.1",
            "sourceIp": "127.0.0.1",
        }
    }
    if claims is not None:
        request_context["authorizer"] = {"jwt": {"claims": claims}}
    return {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": raw_path,
        "rawQueryString": query,
        "headers": {k.lower(): v for k, v in headers.items()},
        "requestContext": request_context,
        "body": body.decode("utf-8") if body else None,
        "isBase64Encoded": False,
    }


def _invoke(event: dict) -> dict:
    data = json.dumps(event).encode("utf-8")
    req = urllib.request.Request(
        LAMBDA_RIE_URL, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _reject_unauthorized(self) -> None:
        payload = json.dumps({"message": "Unauthorized"}).encode("utf-8")
        self.send_response(401)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        # The frontend and this proxy run on different ports (different
        # origins) locally. Without these, a cross-origin fetch() call can't
        # even read this response's status — the browser blocks it as a CORS
        # violation and the promise rejects with a network error instead of
        # resolving with status 401, so the caller never gets to react to it.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(payload)

    def _proxy(self) -> None:
        split = urlsplit(self.path)
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length) if length else b""

        # Mirrors the deployed API: "/" (the health route) is public, CORS
        # preflights skip auth, everything else needs a valid token whose
        # claims are handed to the Lambda.
        claims = _decode_claims(self.headers)
        if claims is None and self.command != "OPTIONS" and split.path != "/":
            self._reject_unauthorized()
            return

        event = _build_event(
            self.command, split.path, split.query, self.headers, body, claims
        )
        try:
            result = _invoke(event)
        except Exception as exc:  # pragma: no cover - surfaced to client
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            payload = json.dumps({"error": f"proxy: {exc}"}).encode("utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        status = result.get("statusCode", 200)
        headers = result.get("headers", {}) or {}
        raw_body = result.get("body", "") or ""
        if result.get("isBase64Encoded"):
            out = base64.b64decode(raw_body)
        else:
            out = raw_body.encode("utf-8")

        self.send_response(status)
        sent_length = False
        for key, value in headers.items():
            if key.lower() == "content-length":
                sent_length = True
            self.send_header(key, value)
        if not sent_length:
            self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        if out:
            self.wfile.write(out)

    do_GET = _proxy
    do_POST = _proxy
    do_PUT = _proxy
    do_DELETE = _proxy
    do_PATCH = _proxy
    do_OPTIONS = _proxy

    def log_message(self, *args):  # quieter logs
        pass


if __name__ == "__main__":
    print(f"API Gateway proxy listening on :{PORT} -> {LAMBDA_RIE_URL}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
