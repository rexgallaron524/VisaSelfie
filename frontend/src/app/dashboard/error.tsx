"use client";

export default function DashboardError({ reset }: { reset: () => void }) {
  return (
    <div className="grid min-h-[50dvh] place-items-center">
      <div className="min-w-0 max-w-md rounded-2xl border border-slate-200 bg-white p-4 sm:p-8">
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
    </div>
  );
}
