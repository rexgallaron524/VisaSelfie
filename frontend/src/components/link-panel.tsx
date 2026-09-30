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
    <div className="rounded-xl border border-teal-200 bg-teal-50 p-5">
      <h2 className="font-semibold text-teal-900">Registration link ready</h2>
      <p className="my-3 text-sm leading-6 text-teal-900">
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
      <button type="button" onClick={copy} className="primary-button mt-3">
        {copied ? "Copied!" : "Copy link"}
      </button>
      {failed && (
        <p role="alert" className="mt-2 text-sm">
          Select the link above and copy it manually.
        </p>
      )}
      <p className="mt-3 text-xs text-teal-800">
        Expires <DateText value={link.expires_at} />. Copy it before leaving
        this page; it cannot be retrieved later.
      </p>
    </div>
  );
}
