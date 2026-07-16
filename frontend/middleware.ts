import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Auth is off when the app is built without Cognito (local docker-compose).
const AUTH_ENABLED = Boolean(process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID);

// Keep in sync with lib/auth.ts (middleware runs on the edge runtime, so the
// names are duplicated here instead of importing browser-oriented code).
const ID_TOKEN_COOKIE = "cashlytics_id_token";
const REFRESH_TOKEN_COOKIE = "cashlytics_refresh_token";

export function middleware(request: NextRequest) {
  if (!AUTH_ENABLED) return NextResponse.next();

  // A refresh token alone counts as logged in: the client silently renews the
  // id token on the next API call.
  const loggedIn =
    request.cookies.has(ID_TOKEN_COOKIE) ||
    request.cookies.has(REFRESH_TOKEN_COOKIE);
  const isLoginPage = request.nextUrl.pathname === "/login";

  if (!loggedIn && !isLoginPage) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  if (loggedIn && isLoginPage) {
    return NextResponse.redirect(new URL("/", request.url));
  }
  return NextResponse.next();
}

export const config = {
  // Everything except Next internals and static assets (paths with a dot).
  matcher: ["/((?!_next|.*\\..*).*)"],
};
