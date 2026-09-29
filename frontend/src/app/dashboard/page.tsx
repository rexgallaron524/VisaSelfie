import Link from "next/link";
import { serverApi } from "@/lib/server-api";
import type { Overview, ProcessList, Activity } from "@/lib/types";
import { DateText, ProcessTable, readable } from "@/components/process-ui";

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
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="mb-2 text-xs font-semibold tracking-widest text-teal-700">
            YOUR WORKSPACE
          </p>
          <h1 className="text-3xl font-semibold">Overview</h1>
          <p className="mt-2 text-sm text-slate-500">
            Manage client registrations and review verification videos.
          </p>
        </div>
        <Link href="/dashboard/clients/new" className="primary-button">
          + Create client
        </Link>
      </div>
      <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {cards.map(([label, value]) => (
          <div
            key={label}
            className="rounded-2xl border border-slate-200 bg-white p-5"
          >
            <p className="text-xs text-slate-500">{label}</p>
            <p className="mt-3 text-3xl font-semibold">{value}</p>
          </div>
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <div className="flex items-center justify-between p-5">
            <h2 className="font-semibold">Recently updated clients</h2>
            <Link href="/dashboard/clients" className="text-sm text-teal-700">
              View all →
            </Link>
          </div>
          <ProcessTable processes={clients.items} />
        </section>
        <section className="rounded-2xl border border-slate-200 bg-white">
          <h2 className="border-b border-slate-100 p-5 font-semibold">
            Recent activity
          </h2>
          <ul className="max-h-96 divide-y divide-slate-100 overflow-y-auto">
            {activity.map((event) => (
              <li key={event.id} className="px-5 py-3">
                <p className="text-sm">{readable(event.action)}</p>
                <p className="mt-1 text-xs text-slate-500">
                  <DateText value={event.created_at} />
                </p>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </>
  );
}
