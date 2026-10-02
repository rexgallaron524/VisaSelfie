import Link from "next/link";

export function Brand({ light = false }: { light?: boolean }) {
  return (
    <Link href="/" aria-label="Visa Selfie home" className="inline-flex min-h-11 shrink-0 items-center gap-3">
      <span className={`grid size-10 place-items-center rounded-[13px] ${light ? "bg-white/10 text-white ring-1 ring-white/10" : "bg-[#4f8cff] text-white shadow-[0_8px_22px_rgba(79,140,255,0.28)]"}`}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="size-6" aria-hidden="true">
          <path d="M8 3H5a2 2 0 0 0-2 2v3m13-5h3a2 2 0 0 1 2 2v3M3 16v3a2 2 0 0 0 2 2h3m8 0h3a2 2 0 0 0 2-2v-3" />
          <circle cx="12" cy="9" r="3" /><path d="M6.5 18a5.5 5.5 0 0 1 11 0" />
        </svg>
      </span>
      <span className={`text-[1.18rem] font-bold tracking-[-0.025em] ${light ? "text-white" : "text-[#f8fafc]"}`}>Visa Selfie<span className={light ? "text-[#a78bfa]" : "text-[#79a8ff]"}>.</span></span>
    </Link>
  );
}
