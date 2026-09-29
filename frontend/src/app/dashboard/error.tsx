"use client";

export default function DashboardError({ reset }: { reset: () => void }) {
  return (
    <main className="grid min-h-dvh place-items-center px-6">
      <div className="max-w-md rounded-2xl border border-slate-200 bg-white p-8">
        <h1 className="text-xl font-semibold">
          We couldn’t load your workspace.
        </h1>
        <p className="my-4 text-sm leading-6 text-slate-500">
          The administration service may be temporarily unavailable. Please try
          again.
        </p>
        <button onClick={reset} className="primary-button">
          Try again
        </button>
      </div>
    </main>
  );
}
