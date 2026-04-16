"use client";

import { motion } from "framer-motion";
import Link from "next/link";

import { Button } from "../components/ui/button";

export default function HomePage() {
  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background-dark px-6 py-20">
      <div
        className="absolute inset-0 bg-hero-grid opacity-70"
        style={{ backgroundSize: "auto, 72px 72px, 72px 72px" }}
      />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(255,122,0,0.14),_transparent_45%)]" />

      <motion.section
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: "easeOut" }}
        className="relative z-10 mx-auto flex w-full max-w-4xl flex-col items-center rounded-3xl border border-white/10 bg-charcoal/70 px-8 py-16 text-center shadow-glow backdrop-blur"
      >
        <span className="mb-5 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.35em] text-muted-gray">
          Performance Foundation
        </span>
        <h1 className="font-display text-5xl font-bold tracking-tight text-white sm:text-6xl md:text-7xl">
          TrainUp
        </h1>
        <p className="mt-5 max-w-2xl text-lg text-muted-gray sm:text-xl">
          AI-Powered Multi-Sport Coaching Platform
        </p>
        <Button
          asChild
          size="lg"
          className="mt-10 min-w-40 bg-primary text-primary-foreground shadow-glow transition-transform duration-300 hover:-translate-y-0.5 hover:bg-primary/90"
        >
          <Link href="/signup">Get Started</Link>
        </Button>
      </motion.section>
    </main>
  );
}
