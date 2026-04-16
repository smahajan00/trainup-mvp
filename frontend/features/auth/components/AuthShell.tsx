"use client";

import { motion } from "framer-motion";
import Link from "next/link";

type AuthShellProps = {
  title: string;
  subtitle: string;
  footerLabel: string;
  footerHref: string;
  footerLinkText: string;
  children: React.ReactNode;
};

export function AuthShell({
  title,
  subtitle,
  footerLabel,
  footerHref,
  footerLinkText,
  children
}: AuthShellProps) {
  return (
    <main className="relative min-h-screen overflow-hidden bg-background-dark px-6 py-10">
      <div
        className="absolute inset-0 bg-hero-grid opacity-60"
        style={{ backgroundSize: "auto, 72px 72px, 72px 72px" }}
      />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(255,122,0,0.18),_transparent_35%),radial-gradient(circle_at_bottom_right,_rgba(255,255,255,0.06),_transparent_28%)]" />

      <div className="relative z-10 mx-auto grid min-h-[calc(100vh-5rem)] w-full max-w-6xl items-center gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <motion.section
          initial={{ opacity: 0, x: -18 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.55, ease: "easeOut" }}
          className="rounded-[2rem] border border-white/10 bg-charcoal/65 p-8 shadow-glow backdrop-blur lg:p-12"
        >
          <div className="inline-flex rounded-full border border-primary/30 bg-primary/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.35em] text-primary">
            TrainUp Access
          </div>
          <h1 className="mt-6 max-w-xl font-display text-4xl font-bold tracking-tight text-white sm:text-5xl">
            AI-powered coaching starts with a clean athlete setup.
          </h1>
          <p className="mt-5 max-w-xl text-base leading-7 text-muted-gray sm:text-lg">
            Register, sign in, and build a structured athlete profile tied to
            your sport and skill level. This foundation is what later powers
            feedback, scoring, and performance analysis across TrainUp.
          </p>
          <div className="mt-10 grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
              <p className="text-sm font-semibold text-white">Secure access</p>
              <p className="mt-2 text-sm leading-6 text-muted-gray">
                JWT-based authentication with profile-aware redirects keeps the
                onboarding flow clean and predictable.
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
              <p className="text-sm font-semibold text-white">Sport-aware setup</p>
              <p className="mt-2 text-sm leading-6 text-muted-gray">
                Seeded sports and structured profile fields keep athlete data
                ready for deterministic coaching logic.
              </p>
            </div>
          </div>
        </motion.section>

        <motion.section
          initial={{ opacity: 0, x: 18 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.55, ease: "easeOut", delay: 0.05 }}
          className="rounded-[2rem] border border-white/10 bg-slate/75 p-8 shadow-2xl backdrop-blur lg:p-10"
        >
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-primary">
            {title}
          </p>
          <h2 className="mt-4 font-display text-3xl font-bold text-white">
            {subtitle}
          </h2>
          <div className="mt-8">{children}</div>
          <p className="mt-8 text-sm text-muted-gray">
            {footerLabel}{" "}
            <Link
              href={footerHref}
              className="font-semibold text-primary transition-colors hover:text-primary/80"
            >
              {footerLinkText}
            </Link>
          </p>
        </motion.section>
      </div>
    </main>
  );
}
