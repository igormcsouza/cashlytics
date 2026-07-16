// Cognito authentication via the plain JSON API (no SDK dependency).
//
// Tokens live in cookies so the Next.js middleware can gate every page:
//   - cashlytics_id_token       expires with the token (~1h)
//   - cashlytics_refresh_token  30 days, used to silently renew the id token
//
// When NEXT_PUBLIC_COGNITO_CLIENT_ID is not set (local dev without Cognito)
// auth is disabled entirely: no login redirect, no Authorization header.

const CLIENT_ID = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID ?? "";
const REGION = process.env.NEXT_PUBLIC_COGNITO_REGION ?? "us-east-1";
// Overridden locally to point at cognito-local instead of real AWS.
const ENDPOINT =
  process.env.NEXT_PUBLIC_COGNITO_ENDPOINT ??
  `https://cognito-idp.${REGION}.amazonaws.com`;

export const ID_TOKEN_COOKIE = "cashlytics_id_token";
export const REFRESH_TOKEN_COOKIE = "cashlytics_refresh_token";

export const authEnabled = CLIENT_ID !== "";

export type LoginResult =
  | { status: "ok" }
  // First login with a temporary password: Cognito requires a new one.
  | { status: "new_password_required"; session: string };

async function cognito(target: string, body: unknown): Promise<any> {
  const res = await fetch(ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-amz-json-1.1",
      "X-Amz-Target": `AWSCognitoIdentityProviderService.${target}`,
    },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const message =
      data.message ?? data.Message ?? "Authentication failed. Please try again.";
    throw new Error(message);
  }
  return data;
}

function setCookie(name: string, value: string, maxAgeSeconds: number) {
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAgeSeconds}; samesite=lax; secure`;
}

function getCookie(name: string): string | null {
  const match = document.cookie
    .split("; ")
    .find((c) => c.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
}

function clearCookie(name: string) {
  document.cookie = `${name}=; path=/; max-age=0; samesite=lax; secure`;
}

function storeTokens(result: {
  IdToken?: string;
  RefreshToken?: string;
  ExpiresIn?: number;
}) {
  if (result.IdToken) {
    setCookie(ID_TOKEN_COOKIE, result.IdToken, result.ExpiresIn ?? 3600);
  }
  if (result.RefreshToken) {
    setCookie(REFRESH_TOKEN_COOKIE, result.RefreshToken, 30 * 24 * 3600);
  }
}

export async function login(
  email: string,
  password: string,
): Promise<LoginResult> {
  const data = await cognito("InitiateAuth", {
    AuthFlow: "USER_PASSWORD_AUTH",
    ClientId: CLIENT_ID,
    AuthParameters: { USERNAME: email, PASSWORD: password },
  });
  if (data.ChallengeName === "NEW_PASSWORD_REQUIRED") {
    return { status: "new_password_required", session: data.Session };
  }
  storeTokens(data.AuthenticationResult ?? {});
  return { status: "ok" };
}

/** Complete the NEW_PASSWORD_REQUIRED challenge of a first login. */
export async function completeNewPassword(
  email: string,
  newPassword: string,
  session: string,
): Promise<void> {
  const data = await cognito("RespondToAuthChallenge", {
    ChallengeName: "NEW_PASSWORD_REQUIRED",
    ClientId: CLIENT_ID,
    Session: session,
    ChallengeResponses: { USERNAME: email, NEW_PASSWORD: newPassword },
  });
  storeTokens(data.AuthenticationResult ?? {});
}

/** Current id token, silently refreshed when expired. Null when logged out. */
export async function getIdToken(): Promise<string | null> {
  if (!authEnabled) return null;
  const idToken = getCookie(ID_TOKEN_COOKIE);
  if (idToken) return idToken;

  const refreshToken = getCookie(REFRESH_TOKEN_COOKIE);
  if (!refreshToken) return null;
  try {
    const data = await cognito("InitiateAuth", {
      AuthFlow: "REFRESH_TOKEN_AUTH",
      ClientId: CLIENT_ID,
      AuthParameters: { REFRESH_TOKEN: refreshToken },
    });
    storeTokens(data.AuthenticationResult ?? {});
    return getCookie(ID_TOKEN_COOKIE);
  } catch {
    logout();
    return null;
  }
}

export function logout() {
  clearCookie(ID_TOKEN_COOKIE);
  clearCookie(REFRESH_TOKEN_COOKIE);
}
