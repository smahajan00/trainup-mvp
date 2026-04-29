"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

const DEFAULT_LINES = [
  "Train smarter. Move better.",
  "Sharpen your form with AI-powered coaching.",
  "Turn every rep into feedback.",
  "Your next improvement starts here.",
  "Record. Analyze. Improve."
];

function getInitialIndex(totalLines: number) {
  const now = new Date();
  return (now.getFullYear() + now.getMonth() + now.getDate()) % totalLines;
}

export function MotivationalHeroLine({
  lines = DEFAULT_LINES
}: {
  lines?: string[];
}) {
  const [index, setIndex] = useState(() => getInitialIndex(lines.length));

  useEffect(() => {
    if (lines.length < 2) {
      return;
    }

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }

    const intervalId = window.setInterval(() => {
      setIndex((currentIndex) => (currentIndex + 1) % lines.length);
    }, 4800);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [lines]);

  return (
    <div className="mt-5 inline-flex min-h-12 items-center gap-3 rounded-full border border-primary/15 bg-primary/10 px-4 py-3 text-sm text-white/85 shadow-[0_16px_38px_rgba(255,122,0,0.12)]">
      <span className="h-2.5 w-2.5 rounded-full bg-primary shadow-[0_0_18px_rgba(255,122,0,0.55)]" />
      <AnimatePresence mode="wait">
        <motion.span
          key={index}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.24, ease: "easeOut" }}
        >
          {lines[index]}
        </motion.span>
      </AnimatePresence>
    </div>
  );
}
