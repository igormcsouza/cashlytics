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
    "w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 " +
    "text-slate-100 placeholder-slate-500 focus:outline-none " +
    "focus:ring-2 focus:ring-indigo-500";

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <h1 className="text-3xl font-bold text-indigo-300 text-center mb-8">
          💰 Cashlytics
        </h1>

        <form
          onSubmit={handleSubmit}
          className="bg-slate-900 border border-slate-800 rounded-lg shadow-xl shadow-black/20 p-6 space-y-4"
        >
          <h2 className="text-lg font-semibold text-slate-200">
            {challengeSession ? "Choose a new password" : "Sign in"}
          </h2>

          {challengeSession && (
            <p className="text-sm text-slate-400">
              First login: replace your temporary password with one of your
              own.
            </p>
          )}

          {error && (
            <div
              role="alert"
              className="bg-red-500/15 text-red-300 ring-1 ring-red-500/25 rounded-lg px-4 py-3 text-sm"
            >
              {error}
            </div>
          )}

          {!challengeSession ? (
            <>
              <label className="block">
                <span className="text-sm text-slate-400">Email</span>
                <input
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className={inputClass}
                />
              </label>
              <label className="block">
                <span className="text-sm text-slate-400">Password</span>
                <input
                  type="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className={inputClass}
                />
              </label>
            </>
          ) : (
            <>
              <label className="block">
                <span className="text-sm text-slate-400">New password</span>
                <input
                  type="password"
                  required
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••"
                  className={inputClass}
                />
              </label>
              <label className="block">
                <span className="text-sm text-slate-400">
                  Confirm new password
                </span>
                <input
                  type="password"
                  required
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  className={inputClass}
                />
              </label>
            </>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-indigo-500 hover:bg-indigo-400 disabled:opacity-50 text-white font-semibold px-4 py-2 rounded-lg shadow-lg shadow-indigo-950/40"
          >
            {submitting
              ? "Signing in…"
              : challengeSession
                ? "Set password and sign in"
                : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
