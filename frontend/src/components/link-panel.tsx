"use client";
import { useState } from "react";
import { DateText } from "@/components/process-ui";
import type { IssuedLink } from "@/lib/types";

export function LinkPanel({ link }: { link: IssuedLink }) {
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);
  const url = link.registration_url;
  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setFailed(false);
    } catch {
      setFailed(true);
    }
  }
  return (
    <div className="min-w-0 rounded-2xl border border-[#314f7d] bg-[#111f37] p-5 sm:p-6">
      <span className="mb-4 grid size-10 place-items-center rounded-xl bg-[#4f8cff] text-white" aria-hidden="true">✓</span>
      <h2 className="font-semibold text-[#b9d0ff]">Registration link ready</h2>
      <p className="my-3 text-sm leading-6 text-[#c5d0e2]">
        Copy this private link and send it to the applicant using WhatsApp. It
        can be used once and expires in 48 hours.
      </p>
      <label htmlFor="registration-link" className="field-label">
        Private registration link
      </label>
      <input
        id="registration-link"
        readOnly
        value={url}
        onFocus={(e) => e.currentTarget.select()}
        className="field-input"
      />
      <button type="button" onClick={copy} className="primary-button mt-3 w-full sm:w-auto">
        {copied ? "Copied!" : "Copy link"}
      </button>
      {failed && (
        <p role="alert" className="mt-2 text-sm">
          Select the link above and copy it manually.
        </p>
      )}
      <p className="mt-3 text-xs leading-5 text-[#9cabc0]">
        Expires <DateText value={link.expires_at} />. Copy it before leaving
        this page; it cannot be retrieved later.
      </p>
    </div>
  );
}
