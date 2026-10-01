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
  return (
    <main className="mx-auto min-h-dvh max-w-xl px-5 py-7">
      <Brand />
      <div
        className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 sm:p-8"
        ref={heading}
        tabIndex={-1}
        style={{ outline: "none" }}
      >
        {stepIndex >= 0 && (
          <div className="mb-6">
            <p className="mb-3 text-xs font-semibold tracking-wider text-teal-700">
              STEP {stepIndex + 1} OF 4
            </p>
            <div className="flex gap-2" aria-hidden="true">
              {[0, 1, 2, 3].map((n) => (
                <span
                  key={n}
                  className={`h-1 flex-1 rounded-full ${n <= stepIndex ? "bg-teal-700" : "bg-slate-100"}`}
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
            <p className="mt-4 text-sm leading-7 text-slate-600">
              It may be incomplete or have been replaced. Please ask the
              operator who invited you for a new registration link.
            </p>
          </>
        )}
        {step === "expired" && (
          <>
            <h1 className="text-2xl font-semibold">Your link has expired</h1>
            <p className="mt-4 text-sm leading-7 text-slate-600">
              Registration links expire after 48 hours. Contact the operator who
              invited you to request a new link.
            </p>
          </>
        )}
        {step === "success" && (
          <>
            <div
              aria-hidden="true"
              className="mb-5 grid size-14 place-items-center rounded-full bg-teal-50 text-2xl text-teal-700"
            >
              ✓
            </div>
            <h1 className="text-2xl font-semibold">Recording submitted</h1>
            <p className="mt-4 text-sm leading-7 text-slate-600">
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
            <h1 className="text-2xl font-semibold">Your details</h1>
            <p className="mt-3 text-sm leading-6 text-slate-500">
              Enter your details exactly as they appear on your passport.
            </p>
            <form method="post" onSubmit={register} className="mt-6 space-y-5">
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
                  required
                  minLength={7}
                  maxLength={32}
                  className="field-input"
                />
              </div>
              <button disabled={pending} className="primary-button w-full">
                {pending ? "Saving…" : "Continue"}
              </button>
            </form>
          </>
        )}
        {step === "consent" && (
          <>
            <h1 className="text-2xl font-semibold">Your privacy and consent</h1>
            <p className="my-5 text-sm leading-7 text-slate-600">
              {state?.consent_text}
            </p>
            <form method="post" onSubmit={consent}>
              <label className="flex items-start gap-3 rounded-xl border border-slate-200 p-4 text-sm leading-6">
                <input
                  type="checkbox"
                  required
                  className="mt-1 size-4 shrink-0 accent-teal-700"
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
            <h1 className="text-2xl font-semibold">Before you record</h1>
            <p className="my-4 text-sm text-slate-500">
              A few simple steps for a clear recording.
            </p>
            <ol className="space-y-4 text-sm leading-6 text-slate-700">
              {[
                "Find good lighting, with the light in front of you.",
                "Keep your whole face visible and remove sunglasses or face coverings.",
                "Make sure only your face is in the frame.",
                "Hold your phone steady and look directly at the front camera.",
                "Follow the 18-second guided prompts: close and open your eyes, open and close your mouth, and turn your head then face forward. The order changes each time.",
                "Recording quality is checked after submission. You will receive retake instructions if needed; your operator reviews accepted videos.",
                "If your browser asks, allow camera access. No microphone access is needed.",
              ].map((text, i) => (
                <li key={text} className="flex gap-3">
                  <span className="grid size-6 shrink-0 place-items-center rounded-full bg-teal-50 text-xs text-teal-800">
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
            className="mt-5 rounded-xl bg-red-50 p-4 text-sm text-red-700"
          >
            {error}
          </p>
        )}
      </div>
      <p className="my-6 text-center text-xs leading-5 text-slate-400">
        Visa Selfie · Private registration
        <br />
        Need help? Contact the operator who sent you this link.
      </p>
    </main>
  );
}
