import type { Metadata } from "next";
import { Brand } from "@/components/brand";
import { LoginForm } from "@/components/login-form";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  return (
    <main className="grid min-h-dvh lg:grid-cols-2">
      <section className="relative hidden flex-col justify-between overflow-hidden bg-[#103e3e] p-12 text-white lg:flex xl:p-16">
        <Brand light />
        <div aria-hidden="true" className="pointer-events-none absolute -right-52 top-20 size-[600px] rounded-full border border-white/10" />
        <div aria-hidden="true" className="pointer-events-none absolute -right-36 top-36 size-[470px] rounded-full border border-white/10" />
        <div className="relative my-16 max-w-lg">
          <span className="mb-8 inline-flex items-center gap-2 rounded-full border border-teal-300/25 bg-teal-300/5 px-3 py-1.5 text-xs tracking-wide text-teal-100"><span className="size-1.5 rounded-full bg-teal-300" /> YOUR VERIFICATION WORKSPACE</span>
          <h1 className="text-5xl leading-[1.12] font-medium tracking-tight xl:text-6xl">A clear path.<br />A personal touch.</h1>
          <p className="mt-6 max-w-sm text-lg leading-8 text-teal-100/75">One private workspace for your team’s visa verification process.</p>
          <div className="mt-12 flex items-center gap-4 border-t border-white/15 pt-7">
            <span aria-hidden="true" className="grid size-11 place-items-center rounded-full bg-white/10 text-xl">✓</span>
            <p className="text-sm leading-6 text-teal-100/80">Built around privacy.<br /><span className="text-white">Managed by your team.</span></p>
          </div>
        </div>
        <p className="text-xs text-teal-100/50">Visa Selfie · Administration</p>
      </section>
      <section className="flex flex-col bg-white px-6 py-8 sm:px-12 lg:px-16">
        <div className="lg:hidden"><Brand /></div>
        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-16">
          <p className="mb-3 text-xs font-semibold tracking-[0.18em] text-teal-700">ADMIN PORTAL</p>
          <h2 className="text-3xl font-semibold tracking-tight text-slate-900">Welcome back.</h2>
          <p className="mt-3 text-sm leading-6 text-slate-500">Sign in to access your Visa Selfie workspace.</p>
          <LoginForm />
        </div>
        <p className="text-center text-xs text-slate-400">Private access · Secure sessions</p>
      </section>
    </main>
  );
}
