import Link from "next/link";
import { serverApi } from "@/lib/server-api";
import type { Overview, ProcessList, Activity } from "@/lib/types";
import { DateText, ProcessTable, readable } from "@/components/process-ui";

const cardStyles = [
  ["bg-[#172a4d] text-[#79a8ff]", "◎"],
  ["bg-[#3b2814] text-[#f5bd73]", "◷"],
  ["bg-[#271f48] text-[#b8a4ff]", "✓"],
  ["bg-[#31202c] text-[#f09ab8]", "⌛"],
];

export default async function DashboardPage() {
  const [stats, clients, activity] = await Promise.all([
    serverApi<Overview>("/admin/processes/summary"),
    serverApi<ProcessList>("/admin/processes?page_size=5"),
    serverApi<Activity[]>("/admin/activity"),
  ]);
  const cards = [
    ["Total clients", stats.total_clients],
    ["Pending registration", stats.pending_registration],
    ["Submitted videos", stats.submitted_videos],
    ["Expired links", stats.expired_links],
  ];
  return (
    <>
      <section className="relative mb-6 overflow-hidden rounded-[1.75rem] border border-[#31466b] bg-[linear-gradient(135deg,#111b2d_0%,#16233b_55%,#231942_100%)] px-5 py-7 text-white shadow-[0_22px_55px_rgba(0,0,0,0.3)] sm:px-8 sm:py-9">
        <div aria-hidden="true" className="absolute -right-20 -top-28 size-72 rounded-full border border-white/8" />
        <div aria-hidden="true" className="absolute -right-8 -top-14 size-48 rounded-full border border-white/8" />
        <div className="relative flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="mb-3 text-xs font-bold tracking-[0.15em] text-[#8cb5ff] uppercase">Your workspace</p>
            <h1 className="text-3xl font-semibold tracking-[-0.035em] sm:text-4xl">Overview</h1>
            <p className="mt-3 max-w-xl text-sm leading-6 text-white/65">Manage registrations, monitor applicant progress, and review submitted verification videos.</p>
          </div>
          <Link href="/dashboard/clients/new" className="primary-button shrink-0">+ Create client</Link>
        </div>
      </section>

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {cards.map(([label, value], index) => (
          <div key={label} className="surface-card min-w-0 p-4 sm:p-5">
            <div className={`mb-5 grid size-9 place-items-center rounded-xl text-lg ${cardStyles[index][0]}`} aria-hidden="true">{cardStyles[index][1]}</div>
            <p className="text-2xl font-semibold tracking-tight text-[#f8fafc] sm:text-3xl">{value}</p>
            <p className="mt-1 text-xs leading-5 text-[#a8b3c5]">{label}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.55fr)_minmax(18rem,0.75fr)]">
        <section className="surface-card min-w-0 overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-x-3 border-b border-[#273449] px-4 py-4 sm:px-6">
            <div><p className="section-label mb-1">Clients</p><h2 className="font-semibold text-[#f8fafc]">Recently updated</h2></div>
            <Link href="/dashboard/clients" className="touch-target shrink-0 rounded-lg px-2 text-sm font-bold text-[#8cb5ff] hover:bg-[#182641]">View all →</Link>
          </div>
          <ProcessTable processes={clients.items} />
        </section>
        <section className="surface-card min-w-0 overflow-hidden">
          <div className="border-b border-[#273449] px-5 py-4"><p className="section-label mb-1">Timeline</p><h2 className="font-semibold text-[#f8fafc]">Recent activity</h2></div>
          {activity.length ? (
            <ul className="max-h-[31rem] divide-y divide-[#273449] overflow-y-auto px-5">
              {activity.map((event) => (
                <li key={event.id} className="relative py-4 pl-6 before:absolute before:left-0 before:top-[1.35rem] before:size-2 before:rounded-full before:bg-[#8b5cf6]">
                  <p className="text-sm font-medium text-[#d9e2f1]">{readable(event.action)}</p>
                  <p className="mt-1 text-xs leading-5 text-[#8e9db2]"><DateText value={event.created_at} /></p>
                </li>
              ))}
            </ul>
          ) : (
            <div className="p-8 text-center"><div className="mx-auto mb-3 grid size-10 place-items-center rounded-full bg-[#172a4d] text-[#79a8ff]">◷</div><p className="text-sm text-[#a8b3c5]">Activity will appear here as applicants progress.</p></div>
          )}
        </section>
      </div>
    </>
  );
}
