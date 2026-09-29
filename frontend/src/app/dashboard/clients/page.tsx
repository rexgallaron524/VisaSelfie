import Link from "next/link";
import { ProcessTable, statuses, readable } from "@/components/process-ui";
import { serverApi } from "@/lib/server-api";
import type { ProcessList } from "@/lib/types";

export default async function ClientsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; status?: string; page?: string }>;
}) {
  const params = await searchParams;
  const page = Math.max(1, Number.parseInt(params.page ?? "1") || 1);
  const query = new URLSearchParams({
    q: (params.q ?? "").slice(0, 200),
    status: params.status ?? "",
    page: String(page),
  });
  const data = await serverApi<ProcessList>(`/admin/processes?${query}`);
  const pageUrl = (next: number) => {
    const p = new URLSearchParams(query);
    p.set("page", String(next));
    return `/dashboard/clients?${p}`;
  };
  return (
    <>
      <div className="mb-8 flex flex-wrap justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold">Clients</h1>
          <p className="mt-2 text-sm text-slate-500">
            {data.total} matching processes
          </p>
        </div>
        <Link href="/dashboard/clients/new" className="primary-button">
          + Create client
        </Link>
      </div>
      <form className="mb-5 flex flex-wrap items-end gap-3">
        <div className="min-w-52 flex-1">
          <label htmlFor="q" className="field-label">
            Search by name
          </label>
          <input
            id="q"
            name="q"
            defaultValue={params.q}
            maxLength={200}
            className="field-input"
          />
        </div>
        <div>
          <label htmlFor="status" className="field-label">
            Status
          </label>
          <select
            id="status"
            name="status"
            defaultValue={params.status}
            className="field-input"
          >
            <option value="">All statuses</option>
            {statuses.map((s) => (
              <option key={s} value={s}>
                {readable(s)}
              </option>
            ))}
          </select>
        </div>
        <button className="primary-button">Filter</button>
      </form>
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <ProcessTable processes={data.items} />
      </div>
      <div className="mt-5 flex items-center justify-between text-sm">
        {page > 1 ? (
          <Link href={pageUrl(page - 1)} className="text-teal-700">
            ← Previous
          </Link>
        ) : (
          <span />
        )}
        <span>Page {page}</span>
        {page * data.page_size < data.total ? (
          <Link href={pageUrl(page + 1)} className="text-teal-700">
            Next →
          </Link>
        ) : (
          <span />
        )}
      </div>
    </>
  );
}
