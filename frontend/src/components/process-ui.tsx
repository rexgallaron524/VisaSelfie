import Link from "next/link";
import type { ClientProcess } from "@/lib/types";

export const statuses = [
  "created",
  "link_generated",
  "opened",
  "registered",
  "recording_started",
  "submitted",
  "reviewed",
  "deleted",
  "expired",
];
export function readable(value: string) {
  return value.replaceAll(/[._]/g, " ").replace(/^./, (c) => c.toUpperCase());
}
export function DateText({ value }: { value: string | null }) {
  if (!value) return <span>—</span>;
  return (
    <time dateTime={value}>
      {new Intl.DateTimeFormat("en-GB", {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: "UTC",
      }).format(new Date(value))}{" "}
      UTC
    </time>
  );
}
export function Status({ value }: { value: string }) {
  const color = ["submitted", "reviewed"].includes(value)
    ? "bg-teal-50 text-teal-800"
    : value === "expired"
      ? "bg-amber-50 text-amber-800"
      : "bg-slate-100 text-slate-600";
  return (
    <span
      className={`inline-block max-w-full rounded-full px-3 py-1 text-xs font-medium ${color}`}
    >
      {readable(value)}
    </span>
  );
}
export function ProcessTable({ processes }: { processes: ClientProcess[] }) {
  return (
    <div className="@container min-w-0">
      <ul aria-label="Client processes" className="divide-y divide-slate-100 @min-[36rem]:hidden">
        {processes.map((p) => (
          <li key={p.id} className="space-y-2 p-4">
            <Link href={`/dashboard/clients/${p.id}`} className="flex min-h-11 items-center font-semibold text-teal-800 underline-offset-4 hover:underline">
              {p.full_name}
            </Link>
            <p className="text-sm text-slate-500">{p.phone_number}</p>
            <Status value={p.status} />
            <p className="text-xs leading-5 text-slate-500">
              Updated <DateText value={p.updated_at} />
            </p>
          </li>
        ))}
      </ul>
      <div className="hidden @min-[36rem]:block">
      <table className="w-full table-fixed text-left text-sm">
        <thead className="border-b border-slate-100 bg-slate-50 text-xs text-slate-500">
          <tr>
            <th scope="col" className="w-[44%] p-4">Client</th>
            <th scope="col" className="w-[28%] p-4">Status</th>
            <th scope="col" className="w-[28%] p-4">Last updated</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {processes.map((p) => (
            <tr key={p.id}>
              <td className="p-4">
                <Link
                  href={`/dashboard/clients/${p.id}`}
                  className="flex min-h-11 items-center font-semibold text-teal-800 underline-offset-4 hover:underline"
                >
                  {p.full_name}
                </Link>
                <p className="mt-1 text-xs text-slate-500">{p.phone_number}</p>
              </td>
              <td className="p-4">
                <Status value={p.status} />
              </td>
              <td className="p-4 text-xs text-slate-500">
                <DateText value={p.updated_at} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
      {!processes.length && (
        <p className="p-8 text-center text-sm text-slate-500">
          No client processes found.
        </p>
      )}
    </div>
  );
}
