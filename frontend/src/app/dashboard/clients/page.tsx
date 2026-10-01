import Link from "next/link";
import { redirect } from "next/navigation";
import { ClientPagination } from "@/components/client-pagination";
import { BackToTop } from "@/components/back-to-top";
import { ProcessTable, statuses, readable } from "@/components/process-ui";
import { serverApi } from "@/lib/server-api";
import type { ProcessList } from "@/lib/types";

export default async function ClientsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; status?: string; page?: string; page_size?: string }>;
}) {
  const params = await searchParams;
  const requestedPage = Number(params.page ?? "1");
  const page = Number.isSafeInteger(requestedPage) && requestedPage >= 1 && requestedPage <= 2147483647 ? requestedPage : 1;
  const requestedSize = Number(params.page_size);
  const pageSize = [10, 30, 50].includes(requestedSize) ? requestedSize : 10;
  const query = new URLSearchParams({
    q: (params.q ?? "").slice(0, 200),
    status: params.status ?? "",
    page: String(page),
    page_size: String(pageSize),
  });
  const data = await serverApi<ProcessList>(`/admin/processes?${query}`);
  const lastPage = Math.max(1, Math.ceil(data.total / pageSize));
  if (page > lastPage) {
    query.set("page", String(lastPage));
    redirect(`/dashboard/clients?${query}`);
  }
  return (
    <>
      <div className="mb-6 flex flex-col gap-4 sm:mb-8 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 id="clients-top" tabIndex={-1} className="text-3xl font-semibold">Clients</h1>
          <p className="mt-2 text-sm text-slate-500">
            {data.total} matching processes
          </p>
        </div>
        <Link href="/dashboard/clients/new" className="primary-button">
          + Create client
        </Link>
      </div>
      <form className="mb-5 grid items-end gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:grid-cols-[minmax(0,1fr)_minmax(0,16rem)_auto]">
        <input type="hidden" name="page_size" value={pageSize} />
        <div className="min-w-0">
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
        <div className="min-w-0">
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
        <button className="primary-button sm:col-span-2 lg:col-span-1">Filter</button>
      </form>
      <section aria-label="Client list" className="min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <ClientPagination position="top" page={page} pageSize={pageSize} total={data.total} query={query.toString()} />
        <ProcessTable processes={data.items} />
        <ClientPagination position="bottom" page={page} pageSize={pageSize} total={data.total} query={query.toString()} />
      </section>
      <BackToTop targetId="clients-top" />
    </>
  );
}
