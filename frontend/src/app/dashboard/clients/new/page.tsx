"use client";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { apiRequest } from "@/lib/api";
import { LinkPanel } from "@/components/link-panel";
import { useHydrated } from "@/lib/use-hydrated";
import type { IssuedLink } from "@/lib/types";

export default function NewClientPage() {
  const hydrated = useHydrated();
  const [link, setLink] = useState<IssuedLink | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      setLink(
        await apiRequest<IssuedLink>("/admin/processes", {
          method: "POST",
          body: JSON.stringify(Object.fromEntries(form)),
        }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to create client.");
    } finally {
      setPending(false);
    }
  }
  return (
    <div className="min-w-0 max-w-xl">
      <Link href="/dashboard/clients" className="touch-target text-sm text-teal-700">
        ← Clients
      </Link>
      <h1 className="mt-5 text-3xl font-semibold">Create a client</h1>
      <p className="my-4 text-sm leading-6 text-slate-500">
        Enter their name and phone number. The applicant will supply their
        passport details and date of birth through the private registration
        link.
      </p>
      {link ? (
        <>
          <LinkPanel link={link} />
          <Link
            href={`/dashboard/clients/${link.process_id}`}
            className="touch-target mt-5 text-teal-700 underline"
          >
            View client process →
          </Link>
        </>
      ) : (
        <form
          method="post"
          onSubmit={submit}
          className="space-y-5 rounded-2xl border border-slate-200 bg-white p-4 sm:p-6"
        >
          <div>
            <label htmlFor="full_name" className="field-label">
              Full name
            </label>
            <input
              id="full_name"
              name="full_name"
              required
              minLength={2}
              maxLength={200}
              className="field-input"
            />
          </div>
          <div>
            <label htmlFor="phone_number" className="field-label">
              Phone number including country code
            </label>
            <input
              id="phone_number"
              name="phone_number"
              type="tel"
              required
              minLength={7}
              maxLength={32}
              placeholder="+44 7700 900000"
              className="field-input"
            />
          </div>
          {error && (
            <p role="alert" className="text-sm text-red-700">
              {error}
            </p>
          )}
          <button disabled={pending || !hydrated} className="primary-button w-full sm:w-auto">
            {pending ? "Creating…" : "Create client and link"}
          </button>
        </form>
      )}
    </div>
  );
}
