"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiRequest } from "@/lib/api";
import { useHydrated } from "@/lib/use-hydrated";

export function LogoutButton() {
  const router = useRouter();
  const hydrated = useHydrated();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(false);

  async function logout() {
    setPending(true);
    setError(false);
    try {
      await apiRequest<void>("/auth/logout", { method: "POST" });
      router.replace("/login");
      router.refresh();
    } catch {
      setError(true);
      setPending(false);
    }
  }

  return (
    <div className="max-w-40">
      <button
        onClick={logout}
        disabled={pending || !hydrated}
        className="touch-target rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-50 sm:px-4"
      >
        {pending ? "Signing out…" : "Sign out"}
      </button>
      {error && (
        <p role="alert" className="mt-2 text-xs text-red-700">
          Couldn’t sign out. Please retry.
        </p>
      )}
    </div>
  );
}
