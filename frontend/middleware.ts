import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Auth is off when the app is built without Cognito (local docker-compose).
const AUTH_ENABLED = Boolean(process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID);

// Keep in sync with lib/auth.ts (middleware runs on the edge runtime, so the
// names are duplicated here instead of importing browser-oriented code).
const ID_TOKEN_COOKIE = "cashlytics_id_token";
const REFRESH_TOKEN_COOKIE = "cashlytics_refresh_token";

// A relative Location header, resolved by the browser against the page it
// actually requested (the CloudFront domain) — never build an absolute URL
// from `request.url` here. Behind CloudFront the Lambda origin never sees the
// real Host (the distribution's origin request policy strips it), so
// `request.url`/`request.nextUrl` resolve to the origin's own raw Function URL
// instead of the public domain; redirecting there breaks every `/_next/static/*`
// asset, since those are only served through CloudFront's S3 route.
function redirect(path: string): NextResponse {
  const res = new NextResponse(null, { status: 307 });
  res.headers.set("Location", path);
  return res;
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
    return redirect("/login");
  }
  if (loggedIn && isLoginPage) {
    return redirect("/");
  }
  return NextResponse.next();
}

export const config = {
  // Everything except Next internals and static assets (paths with a dot).
  matcher: ["/((?!_next|.*\\..*).*)"],
};
