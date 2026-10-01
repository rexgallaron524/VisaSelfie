"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTransition } from "react";

interface Props {
  position: "top" | "bottom";
  page: number;
  pageSize: number;
  total: number;
  query: string;
}

export function ClientPagination({ position, page, pageSize, total, query }: Props) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const pages = Math.max(1, Math.ceil(total / pageSize));
  function url(next: number, size = pageSize) {
    const params = new URLSearchParams(query);
    params.set("page", String(next));
    params.set("page_size", String(size));
    return `/dashboard/clients?${params}`;
  }
  const numbers = [...new Set([1, page - 1, page, page + 1, pages])]
    .filter(n => n >= 1 && n <= pages).sort((a, b) => a - b);
  const items: (number | string)[] = [];
  numbers.forEach((n, index) => {
    if (index && n > numbers[index - 1] + 1) items.push(`gap-${n}`);
    items.push(n);
  });
  const button =
    "touch-target size-11 shrink-0 rounded-lg border border-slate-300 text-sm text-teal-800 hover:bg-teal-50 sm:w-auto sm:px-3";
  const start = total ? (page - 1) * pageSize + 1 : 0;
  const end = Math.min(page * pageSize, total);
  return (
    <nav
      aria-label={`Client pagination ${position}`}
      aria-busy={pending}
      className={`flex min-w-0 items-center gap-2 overflow-x-auto px-3 py-2.5 sm:px-4 ${position === "top" ? "border-b border-slate-200" : "border-t border-slate-200"}`}
    >
      <p role="status" className="shrink-0 text-xs text-slate-600 sm:text-sm">
        <span className="sm:hidden">{total ? `${start}–${end} / ${total}` : "0 clients"}</span>
        <span className="hidden sm:inline">
          {total ? `Showing ${start}–${end} of ${total} clients` : "No clients to display"}
        </span>
      </p>
      <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
        <label htmlFor={`page-size-${position}`} className="sr-only sm:not-sr-only sm:text-sm sm:text-slate-600">
          Clients per page
        </label>
        <select
          id={`page-size-${position}`}
          aria-label="Clients per page"
          value={pageSize}
          disabled={pending}
          onChange={e => {
            const size = Number(e.target.value);
            startTransition(() => router.push(url(1, size)));
          }}
          className="field-input min-h-11 w-[3.75rem] shrink-0 px-2 py-2 text-base sm:w-20"
        >
          {[10, 30, 50].map(size => <option key={size} value={size}>{size}</option>)}
        </select>
      </div>
      <div className="ml-auto flex shrink-0 items-center gap-1.5 sm:gap-2">
        {page > 1 ? (
          <Link href={url(page - 1)} className={button} aria-label="Previous page">
            <span aria-hidden="true" className="sm:hidden">‹</span><span className="hidden sm:inline">Previous</span>
          </Link>
        ) : (
          <span aria-disabled="true" className={`${button} opacity-40`}>
            <span aria-hidden="true" className="sm:hidden">‹</span><span className="hidden sm:inline">Previous</span>
          </span>
        )}
        {items.map(item => typeof item === "number" ? (
          <Link
            key={item}
            href={url(item)}
            aria-label={`Page ${item}`}
            aria-current={item === page ? "page" : undefined}
            className={`${button} ${item === page ? "border-teal-800 bg-teal-50 font-semibold" : "hidden sm:inline-flex"}`}
          >
            {item}
          </Link>
        ) : <span key={item} aria-hidden="true" className="hidden px-1 sm:inline">…</span>)}
        {page < pages ? (
          <Link href={url(page + 1)} className={button} aria-label="Next page">
            <span aria-hidden="true" className="sm:hidden">›</span><span className="hidden sm:inline">Next</span>
          </Link>
        ) : (
          <span aria-disabled="true" className={`${button} opacity-40`}>
            <span aria-hidden="true" className="sm:hidden">›</span><span className="hidden sm:inline">Next</span>
          </span>
        )}
        <span className="hidden shrink-0 text-xs text-slate-500 lg:inline">Page {page} of {pages}</span>
      </div>
    </nav>
  );
}
