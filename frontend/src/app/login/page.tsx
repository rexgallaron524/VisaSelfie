import type { Metadata } from "next";
import { Brand } from "@/components/brand";
import { LoginForm } from "@/components/login-form";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  return (
    <main className="grid min-h-dvh bg-[#080b12] lg:grid-cols-[minmax(25rem,1.1fr)_minmax(25rem,0.9fr)]">
      <section className="relative hidden flex-col justify-between overflow-hidden border-r border-[#273449] bg-[#0b101a] p-12 text-white lg:flex xl:p-16">
        <Brand light />
        <div aria-hidden="true" className="pointer-events-none absolute -right-52 top-20 size-[600px] rounded-full border border-white/8" />
        <div aria-hidden="true" className="pointer-events-none absolute -right-36 top-36 size-[470px] rounded-full border border-white/8" />
        <div aria-hidden="true" className="pointer-events-none absolute bottom-[-9rem] left-[-6rem] size-72 rounded-full bg-[#4f8cff]/25 blur-3xl" />
        <div className="relative my-16 max-w-lg">
          <span className="mb-8 inline-flex items-center gap-2 rounded-full border border-[#4f8cff]/30 bg-[#4f8cff]/10 px-3 py-1.5 text-xs font-semibold tracking-wide text-[#a9c6ff]"><span className="size-1.5 rounded-full bg-[#8b5cf6]" /> YOUR VERIFICATION WORKSPACE</span>
          <h1 className="text-5xl leading-[1.08] font-semibold tracking-[-0.045em] xl:text-6xl">A clear path.<br /><span className="bg-gradient-to-r from-[#79a8ff] to-[#b69aff] bg-clip-text text-transparent">A personal touch.</span></h1>
          <p className="mt-6 max-w-md text-lg leading-8 text-white/65">One private workspace for managing applicant registrations and facial video reviews.</p>
          <div className="mt-12 grid max-w-md grid-cols-2 gap-3 border-t border-white/10 pt-7">
            <div className="rounded-2xl border border-[#2b3950] bg-[#111827] p-4"><span aria-hidden="true" className="mb-4 grid size-8 place-items-center rounded-lg bg-[#4f8cff]/15 text-[#8cb5ff]">✓</span><p className="text-sm font-semibold">Private links</p><p className="mt-1 text-xs leading-5 text-white/45">Unique access for every applicant.</p></div>
            <div className="rounded-2xl border border-[#2b3950] bg-[#111827] p-4"><span aria-hidden="true" className="mb-4 grid size-8 place-items-center rounded-lg bg-[#8b5cf6]/15 text-[#b8a4ff]">◷</span><p className="text-sm font-semibold">Clear progress</p><p className="mt-1 text-xs leading-5 text-white/45">A simple view of each case.</p></div>
          </div>
        </div>
        <p className="text-xs text-white/35">Visa Selfie · Administration</p>
      </section>
      <section className="page-shell flex min-w-0 flex-col bg-[radial-gradient(circle_at_top_right,#17203a_0%,#0b101a_45%,#080b12_100%)] py-6 sm:py-8 lg:px-16">
        <div className="lg:hidden"><Brand /></div>
        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-8 sm:py-12 lg:py-16">
          <p className="section-label mb-3">Admin portal</p>
          <h2 className="text-3xl font-semibold tracking-[-0.035em] text-[#f8fafc] sm:text-4xl">Welcome back.</h2>
          <p className="mt-3 text-sm leading-6 text-[#a8b3c5]">Sign in to access your Visa Selfie workspace.</p>
          <LoginForm />
        </div>
        <p className="text-center text-xs text-[#7f8da2]">Private access · Secure sessions</p>
      </section>
    </main>
  );
}
