"use client";

import { useEffect, useRef } from "react";

interface ConfirmationModalProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  pending?: boolean;
  destructive?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}

export function ConfirmationModal({
  open,
  title,
  description,
  confirmLabel,
  pending = false,
  destructive = false,
  onConfirm,
  onClose,
}: ConfirmationModalProps) {
  const dialog = useRef<HTMLDialogElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    returnFocus.current = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialog.current?.showModal();
    return () => {
      document.body.style.overflow = previousOverflow;
      queueMicrotask(() => returnFocus.current?.focus());
    };
  }, [open]);

  if (!open) return null;

  function close() {
    if (!pending) dialog.current?.close();
  }

  return (
    <dialog
      ref={dialog}
      role="alertdialog"
      aria-labelledby="confirmation-title"
      aria-describedby="confirmation-description"
      aria-busy={pending}
      onCancel={(event) => {
        event.preventDefault();
        close();
      }}
      onClose={onClose}
      onClick={(event) => {
        if (event.target === event.currentTarget) close();
      }}
      className="m-auto w-[calc(100%-2rem)] max-w-md rounded-2xl border border-[#34435a] bg-[#111827] p-0 text-[#f8fafc] shadow-[0_28px_90px_rgba(0,0,0,0.65)] backdrop:bg-[#02040a]/80 backdrop:backdrop-blur-sm"
    >
      <div className="p-5 sm:p-6">
        <div
          aria-hidden="true"
          className={`mb-5 grid size-11 place-items-center rounded-xl text-xl ${
            destructive
              ? "bg-[#321923] text-[#ff8fa6]"
              : "bg-[#172a4d] text-[#8cb5ff]"
          }`}
        >
          {destructive ? "!" : "?"}
        </div>
        <h2 id="confirmation-title" className="text-xl font-semibold tracking-[-0.02em]">
          {title}
        </h2>
        <p id="confirmation-description" className="mt-3 text-sm leading-6 text-[#a8b3c5]">
          {description}
        </p>
        <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <button type="button" disabled={pending} onClick={close} className="secondary-button">
            Cancel
          </button>
          <button
            type="button"
            disabled={pending}
            onClick={onConfirm}
            className={
              destructive
                ? "inline-flex min-h-11 items-center justify-center rounded-xl bg-[#d4425f] px-5 py-3 text-sm font-bold text-white transition hover:bg-[#bd3651] disabled:cursor-wait disabled:opacity-60"
                : "primary-button"
            }
          >
            {pending ? "Working…" : confirmLabel}
          </button>
        </div>
      </div>
    </dialog>
  );
}
