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
    <div className="min-h-dvh">
      <header className="border-b border-slate-200 bg-white">
        <div className="page-shell mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-3 gap-y-2 py-3 sm:gap-4 sm:py-5">
          <Brand />
          <nav aria-label="Main navigation" className="order-3 flex w-full items-center gap-2 border-t border-slate-100 pt-2 text-sm sm:order-none sm:w-auto sm:border-0 sm:pt-0">
            <Link href="/dashboard" className="touch-target flex-1 rounded-lg px-4 hover:bg-teal-50 hover:text-teal-700 sm:flex-none">
              Overview
            </Link>
            <Link href="/dashboard/clients" className="touch-target flex-1 rounded-lg px-4 hover:bg-teal-50 hover:text-teal-700 sm:flex-none">
              Clients
            </Link>
          </nav>
          <div className="flex min-w-0 items-center gap-3">
            <span className="hidden max-w-48 truncate text-xs text-slate-500 lg:block" title={admin.email}>
              {admin.email}
            </span>
            <LogoutButton />
          </div>
        </div>
      </header>
      <main className="page-shell mx-auto max-w-6xl py-6 sm:py-10">{children}</main>
    </div>
  );
}
