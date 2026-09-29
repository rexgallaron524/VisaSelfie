"use client";

import { useEffect, useRef, useState } from "react";
import { apiRequest, ApiError } from "@/lib/api";

interface Props {
  token: string;
  maxSeconds: number;
  maxBytes: number;
  onSubmitted: () => void;
  onLinkError: (status: number) => void;
}

export function CameraRecorder({
  token,
  maxSeconds,
  maxBytes,
  onSubmitted,
  onLinkError,
}: Props) {
  const live = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const previewUrl = useRef<string | null>(null);
  const upload = useRef<XMLHttpRequest | null>(null);
  const mounted = useRef(true);
  const [stage, setStage] = useState<
    "idle" | "ready" | "recording" | "preview"
  >("idle");
  const [blob, setBlob] = useState<Blob | null>(null);
  const [url, setUrl] = useState("");
  const [seconds, setSeconds] = useState(0);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState<number | null>(null);

  function releaseCamera() {
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = null;
    if (live.current) live.current.srcObject = null;
  }

  useEffect(() => {
    mounted.current = true;
    const stopOnHide = () => {
      if (document.hidden && recorder.current?.state === "recording")
        recorder.current.stop();
    };
    document.addEventListener("visibilitychange", stopOnHide);
    return () => {
      mounted.current = false;
      document.removeEventListener("visibilitychange", stopOnHide);
      if (timer.current) clearInterval(timer.current);
      if (recorder.current) {
        recorder.current.onstop = null;
        recorder.current.onerror = null;
        recorder.current.ondataavailable = null;
        if (recorder.current.state !== "inactive") recorder.current.stop();
      }
      stream.current?.getTracks().forEach((track) => track.stop());
      if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
      upload.current?.abort();
    };
  }, []);

  async function enableCamera() {
    setPending(true);
    setError("");
    setBlob(null);
    setUrl("");
    setStage("idle");
    if (previewUrl.current) {
      URL.revokeObjectURL(previewUrl.current);
      previewUrl.current = null;
    }
    releaseCamera();
    try {
      if (!window.isSecureContext)
        throw new Error(
          "Open this link over HTTPS to use your camera. For local desktop testing, use localhost.",
        );
      if (
        !navigator.mediaDevices?.getUserMedia ||
        typeof MediaRecorder === "undefined"
      )
        throw new Error(
          "This browser cannot record video. Open the link in a recent Safari or Chrome browser.",
        );
      const media = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "user",
          width: { ideal: 640 },
          height: { ideal: 480 },
          frameRate: { ideal: 24, max: 30 },
        },
        audio: false,
      });
      if (!mounted.current) {
        media.getTracks().forEach((track) => track.stop());
        return;
      }
      stream.current = media;
      if (live.current) {
        live.current.srcObject = media;
        await live.current.play();
      }
      media.getVideoTracks()[0].onended = () => {
        if (recorder.current?.state === "recording") recorder.current.stop();
        else {
          releaseCamera();
          setStage("idle");
          setError("Your camera was disconnected. Please enable it again.");
        }
      };
      setStage("ready");
    } catch (e) {
      releaseCamera();
      const message =
        e instanceof DOMException && e.name === "NotAllowedError"
          ? "Camera permission was denied. Allow camera access in your browser settings, then try again. If you opened this in WhatsApp, open it in Safari or Chrome."
          : e instanceof Error
            ? e.message
            : "Unable to open your camera. Please try again.";
      if (mounted.current) setError(message);
    } finally {
      if (mounted.current) setPending(false);
    }
  }

  async function start() {
    if (!stream.current) return;
    setPending(true);
    setError("");
    setSeconds(0);
    try {
      await apiRequest<void>("/public/recording", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!mounted.current || !stream.current) return;
      const mime = [
        "video/webm;codecs=vp8",
        "video/webm;codecs=vp9",
        "video/mp4",
      ].find((type) => MediaRecorder.isTypeSupported(type));
      const mediaRecorder = new MediaRecorder(stream.current, {
        ...(mime ? { mimeType: mime } : {}),
        videoBitsPerSecond: 1500000,
      });
      recorder.current = mediaRecorder;
      const chunks: Blob[] = [];
      let bytes = 0;
      let failed = false;
      const started = performance.now();
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size) {
          chunks.push(event.data);
          bytes += event.data.size;
        }
        if (bytes > maxBytes && mediaRecorder.state === "recording")
          mediaRecorder.stop();
      };
      mediaRecorder.onerror = () => {
        failed = true;
        setError("Recording failed. Please enable the camera and try again.");
        if (mediaRecorder.state !== "inactive") mediaRecorder.stop();
      };
      mediaRecorder.onstop = () => {
        if (timer.current) clearInterval(timer.current);
        releaseCamera();
        if (!mounted.current) return;
        const elapsed = (performance.now() - started) / 1000;
        if (failed || elapsed < 3 || !bytes || bytes > maxBytes) {
          setStage("idle");
          setError(
            bytes > maxBytes
              ? "Recording is too large. Please try a shorter video."
              : "Please record at least 3 seconds and try again.",
          );
          return;
        }
        const video = new Blob(chunks, {
          type: mediaRecorder.mimeType || mime || "video/webm",
        });
        const objectUrl = URL.createObjectURL(video);
        previewUrl.current = objectUrl;
        setBlob(video);
        setUrl(objectUrl);
        setStage("preview");
      };
      mediaRecorder.start(250);
      setStage("recording");
      timer.current = setInterval(() => {
        const elapsed = (performance.now() - started) / 1000;
        setSeconds(Math.floor(elapsed));
        if (elapsed >= maxSeconds - 0.25 && mediaRecorder.state === "recording")
          mediaRecorder.stop();
      }, 200);
    } catch (e) {
      if (e instanceof ApiError && [404, 410].includes(e.status))
        onLinkError(e.status);
      else if (
        e instanceof ApiError &&
        e.status === 409 &&
        e.message.includes("already been submitted")
      )
        onSubmitted();
      else
        setError(e instanceof Error ? e.message : "Unable to start recording.");
    } finally {
      if (mounted.current) setPending(false);
    }
  }

  function submit() {
    if (!blob) return;
    setPending(true);
    setError("");
    setProgress(0);
    const xhr = new XMLHttpRequest();
    upload.current = xhr;
    xhr.open("POST", "/api/public/video");
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.setRequestHeader("Content-Type", blob.type);
    xhr.timeout = 180000;
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable)
        setProgress(Math.round((event.loaded / event.total) * 100));
    };
    const fail = (message: string) => {
      if (mounted.current) {
        setPending(false);
        setProgress(null);
        setError(message);
      }
    };
    xhr.onerror = () =>
      fail(
        "Upload interrupted. Your preview is still available; check your connection and retry.",
      );
    xhr.ontimeout = () =>
      fail("Upload timed out. Please retry your submission.");
    xhr.onload = () => {
      if (!mounted.current) return;
      let message = "Submission failed. Please retry.";
      try {
        message = JSON.parse(xhr.responseText).detail ?? message;
      } catch {
        /* Non-JSON proxy response. */
      }
      if (
        xhr.status === 201 ||
        (xhr.status === 409 && message.includes("already been submitted"))
      )
        onSubmitted();
      else if ([404, 410].includes(xhr.status)) onLinkError(xhr.status);
      else
        fail(
          xhr.status === 429
            ? "Too many attempts. Wait a minute and retry."
            : message,
        );
    };
    xhr.send(blob);
  }

  return (
    <div>
      <h2 className="text-2xl font-semibold">
        {stage === "preview"
          ? "Preview your recording"
          : "Record your facial video"}
      </h2>
      <p className="my-3 text-sm leading-6 text-slate-500">
        {stage === "preview"
          ? "Check that your face is clear and fully visible. Retake if needed, or confirm to submit."
          : `Look directly at the camera and keep your face in the frame. Record for 3–${maxSeconds} seconds. Audio is not recorded.`}
      </p>
      <div className="relative my-5 overflow-hidden rounded-2xl bg-slate-950">
        <video
          ref={live}
          muted
          autoPlay
          playsInline
          className={`aspect-[3/4] max-h-[420px] w-full -scale-x-100 object-contain ${stage === "preview" ? "hidden" : ""}`}
        />
        {stage === "preview" && (
          <video
            key={url}
            src={url}
            controls
            playsInline
            className="aspect-[3/4] max-h-[420px] w-full object-contain"
          />
        )}
        {stage === "idle" && (
          <p className="absolute inset-0 grid place-items-center px-6 text-center text-sm text-white/70">
            Your camera preview will appear here
          </p>
        )}
        {stage === "recording" && (
          <span
            role="status"
            className="absolute top-4 left-4 rounded-full bg-red-600 px-3 py-1 text-sm text-white"
          >
            ● {seconds}s / {maxSeconds}s
          </span>
        )}
      </div>
      {error && (
        <p
          role="alert"
          className="my-4 rounded-xl bg-red-50 p-4 text-sm text-red-800"
        >
          {error}
        </p>
      )}
      {progress !== null && (
        <div role="status" className="my-4 text-sm text-teal-800">
          <p>
            {progress === 100
              ? "Checking and saving your recording…"
              : `Uploading… ${progress}%`}
          </p>
          <progress value={progress} max={100} className="mt-2 w-full" />
          <p className="mt-1 text-xs">
            Keep this page open until you see confirmation.
          </p>
        </div>
      )}
      <div className="flex flex-wrap gap-3">
        {stage === "idle" && (
          <button
            disabled={pending}
            onClick={enableCamera}
            className="primary-button w-full"
          >
            {pending ? "Opening camera…" : "Enable camera"}
          </button>
        )}
        {stage === "ready" && (
          <button
            disabled={pending}
            onClick={start}
            className="primary-button w-full"
          >
            {pending ? "Preparing…" : "Start recording"}
          </button>
        )}
        {stage === "recording" && (
          <button
            disabled={seconds < 3}
            onClick={() => recorder.current?.stop()}
            className="primary-button w-full"
          >
            Stop recording{seconds < 3 ? " (minimum 3 seconds)" : ""}
          </button>
        )}
        {stage === "preview" && (
          <>
            <button
              disabled={pending}
              onClick={enableCamera}
              className="rounded-xl border border-slate-300 px-5 py-3 text-sm disabled:opacity-50"
            >
              Retake
            </button>
            <button
              disabled={pending}
              onClick={submit}
              className="primary-button flex-1"
            >
              {pending ? "Submitting…" : "Confirm and submit"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
