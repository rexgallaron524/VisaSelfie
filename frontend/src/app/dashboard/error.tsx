"use client";

export default function DashboardError({ reset }: { reset: () => void }) {
  return (
    <div className="grid min-h-[50dvh] place-items-center">
      <div className="surface-card min-w-0 max-w-md p-5 sm:p-8">
        <h1 className="text-xl font-semibold">
          We couldn’t load your workspace.
        </h1>
        <p className="my-4 text-sm leading-6 text-[#a8b3c5]">
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
