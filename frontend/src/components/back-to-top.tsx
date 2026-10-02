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
      className="fixed right-[max(1rem,env(safe-area-inset-right))] bottom-[max(1rem,env(safe-area-inset-bottom))] z-20 flex size-12 items-center justify-center rounded-full bg-[#4f8cff] text-xl text-white shadow-[0_10px_30px_rgba(79,140,255,0.3)] transition hover:-translate-y-0.5 hover:bg-[#3978ed]">
      <span aria-hidden="true">↑</span>
    </button>
  );
}
