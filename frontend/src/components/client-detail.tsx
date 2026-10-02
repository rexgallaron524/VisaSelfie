"use client";
import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useHydrated } from "@/lib/use-hydrated";
import { apiRequest } from "@/lib/api";
import { DateText, readable, Status } from "@/components/process-ui";
import { LinkPanel } from "@/components/link-panel";
import { ConfirmationModal } from "@/components/confirmation-modal";
import type { IssuedLink, ProcessDetail } from "@/lib/types";

export function ClientDetail({ process }: { process: ProcessDetail }) {
  const router = useRouter();
  const hydrated = useHydrated();
  const [issued, setIssued] = useState<IssuedLink | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [confirmation, setConfirmation] = useState<
    "link" | "delete" | "review" | null
  >(null);
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
      setConfirmation(null);
      router.refresh();
    } finally {
      setPending(false);
    }
  }
  const confirmationContent = confirmation
    ? {
        link: {
          title: "Replace registration link?",
          description:
            "A new private link will be valid for 48 hours and the previous link will stop working. Registration and consent already provided will be preserved.",
          confirmLabel: "Generate replacement",
          destructive: false,
        },
        delete: {
          title: "Delete facial video?",
          description:
            "The video will be permanently removed from private storage. The client record and audit history will remain. This action cannot be undone.",
          confirmLabel: "Delete permanently",
          destructive: true,
        },
        review: {
          title: "Mark video as reviewed?",
          description:
            "This records that an administrator has completed the manual video review and updates the client process status.",
          confirmLabel: "Mark reviewed",
          destructive: false,
        },
      }[confirmation]
    : null;
  return (
    <>
      <Link href="/dashboard/clients" className="touch-target rounded-lg px-2 text-sm font-semibold text-[#8cb5ff] hover:bg-[#182641]">
        ← Clients
      </Link>
      <div className="my-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0 flex-1">
          <p className="section-label mb-2">Client process</p>
          <h1 className="mb-3 text-3xl font-semibold tracking-[-0.03em] sm:text-4xl">{process.full_name}</h1>
          <Status value={process.status} />
        </div>
        <button
          className="secondary-button shrink-0"
          disabled={!hydrated}
          onClick={() => router.refresh()}
        >
          Refresh status
        </button>
      </div>
      {error && (
        <p
          role="alert"
          className="mb-5 rounded-xl border border-[#713744] bg-[#321923] p-4 text-sm text-[#ffabbc]"
        >
          {error}
        </p>
      )}
      {confirmation && confirmationContent && (
        <ConfirmationModal
          open
          title={confirmationContent.title}
          description={confirmationContent.description}
          confirmLabel={confirmationContent.confirmLabel}
          destructive={confirmationContent.destructive}
          pending={pending}
          onConfirm={() => act(confirmation)}
          onClose={() => setConfirmation(null)}
        />
      )}
      <div className="grid items-start gap-6 xl:grid-cols-[minmax(19rem,0.8fr)_minmax(26rem,1.2fr)]">
        <div className="min-w-0 space-y-6">
          <section className="surface-card p-5 sm:p-6">
            <p className="section-label mb-1">Profile</p><h2 className="mb-5 text-lg font-semibold">Client information</h2>
            <dl className="grid min-w-0 grid-cols-1 gap-x-5 gap-y-4 text-sm sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
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
                <div key={label} className="min-w-0">
                  <dt className="text-xs font-medium text-[#8e9db2]">{label}</dt>
                  <dd className="mt-1 whitespace-pre-line break-words font-medium text-[#d9e2f1]">{value}</dd>
                </div>
              ))}
              <div>
                <dt className="text-xs font-medium text-[#8e9db2]">Created</dt>
                <dd className="mt-1">
                  <DateText value={process.created_at} />
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-[#8e9db2]">Consent</dt>
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
            <section className="surface-card p-5 sm:p-6">
              {issued ? (
                <LinkPanel link={issued} />
              ) : (
                <>
                  <h2 className="font-semibold">Registration link</h2>
                  <p className="my-3 text-sm leading-6 text-[#a8b3c5]">
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
          <section className="surface-card p-5 sm:p-6">
            <p className="section-label mb-1">Submission</p><h2 className="text-lg font-semibold">Facial video</h2>
            {video && video.status !== "deleted" && (
              <div className="my-4 rounded-xl border border-[#68451d] bg-[#2e2114] p-4 text-sm text-[#f2cf9e]">
                <p className="font-semibold">
                  {video.assessment?.passed ? "Guided checks passed — manual review required" : "No automated assessment for this recording"}
                </p>
                <p className="mt-2">Identity and liveness are not verified. Review for face coverings, photo/video replay and other suspicious signs before accepting.</p>
                {video.assessment && <p className="mt-2">Checked lighting, one face, framing, sharpness and the requested movement sequence.</p>}
              </div>
            )}
            {!video ? (
              <p className="mt-4 text-sm text-[#a8b3c5]">
                Waiting for the applicant to submit their recording.
              </p>
            ) : video.status === "deleted" ? (
              <p className="mt-4 text-sm text-[#a8b3c5]">
                Video deleted <DateText value={video.deleted_at} />. Audit
                history has been retained.
              </p>
            ) : (
              <>
                <p className="my-3 text-xs text-[#8e9db2]">
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
                        className="aspect-[4/3] max-h-[60svh] w-full rounded-2xl bg-[#04070d] object-contain ring-4 ring-[#273449]"
                        onError={() =>
                          setError(
                            "Unable to load the video. Refresh your session and retry.",
                          )
                        }
                      />
                    ) : (
                      <button
                        className="mb-4 grid aspect-[4/3] max-h-[60svh] w-full place-items-center rounded-2xl bg-[#090e18] text-sm font-semibold text-white shadow-inner ring-1 ring-[#273449] transition hover:bg-[#111b2b]"
                        disabled={!hydrated}
                        onClick={() => setPlaying(true)}
                      >
                        ▶ View recording
                      </button>
                    )}
                    <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:gap-4">
                      <a
                        href={`/api${endpoint}/video?download=true`}
                        className="touch-target text-sm font-medium text-[#8cb5ff] underline"
                      >
                        Download video
                      </a>
                      {process.status !== "reviewed" && (
                        <button
                          disabled={pending || !hydrated}
                          onClick={() => setConfirmation("review")}
                          className="touch-target text-sm font-medium text-[#8cb5ff] underline"
                        >
                          Mark reviewed
                        </button>
                      )}
                      <button
                        disabled={pending || !hydrated}
                        onClick={() => setConfirmation("delete")}
                        className="touch-target text-sm font-medium text-[#ff8fa6] underline"
                      >
                        Delete video
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <p className="my-4 text-sm text-[#f5bd73]">
                      Deletion is pending. Video access is disabled until
                      deletion finishes.
                    </p>
                    <button
                      className="primary-button"
                      disabled={pending || !hydrated}
                      onClick={() => setConfirmation("delete")}
                    >
                      Retry deletion
                    </button>
                  </>
                )}
              </>
            )}
          </section>
          <section className="surface-card p-5 sm:p-6">
            <p className="section-label mb-1">Timeline</p><h2 className="mb-4 font-semibold">Process history</h2>
            <p className="mb-4 text-xs text-[#8e9db2]">Latest 100 events</p>
            <ol className="max-h-96 space-y-4 overflow-y-auto">
              {process.history.map((event) => (
                <li key={event.id} className="border-l-2 border-[#4f8cff] pl-4">
                  <p className="text-sm">{readable(event.action)}</p>
                  <p className="mt-1 text-xs text-[#8e9db2]">
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
