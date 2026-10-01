import Link from "next/link";

export function Brand({ light = false }: { light?: boolean }) {
  return (
    <Link href="/" aria-label="Visa Selfie home" className="inline-flex min-h-11 shrink-0 items-center gap-2 sm:gap-3">
      <span className={`grid size-10 place-items-center rounded-xl ${light ? "bg-white/10 text-white" : "bg-teal-800 text-white"}`}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="size-6" aria-hidden="true">
          <path d="M8 3H5a2 2 0 0 0-2 2v3m13-5h3a2 2 0 0 1 2 2v3M3 16v3a2 2 0 0 0 2 2h3m8 0h3a2 2 0 0 0 2-2v-3" />
          <circle cx="12" cy="9" r="3" /><path d="M6.5 18a5.5 5.5 0 0 1 11 0" />
        </svg>
      </span>
      <span className={`text-xl font-semibold tracking-tight ${light ? "text-white" : "text-slate-900"}`}>Visa Selfie<span className="text-teal-500">.</span></span>
    </Link>
  );
}
