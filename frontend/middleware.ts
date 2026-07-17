import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Auth is off when the app is built without Cognito (local docker-compose).
const AUTH_ENABLED = Boolean(process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID);

// Keep in sync with lib/auth.ts (middleware runs on the edge runtime, so the
// names are duplicated here instead of importing browser-oriented code).
const ID_TOKEN_COOKIE = "cashlytics_id_token";
const REFRESH_TOKEN_COOKIE = "cashlytics_refresh_token";

// Next's non-edge middleware adapter (`next start`, what this Lambda-container
// image runs) always re-parses the Location header as an absolute URL with no
// base and throws "Invalid URL" on a bare relative path, so this must be
// absolute. Behind CloudFront the Lambda origin never sees the real Host (the
// distribution's origin request policy strips it — Function URLs reject a
// mismatched one), so `request.url` resolves to the origin's own raw Function
// URL instead of the public domain. A CloudFront Function
// (infra/stacks/frontend_stack.py) forwards the real Host as `x-forwarded-host`
// instead; fall back to the request's own host for local/docker where no such
// function runs (AUTH_ENABLED is off there anyway, so this fallback is unused
// in practice today).
function redirect(request: NextRequest, path: string): NextResponse {
  const host = request.headers.get("x-forwarded-host") ?? request.nextUrl.host;
  const url = new URL(path, `${request.nextUrl.protocol}//${host}`);
  return NextResponse.redirect(url, 307);
}

export function middleware(request: NextRequest) {
  if (!AUTH_ENABLED) return NextResponse.next();

  // A refresh token alone counts as logged in: the client silently renews the
  // id token on the next API call.
  const loggedIn =
    request.cookies.has(ID_TOKEN_COOKIE) ||
    request.cookies.has(REFRESH_TOKEN_COOKIE);
  const isLoginPage = request.nextUrl.pathname === "/login";

  if (!loggedIn && !isLoginPage) {
    return redirect(request, "/login");
  }
  if (loggedIn && isLoginPage) {
    return redirect(request, "/");
  }
  return NextResponse.next();
}

export const config = {
  // Everything except Next internals and static assets (paths with a dot).
  matcher: ["/((?!_next|.*\\..*).*)"],
};
