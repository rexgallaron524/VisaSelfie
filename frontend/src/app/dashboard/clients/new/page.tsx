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
    <div className="min-w-0">
      <Link href="/dashboard/clients" className="touch-target rounded-lg px-2 text-sm font-semibold text-[#8cb5ff] hover:bg-[#182641]">
        ← Clients
      </Link>
      <p className="section-label mt-5">New registration</p>
      <h1 className="page-title mt-2">Create a client</h1>
      <p className="mt-3 max-w-xl text-sm leading-6 text-[#a8b3c5]">
        Enter their name and phone number. The applicant will supply their
        passport details and date of birth through the private registration
        link.
      </p>
      <div className="mt-7 grid gap-6 xl:grid-cols-[minmax(0,42rem)_minmax(18rem,1fr)]">
      {link ? (
        <>
          <LinkPanel link={link} />
          <Link
            href={`/dashboard/clients/${link.process_id}`}
            className="touch-target mt-5 font-semibold text-[#8cb5ff] underline"
          >
            View client process →
          </Link>
        </>
      ) : (
        <form
          method="post"
          onSubmit={submit}
          className="surface-card space-y-5 p-5 sm:p-7"
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
            <p role="alert" className="rounded-xl border border-[#713744] bg-[#321923] p-4 text-sm text-[#ffabbc]">
              {error}
            </p>
          )}
          <button disabled={pending || !hydrated} className="primary-button w-full sm:w-auto">
            {pending ? "Creating…" : "Create client and link"}
          </button>
        </form>
      )}
      <aside className="soft-panel h-fit p-5 sm:p-6">
        <span className="grid size-10 place-items-center rounded-xl bg-[#172a4d] text-[#79a8ff]" aria-hidden="true">↗</span>
        <h2 className="mt-5 font-semibold text-[#f8fafc]">What happens next</h2>
        <ol className="mt-4 space-y-4 text-sm leading-6 text-[#a8b3c5]">
          <li className="flex gap-3"><span className="font-bold text-[#8cb5ff]">01</span><span>A private registration link is created for this client.</span></li>
          <li className="flex gap-3"><span className="font-bold text-[#8cb5ff]">02</span><span>You share the link with the same WhatsApp number entered here.</span></li>
          <li className="flex gap-3"><span className="font-bold text-[#8cb5ff]">03</span><span>The applicant enters passport details, gives consent, and records their video.</span></li>
        </ol>
        <p className="mt-5 border-t border-[#2b3950] pt-4 text-xs leading-5 text-[#8e9db2]">Registration links remain valid for 48 hours.</p>
      </aside>
      </div>
    </div>
  );
}
