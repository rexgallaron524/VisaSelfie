"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import { Brand } from "@/components/brand";
import { useParams } from "next/navigation";
import { CameraRecorder } from "@/components/camera-recorder";
import { apiRequest, ApiError } from "@/lib/api";
import type { PublicState } from "@/lib/types";

type Step =
  | "loading"
  | "registration"
  | "consent"
  | "instructions"
  | "camera"
  | "success"
  | "invalid"
  | "expired"
  | "error";

export default function RegisterPage() {
  const params = useParams<{ token?: string }>();
  const pathToken = params.token;
  const [step, setStep] = useState<Step>("loading");
  const [state, setState] = useState<PublicState | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [token, setToken] = useState("");
  const heading = useRef<HTMLDivElement>(null);

  function linkError(status: number) {
    setStep(status === 410 ? "expired" : "invalid");
  }
  const handleError = useCallback((e: unknown) => {
    if (e instanceof ApiError && [404, 410].includes(e.status))
      linkError(e.status);
    else if (
      e instanceof ApiError &&
      e.status === 409 &&
      e.message.includes("already been submitted")
    )
      setStep("success");
    else setError(e instanceof Error ? e.message : "Please try again.");
  }, []);
  const validate = useCallback(async () => {
    setStep("loading");
    setError("");
    const currentToken = pathToken ?? window.location.hash.slice(1);
    setToken(currentToken);
    if (!currentToken || currentToken.length > 128) {
      setStep("invalid");
      return;
    }
    try {
      const data = await apiRequest<PublicState>("/public/open", {
        method: "POST",
        headers: { Authorization: `Bearer ${currentToken}` },
      });
      setState(data);
      setStep(
        data.consent_accepted
          ? "instructions"
          : data.registered
            ? "consent"
            : "registration",
      );
    } catch (e) {
      if (e instanceof ApiError && [404, 410, 409].includes(e.status))
        handleError(e);
      else {
        setStep("error");
        setError(e instanceof Error ? e.message : "Unable to check your link.");
      }
    }
  }, [handleError, pathToken]);
  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (active) void validate();
    });
    const change = () => {
      void validate();
    };
    window.addEventListener("hashchange", change);
    return () => {
      active = false;
      window.removeEventListener("hashchange", change);
    };
  }, [validate]);
  useEffect(() => {
    heading.current?.focus();
  }, [step]);

  async function register(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      await apiRequest<void>("/public/register", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify(Object.fromEntries(form)),
      });
      setStep("consent");
    } catch (e) {
      handleError(e);
    } finally {
      setPending(false);
    }
  }
  async function consent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      await apiRequest<void>("/public/consent", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          accepted: true,
          version: state?.consent_version,
        }),
      });
      setStep("instructions");
    } catch (e) {
      handleError(e);
    } finally {
      setPending(false);
    }
  }
  const stepIndex = [
    "registration",
    "consent",
    "instructions",
    "camera",
  ].indexOf(step);
  const stepNames = ["Your details", "Privacy & consent", "Before you record", "Facial video"];
  return (
    <main className="page-shell mx-auto min-h-dvh max-w-6xl py-4 sm:py-7 lg:py-9">
      <header className="flex items-center justify-between gap-4"><Brand /><span className="hidden rounded-full border border-[#314f7d] bg-[#172a4d] px-3 py-1.5 text-xs font-semibold text-[#9dbdff] sm:inline-flex">Private registration</span></header>
      <div className={`mt-5 grid items-start gap-6 sm:mt-8 ${stepIndex >= 0 ? "lg:grid-cols-[17rem_minmax(0,42rem)] lg:justify-center xl:grid-cols-[19rem_minmax(0,45rem)]" : "mx-auto max-w-xl"}`}>
        {stepIndex >= 0 && (
          <aside className="soft-panel sticky top-8 hidden overflow-hidden p-6 lg:block">
            <p className="section-label">Registration journey</p>
            <ol className="mt-6 space-y-1">
              {stepNames.map((name, index) => (
                <li key={name} className={`flex items-center gap-3 rounded-xl px-3 py-3 text-sm ${index === stepIndex ? "bg-[#1a2639] font-semibold text-[#f8fafc] shadow-sm" : index < stepIndex ? "text-[#8cb5ff]" : "text-[#7f8da2]"}`}>
                  <span className={`grid size-7 shrink-0 place-items-center rounded-full text-xs font-bold ${index < stepIndex ? "bg-[#4f8cff] text-white" : index === stepIndex ? "bg-[#271f48] text-[#b8a4ff]" : "bg-[#202b3d] text-[#8190a6]"}`}>{index < stepIndex ? "✓" : index + 1}</span>
                  {name}
                </li>
              ))}
            </ol>
            <div className="mt-7 border-t border-[#2b3950] pt-5"><p className="text-sm font-semibold text-[#d9e2f1]">Need help?</p><p className="mt-2 text-xs leading-5 text-[#8e9db2]">Contact the operator who sent you this private link.</p></div>
          </aside>
        )}
      <div
        className="surface-card min-w-0 overflow-hidden p-5 sm:p-8 lg:p-9"
        ref={heading}
        tabIndex={-1}
        style={{ outline: "none" }}
      >
        {stepIndex >= 0 && (
          <div className="mb-7 lg:hidden">
            <div className="mb-3 flex items-center justify-between gap-3"><p className="section-label">
              STEP {stepIndex + 1} OF 4
            </p><p className="text-xs font-semibold text-[#a8b3c5]">{stepNames[stepIndex]}</p></div>
            <div className="flex gap-2" aria-hidden="true">
              {[0, 1, 2, 3].map((n) => (
                <span
                  key={n}
                  className={`h-1.5 flex-1 rounded-full ${n <= stepIndex ? "bg-[#4f8cff]" : "bg-[#273449]"}`}
                />
              ))}
            </div>
          </div>
        )}
        {step === "loading" && (
          <p role="status">Checking your registration link…</p>
        )}
        {step === "invalid" && (
          <>
            <h1 className="text-2xl font-semibold">This link isn’t valid</h1>
            <p className="mt-4 text-sm leading-7 text-[#b8c4d6]">
              It may be incomplete or have been replaced. Please ask the
              operator who invited you for a new registration link.
            </p>
          </>
        )}
        {step === "expired" && (
          <>
            <h1 className="text-2xl font-semibold">Your link has expired</h1>
            <p className="mt-4 text-sm leading-7 text-[#b8c4d6]">
              Registration links expire after 48 hours. Contact the operator who
              invited you to request a new link.
            </p>
          </>
        )}
        {step === "success" && (
          <>
            <div
              aria-hidden="true"
              className="mb-5 grid size-14 place-items-center rounded-full bg-[#172a4d] text-2xl text-[#8cb5ff]"
            >
              ✓
            </div>
            <h1 className="text-2xl font-semibold">Recording submitted</h1>
            <p className="mt-4 text-sm leading-7 text-[#b8c4d6]">
              Your recording has been received. Your operator can now review it.
              You can close this page.
            </p>
          </>
        )}
        {step === "error" && (
          <>
            <h1 className="text-2xl font-semibold">
              We couldn’t check your link
            </h1>
            <button onClick={validate} className="primary-button mt-5">
              Try again
            </button>
          </>
        )}
        {step === "registration" && (
          <>
            <p className="section-label mb-2">Applicant information</p>
            <h1 className="text-3xl font-semibold tracking-[-0.03em]">Your details</h1>
            <p className="mt-3 text-sm leading-6 text-[#a8b3c5]">
              Enter your details exactly as they appear on your passport.
            </p>
            <form method="post" onSubmit={register} className="mt-7 space-y-5">
              <div>
                <label htmlFor="full_name" className="field-label">
                  Full name
                </label>
                <input
                  id="full_name"
                  name="full_name"
                  autoComplete="name"
                  defaultValue={state?.full_name}
                  required
                  minLength={2}
                  maxLength={200}
                  className="field-input"
                />
              </div>
              <div>
                <label htmlFor="date_of_birth" className="field-label">
                  Date of birth
                </label>
                <input
                  id="date_of_birth"
                  name="date_of_birth"
                  type="date"
                  autoComplete="bday"
                  required
                  min="1900-01-01"
                  max={new Date().toISOString().slice(0, 10)}
                  className="field-input"
                />
              </div>
              <div>
                <label htmlFor="passport_number" className="field-label">
                  Passport number
                </label>
                <input
                  id="passport_number"
                  name="passport_number"
                  required
                  minLength={5}
                  maxLength={32}
                  autoCapitalize="characters"
                  autoComplete="off"
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
                  autoComplete="tel"
                  value={state?.phone_number ?? ""}
                  readOnly
                  aria-describedby="phone-number-help"
                  required
                  minLength={7}
                  maxLength={32}
                  className="field-input"
                />
                <p id="phone-number-help" className="mt-2 text-sm text-[#a8b3c5]">
                  This number was provided by the operator who invited you and cannot be
                  changed here. If it is incorrect, contact your operator.
                </p>
              </div>
              <fieldset className="soft-panel space-y-5 p-4 sm:p-5">
                <legend className="px-2 text-sm font-semibold text-[#d9e2f1]">Additional contact details <span className="font-normal text-[#8e9db2]">(optional)</span></legend>
                <div>
                  <label htmlFor="email" className="field-label">Email address</label>
                  <input id="email" name="email" type="email" autoComplete="email" maxLength={254} className="field-input" />
                </div>
                <div>
                  <label htmlFor="alternative_phone_number" className="field-label">Alternative phone number including country code</label>
                  <input id="alternative_phone_number" name="alternative_phone_number" type="tel" autoComplete="section-alternative tel" maxLength={32} className="field-input" />
                </div>
                <div>
                  <label htmlFor="address" className="field-label">Residential address</label>
                  <textarea id="address" name="address" autoComplete="street-address" rows={3} maxLength={500} className="field-input resize-y" aria-describedby="address-help" />
                  <p id="address-help" className="mt-2 text-sm text-[#a8b3c5]">Include your street or neighbourhood, city and country.</p>
                </div>
              </fieldset>
              <button disabled={pending} className="primary-button w-full">
                {pending ? "Saving…" : "Continue"}
              </button>
            </form>
          </>
        )}
        {step === "consent" && (
          <>
            <p className="section-label mb-2">Your control</p>
            <h1 className="text-3xl font-semibold tracking-[-0.03em]">Your privacy and consent</h1>
            <p className="my-6 rounded-2xl border border-[#2b3950] bg-[#121b2a] p-5 text-sm leading-7 text-[#b8c4d6]">
              {state?.consent_text}
            </p>
            <form method="post" onSubmit={consent}>
              <label className="flex min-h-11 items-start gap-3 rounded-xl border border-[#34435a] p-4 text-sm leading-6 transition hover:bg-[#182131]">
                <input
                  type="checkbox"
                  required
                  className="mt-1 size-5 shrink-0 accent-[#4f8cff]"
                />
                I have read the privacy notice and consent to the collection and
                use of my details and facial video.
              </label>
              <button disabled={pending} className="primary-button mt-5 w-full">
                {pending ? "Saving consent…" : "Agree and continue"}
              </button>
            </form>
          </>
        )}
        {step === "instructions" && (
          <>
            <p className="section-label mb-2">Recording guide</p>
            <h1 className="text-3xl font-semibold tracking-[-0.03em]">Before you record</h1>
            <p className="my-4 text-sm text-[#a8b3c5]">
              A few simple steps for a clear recording.
            </p>
            <ol className="mt-6 grid gap-3 text-sm leading-6 text-[#b8c4d6] sm:grid-cols-2">
              {[
                "Find good lighting, with the light in front of you.",
                "Keep your whole face visible and remove sunglasses or face coverings.",
                "Make sure only your face is in the frame.",
                "Hold your phone steady and look directly at the front camera.",
                "Follow the 18-second guided prompts: close and open your eyes, open and close your mouth, and turn your head then face forward. The order changes each time.",
                "Recording quality is checked after submission. You will receive retake instructions if needed; your operator reviews accepted videos.",
                "If your browser asks, allow camera access. No microphone access is needed.",
              ].map((text, i) => (
                <li key={text} className={`flex gap-3 rounded-xl border border-[#2b3950] bg-[#121b2a] p-4 ${i === 4 ? "sm:col-span-2" : ""}`}>
                  <span className="grid size-7 shrink-0 place-items-center rounded-full bg-[#172a4d] text-xs font-bold text-[#8cb5ff]">
                    {i + 1}
                  </span>
                  {text}
                </li>
              ))}
            </ol>
            <button
              onClick={() => {
                setError("");
                setStep("camera");
              }}
              className="primary-button mt-7 w-full"
            >
              Continue to camera
            </button>
          </>
        )}
        {step === "camera" && state && (
          <CameraRecorder
            token={token}
            maxSeconds={state.max_video_seconds}
            maxBytes={state.max_upload_bytes}
            onSubmitted={() => {
              setError("");
              setStep("success");
            }}
            onLinkError={linkError}
          />
        )}
        {error && (
          <p
            role="alert"
            className="mt-5 rounded-xl border border-[#713744] bg-[#321923] p-4 text-sm text-[#ffabbc]"
          >
            {error}
          </p>
        )}
      </div>
      </div>
      <p className="my-6 text-center text-xs leading-5 text-[#7f8da2]">
        Visa Selfie · Private registration
        <br />
        Need help? Contact the operator who sent you this link.
      </p>
    </main>
  );
}
