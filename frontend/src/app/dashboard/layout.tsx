import Link from "next/link";
import { Brand } from "@/components/brand";
import { LogoutButton } from "@/components/logout-button";
import { requireAdmin } from "@/lib/server-api";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const admin = await requireAdmin();
  return (
    <div className="min-h-dvh bg-[#080b12] lg:grid lg:grid-cols-[16.5rem_minmax(0,1fr)]">
      <aside className="hidden min-h-dvh flex-col border-r border-[#273449] bg-[#0b101a] px-5 py-6 text-white lg:sticky lg:top-0 lg:flex lg:h-dvh">
        <Brand light />
        <p className="mt-9 px-3 text-[0.68rem] font-bold tracking-[0.16em] text-white/40 uppercase">Workspace</p>
        <nav aria-label="Main navigation" className="mt-3 space-y-1.5 text-sm">
          <Link href="/dashboard" className="touch-target w-full justify-start gap-3 rounded-xl px-3.5 font-semibold text-white/75 transition hover:bg-white/10 hover:text-white"><span aria-hidden="true" className="grid size-8 place-items-center rounded-lg bg-white/8">⌂</span> Overview</Link>
          <Link href="/dashboard/clients" className="touch-target w-full justify-start gap-3 rounded-xl px-3.5 font-semibold text-white/75 transition hover:bg-white/10 hover:text-white"><span aria-hidden="true" className="grid size-8 place-items-center rounded-lg bg-white/8">◎</span> Clients</Link>
        </nav>
        <div className="mt-auto rounded-2xl border border-[#293750] bg-[#111827] p-4">
          <div className="mb-3 flex items-center gap-2 text-xs font-bold text-[#8cb5ff]"><span className="size-2 rounded-full bg-[#8b5cf6] shadow-[0_0_0_4px_rgba(139,92,246,0.14)]" /> Secure workspace</div>
          <p className="truncate text-xs text-white/55" title={admin.email}>{admin.email}</p>
          <div className="mt-2"><LogoutButton /></div>
        </div>
      </aside>
      <div className="min-w-0">
        <header className="border-b border-[#273449] bg-[#0b101a]/95 backdrop-blur lg:hidden">
          <div className="page-shell flex items-center justify-between gap-3 py-3"><Brand /><div className="rounded-xl bg-[#182131]"><LogoutButton /></div></div>
          <nav aria-label="Main navigation" className="page-shell flex gap-1 border-t border-[#1e293b] pb-2 pt-1 text-sm">
            <Link href="/dashboard" className="touch-target flex-1 rounded-lg px-4 font-semibold text-[#c5d0e2] hover:bg-[#182131]">Overview</Link>
            <Link href="/dashboard/clients" className="touch-target flex-1 rounded-lg px-4 font-semibold text-[#c5d0e2] hover:bg-[#182131]">Clients</Link>
          </nav>
        </header>
        <main className="page-shell mx-auto max-w-[90rem] py-6 sm:py-9 lg:px-10 xl:px-12">{children}</main>
      </div>
    </div>
  );
}
