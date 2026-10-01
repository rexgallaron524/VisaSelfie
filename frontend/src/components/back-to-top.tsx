"use client";

import { useEffect, useState } from "react";

export function BackToTop({ targetId }: { targetId: string }) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const update = () => setVisible(window.scrollY > 600);
    update();
    window.addEventListener("scroll", update, { passive: true });
    return () => window.removeEventListener("scroll", update);
  }, []);
  if (!visible) return null;
  return (
    <button type="button" aria-label="Back to top"
      onClick={() => {
        document.getElementById(targetId)?.focus({ preventScroll: true });
        window.scrollTo({ top: 0, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" });
      }}
      className="fixed right-[max(1rem,env(safe-area-inset-right))] bottom-[max(1rem,env(safe-area-inset-bottom))] z-20 flex size-12 items-center justify-center rounded-full bg-teal-800 text-xl text-white shadow-lg hover:bg-teal-900">
      <span aria-hidden="true">↑</span>
    </button>
  );
}
