"""Minimal API Gateway emulator for local development.

Translates incoming HTTP requests into API Gateway HTTP API (v2) events,
forwards them to the backend Lambda container's Runtime Interface Emulator
(RIE) invocations endpoint, and returns the Lambda's HTTP response. This is the
same translation API Gateway / a function URL performs in AWS, giving the
frontend and the smoke test a real REST endpoint backed by the production
Lambda handler.

Standard library only — no third-party dependencies.

Environment:
    LAMBDA_RIE_URL  Full invocations URL of the backend RIE
                    (default: http://backend:8080/2015-03-31/functions/function/invocations)
    PORT            Port to listen on (default: 8080)
"""

import base64
import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

LAMBDA_RIE_URL = os.environ.get(
    "LAMBDA_RIE_URL",
    "http://backend:8080/2015-03-31/functions/function/invocations",
)
PORT = int(os.environ.get("PORT", "8080"))


def _build_event(method: str, raw_path: str, query: str, headers, body: bytes) -> dict:
    return {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": raw_path,
        "rawQueryString": query,
        "headers": {k.lower(): v for k, v in headers.items()},
        "requestContext": {
            "http": {
                "method": method,
                "path": raw_path,
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
            }
        },
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

    def _proxy(self) -> None:
        split = urlsplit(self.path)
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length) if length else b""

        event = _build_event(
            self.command, split.path, split.query, self.headers, body
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
