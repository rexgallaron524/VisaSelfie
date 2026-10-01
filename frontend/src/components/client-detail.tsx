"use client";
import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useHydrated } from "@/lib/use-hydrated";
import { apiRequest } from "@/lib/api";
import { DateText, readable, Status } from "@/components/process-ui";
import { LinkPanel } from "@/components/link-panel";
import type { IssuedLink, ProcessDetail } from "@/lib/types";

export function ClientDetail({ process }: { process: ProcessDetail }) {
  const router = useRouter();
  const hydrated = useHydrated();
  const [issued, setIssued] = useState<IssuedLink | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [confirmation, setConfirmation] = useState<"link" | "delete" | null>(
    null,
  );
  const video = process.video;
  const closed = ["submitted", "reviewed", "deleted"].includes(process.status);
  const endpoint = `/admin/processes/${process.id}`;
  async function act(action: "link" | "delete" | "review") {
    setPending(true);
    setError("");
    try {
      if (action === "link")
        setIssued(
          await apiRequest<IssuedLink>(`${endpoint}/link`, { method: "POST" }),
        );
      else
        await apiRequest<void>(
          `${endpoint}/${action === "delete" ? "video" : "review"}`,
          { method: action === "delete" ? "DELETE" : "POST" },
        );
      if (action === "delete") setPlaying(false);
      setConfirmation(null);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed. Please retry.");
      router.refresh();
    } finally {
      setPending(false);
    }
  }
  return (
    <>
      <Link href="/dashboard/clients" className="touch-target text-sm text-teal-700">
        ← Clients
      </Link>
      <div className="my-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 flex-1">
          <h1 className="mb-3 text-3xl font-semibold">{process.full_name}</h1>
          <Status value={process.status} />
        </div>
        <button
          className="touch-target shrink-0 rounded-lg border border-slate-300 px-4 py-2 text-sm"
          disabled={!hydrated}
          onClick={() => router.refresh()}
        >
          Refresh status
        </button>
      </div>
      {error && (
        <p
          role="alert"
          className="mb-5 rounded-xl bg-red-50 p-4 text-sm text-red-700"
        >
          {error}
        </p>
      )}
      {confirmation && (
        <div
          role="alertdialog"
          aria-label={
            confirmation === "delete"
              ? "Confirm video deletion"
              : "Confirm link replacement"
          }
          className="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-5"
        >
          <p className="text-sm leading-6">
            {confirmation === "delete"
              ? "Permanently delete this video from private storage? The client record and audit history will remain. This cannot be undone."
              : "Generate a new 48-hour link? Any previous link will stop working. Registration and consent already provided will be preserved."}
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              disabled={pending || !hydrated}
              onClick={() => act(confirmation)}
              className="primary-button"
            >
              {pending ? "Working…" : "Confirm"}
            </button>
            <button
              disabled={pending || !hydrated}
              onClick={() => setConfirmation(null)}
              className="touch-target px-4 text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
      <div className="grid items-start gap-6 lg:grid-cols-2">
        <div className="min-w-0 space-y-6">
          <section className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-6">
            <h2 className="mb-5 text-lg font-semibold">Client information</h2>
            <dl className="space-y-4 text-sm">
              {[
                ["Full name", process.full_name],
                [
                  "Date of birth",
                  process.date_of_birth ?? "Awaiting registration",
                ],
                [
                  "Passport number",
                  process.passport_number ?? "Awaiting registration",
                ],
                ["Phone", process.phone_number],
                ["Email address", process.email ?? "Not provided"],
                ["Alternative phone", process.alternative_phone_number ?? "Not provided"],
                ["Residential address", process.address ?? "Not provided"],
              ].map(([label, value]) => (
                <div key={label}>
                  <dt className="text-xs text-slate-500">{label}</dt>
                  <dd className="mt-1 whitespace-pre-line break-words">{value}</dd>
                </div>
              ))}
              <div>
                <dt className="text-xs text-slate-500">Created</dt>
                <dd className="mt-1">
                  <DateText value={process.created_at} />
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Consent</dt>
                <dd className="mt-1">
                  {process.consent ? (
                    <>
                      <DateText value={process.consent.accepted_at} />
                      <br />
                      Notice version {process.consent.consent_version}
                    </>
                  ) : (
                    "Not yet accepted"
                  )}
                </dd>
              </div>
            </dl>
          </section>
          {!closed && (
            <section className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-6">
              {issued ? (
                <LinkPanel link={issued} />
              ) : (
                <>
                  <h2 className="font-semibold">Registration link</h2>
                  <p className="my-3 text-sm text-slate-500">
                    Expires <DateText value={process.link_expires_at} />. For
                    privacy, the original link cannot be retrieved. Generate a
                    replacement if you need to send it again.
                  </p>
                  <button
                    onClick={() => setConfirmation("link")}
                    disabled={pending || !hydrated}
                    className="primary-button w-full sm:w-auto"
                  >
                    Generate new link
                  </button>
                </>
              )}
            </section>
          )}
        </div>
        <div className="min-w-0 space-y-6">
          <section className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-6">
            <h2 className="text-lg font-semibold">Facial video</h2>
            {video && video.status !== "deleted" && (
              <div className="my-4 rounded-xl bg-amber-50 p-4 text-sm text-amber-950">
                <p className="font-semibold">
                  {video.assessment?.passed ? "Guided checks passed — manual review required" : "No automated assessment for this recording"}
                </p>
                <p className="mt-2">Identity and liveness are not verified. Review for face coverings, photo/video replay and other suspicious signs before accepting.</p>
                {video.assessment && <p className="mt-2">Checked lighting, one face, framing, sharpness and the requested movement sequence.</p>}
              </div>
            )}
            {!video ? (
              <p className="mt-4 text-sm text-slate-500">
                Waiting for the applicant to submit their recording.
              </p>
            ) : video.status === "deleted" ? (
              <p className="mt-4 text-sm text-slate-500">
                Video deleted <DateText value={video.deleted_at} />. Audit
                history has been retained.
              </p>
            ) : (
              <>
                <p className="my-3 text-xs text-slate-500">
                  {video.duration.toFixed(1)} seconds ·{" "}
                  {(video.file_size / 1024 / 1024).toFixed(1)} MB ·{" "}
                  <DateText value={video.uploaded_at} />
                </p>
                {video.status === "active" ? (
                  <>
                    {playing ? (
                      <video
                        src={`/api${endpoint}/video`}
                        controls
                        playsInline
                        preload="metadata"
                        className="aspect-[4/3] max-h-[60svh] w-full rounded-xl bg-slate-950 object-contain"
                        onError={() =>
                          setError(
                            "Unable to load the video. Refresh your session and retry.",
                          )
                        }
                      />
                    ) : (
                      <button
                        className="mb-4 grid aspect-[4/3] max-h-[60svh] w-full place-items-center rounded-xl bg-slate-900 text-sm text-white"
                        disabled={!hydrated}
                        onClick={() => setPlaying(true)}
                      >
                        ▶ View recording
                      </button>
                    )}
                    <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:gap-4">
                      <a
                        href={`/api${endpoint}/video?download=true`}
                        className="touch-target text-sm font-medium text-teal-800 underline"
                      >
                        Download video
                      </a>
                      {process.status !== "reviewed" && (
                        <button
                          disabled={pending || !hydrated}
                          onClick={() => act("review")}
                          className="touch-target text-sm font-medium text-teal-800 underline"
                        >
                          Mark reviewed
                        </button>
                      )}
                      <button
                        disabled={pending || !hydrated}
                        onClick={() => setConfirmation("delete")}
                        className="touch-target text-sm font-medium text-red-700 underline"
                      >
                        Delete video
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <p className="my-4 text-sm text-amber-800">
                      Deletion is pending. Video access is disabled until
                      deletion finishes.
                    </p>
                    <button
                      className="primary-button"
                      disabled={pending || !hydrated}
                      onClick={() => act("delete")}
                    >
                      Retry deletion
                    </button>
                  </>
                )}
              </>
            )}
          </section>
          <section className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-6">
            <h2 className="mb-4 font-semibold">Process history</h2>
            <p className="mb-4 text-xs text-slate-500">Latest 100 events</p>
            <ol className="max-h-96 space-y-4 overflow-y-auto">
              {process.history.map((event) => (
                <li key={event.id} className="border-l-2 border-teal-100 pl-4">
                  <p className="text-sm">{readable(event.action)}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {readable(event.actor_type)} ·{" "}
                    <DateText value={event.created_at} />
                  </p>
                </li>
              ))}
            </ol>
          </section>
        </div>
      </div>
    </>
  );
}
