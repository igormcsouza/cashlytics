"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { completeNewPassword, login } from "@/lib/auth";

export default function Login() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // First login with a temporary password: Cognito asks for a new one.
  const [challengeSession, setChallengeSession] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (challengeSession) {
        if (newPassword !== confirmPassword) {
          throw new Error("Passwords do not match.");
        }
        await completeNewPassword(email, newPassword, challengeSession);
      } else {
        const result = await login(email, password);
        if (result.status === "new_password_required") {
          setChallengeSession(result.session);
          return;
        }
      }
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass =
    "w-full bg-slate-950 border border-slate-700 text-slate-100 " +
    "placeholder:text-slate-500 rounded-lg px-3 py-2 focus:outline-none " +
    "focus:ring-2 focus:ring-indigo-400 focus:border-indigo-400";
  const labelClass = "block text-sm font-medium text-slate-300 mb-1";

  return (
    <div className="max-w-4xl mx-auto py-10 px-4">
      <h1 className="text-3xl font-bold text-indigo-300 text-center mb-6">
        💰 Cashlytics
      </h1>

      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl shadow-black/50 p-6 w-full max-w-md mx-auto">
        <h2 className="text-xl font-bold text-indigo-300 mb-4">
          {challengeSession ? "Choose a new password" : "Sign in"}
        </h2>

        {challengeSession && (
          <p className="text-sm text-slate-400 -mt-2 mb-4">
            First login: replace your temporary password with one of your own.
          </p>
        )}

        {error && (
          <div
            role="alert"
            className="bg-red-500/15 text-red-300 ring-1 ring-red-500/25 rounded-lg px-4 py-3 mb-4"
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {!challengeSession ? (
            <>
              <div>
                <label className={labelClass}>Email</label>
                <input
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Password</label>
                <input
                  type="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className={inputClass}
                />
              </div>
            </>
          ) : (
            <>
              <div>
                <label className={labelClass}>New password</label>
                <input
                  type="password"
                  required
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••"
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Confirm new password</label>
                <input
                  type="password"
                  required
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  className={inputClass}
                />
              </div>
            </>
          )}

          <div className="pt-2">
            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-indigo-500 hover:bg-indigo-400 disabled:opacity-50 text-white font-semibold py-2 rounded-lg"
            >
              {submitting
                ? "Signing in…"
                : challengeSession
                  ? "Set password and sign in"
                  : "Sign in"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
