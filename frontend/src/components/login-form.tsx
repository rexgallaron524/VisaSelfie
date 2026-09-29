"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { apiRequest } from "@/lib/api";
import type { Admin } from "@/lib/types";
import { useHydrated } from "@/lib/use-hydrated";

export function LoginForm() {
  const router = useRouter();
  const hydrated = useHydrated();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setPending(true);
    const form = new FormData(event.currentTarget);
    try {
      await apiRequest<Admin>("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: form.get("email"),
          password: form.get("password"),
        }),
      });
      router.replace("/dashboard");
      router.refresh();
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Unable to sign in. Please try again.",
      );
      setPending(false);
    }
  }

  return (
    <form
      method="post"
      onSubmit={submit}
      className="mt-9 space-y-5"
      aria-busy={pending}
    >
      <div>
        <label htmlFor="email" className="field-label">
          Email address
        </label>
        <input
          id="email"
          name="email"
          type="email"
          autoComplete="username"
          required
          maxLength={254}
          placeholder="you@company.com"
          className="field-input"
          disabled={pending}
        />
      </div>
      <div>
        <label htmlFor="password" className="field-label">
          Password
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          maxLength={128}
          placeholder="Enter your password"
          className="field-input"
          disabled={pending}
        />
      </div>
      {error && (
        <p
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
        >
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={pending || !hydrated}
        className="primary-button w-full"
      >
        {pending ? "Signing in…" : "Sign in to your workspace"}
        {!pending && <span aria-hidden="true">→</span>}
      </button>
      <p className="text-center text-xs leading-5 text-slate-500">
        Administrator access only. Contact your operator if you need an account.
      </p>
    </form>
  );
}
