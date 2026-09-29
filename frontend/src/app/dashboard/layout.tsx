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
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-5">
          <Brand />
          <nav className="flex items-center gap-5 text-sm">
            <Link href="/dashboard" className="hover:text-teal-700">
              Overview
            </Link>
            <Link href="/dashboard/clients" className="hover:text-teal-700">
              Clients
            </Link>
          </nav>
          <div className="flex items-center gap-4">
            <span className="hidden text-xs text-slate-500 lg:block">
              {admin.email}
            </span>
            <LogoutButton />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
    </div>
  );
}
