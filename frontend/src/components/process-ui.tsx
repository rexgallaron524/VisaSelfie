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
    ? "bg-[#172a4d] text-[#8cb5ff] ring-[#294a7a]"
    : value === "expired"
      ? "bg-[#3b2814] text-[#f5bd73] ring-[#68451d]"
      : value === "recording_started"
        ? "bg-[#271f48] text-[#b8a4ff] ring-[#4d3f7c]"
        : "bg-[#1b2535] text-[#a8b3c5] ring-[#303e54]";
  return (
    <span
      className={`inline-block max-w-full rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset ${color}`}
    >
      {readable(value)}
    </span>
  );
}
export function ProcessTable({ processes }: { processes: ClientProcess[] }) {
  return (
    <div className="@container min-w-0">
      <ul aria-label="Client processes" className="divide-y divide-[#273449] @min-[36rem]:hidden">
        {processes.map((p) => (
          <li key={p.id} className="space-y-2 p-4 transition hover:bg-[#151f2e]">
            <Link href={`/dashboard/clients/${p.id}`} className="flex min-h-11 items-center font-semibold text-[#8cb5ff] underline-offset-4 hover:underline">
              {p.full_name}
            </Link>
            <p className="text-sm text-[#a8b3c5]">{p.phone_number}</p>
            <Status value={p.status} />
            <p className="text-xs leading-5 text-[#8e9db2]">
              Updated <DateText value={p.updated_at} />
            </p>
          </li>
        ))}
      </ul>
      <div className="hidden @min-[36rem]:block">
      <table className="w-full table-fixed text-left text-sm">
        <thead className="border-b border-[#273449] bg-[#151e2c] text-xs font-semibold text-[#a8b3c5]">
          <tr>
            <th scope="col" className="w-[44%] p-4">Client</th>
            <th scope="col" className="w-[28%] p-4">Status</th>
            <th scope="col" className="w-[28%] p-4">Last updated</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#273449]">
          {processes.map((p) => (
            <tr key={p.id} className="transition hover:bg-[#151f2e]">
              <td className="p-4">
                <Link
                  href={`/dashboard/clients/${p.id}`}
                  className="flex min-h-11 items-center font-semibold text-[#8cb5ff] underline-offset-4 hover:underline"
                >
                  {p.full_name}
                </Link>
                <p className="mt-1 text-xs text-[#8e9db2]">{p.phone_number}</p>
              </td>
              <td className="p-4">
                <Status value={p.status} />
              </td>
              <td className="p-4 text-xs leading-5 text-[#8e9db2]">
                <DateText value={p.updated_at} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
      {!processes.length && (
        <div className="px-6 py-12 text-center"><div className="mx-auto mb-3 grid size-11 place-items-center rounded-full bg-[#172a4d] text-xl text-[#79a8ff]">◎</div><p className="font-semibold text-[#e8eef8]">No client processes found.</p><p className="mt-1 text-sm text-[#a8b3c5]">Try changing the filters or create a new client.</p></div>
      )}
    </div>
  );
}
