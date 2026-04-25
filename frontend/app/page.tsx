"use client";

import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { BarChart3, Camera, UploadCloud } from "lucide-react";

import { Button } from "../components/ui/button";

export default function HomePage() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-[#0f1115]">
      <div
        className="absolute inset-0 bg-hero-grid opacity-[0.06]"
        style={{ backgroundSize: "auto, 72px 72px, 72px 72px" }}
      />

      <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(0,0,0,0.16),transparent_26%,rgba(0,0,0,0.44)_100%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_42%,rgba(5,7,10,0.16)_70%,rgba(5,7,10,0.62)_100%)]" />
      <div className="absolute inset-y-0 left-0 w-full md:w-[54%] bg-[linear-gradient(90deg,rgba(8,10,15,0.98)_0%,rgba(10,12,18,0.97)_44%,rgba(15,17,21,0.9)_72%,rgba(15,17,21,0.54)_100%)]" />

      <motion.div
        className="absolute inset-y-0 right-0 w-full md:w-[63%]"
        animate={{ scale: [1.03, 1.043, 1.03], x: [0, 6, 0] }}
        transition={{
          duration: 16,
          ease: "easeInOut",
          repeat: Number.POSITIVE_INFINITY
        }}
      >
        <div className="absolute inset-0">
          <Image
            src="/hero-football.webp"
            alt=""
            fill
            priority
            sizes="(min-width: 768px) 63vw, 100vw"
            className="object-cover object-[90%_center] opacity-100 brightness-[1.16] saturate-[0.96] contrast-[1.18]"
          />
        </div>
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_62%_56%,rgba(255,122,0,0.14),transparent_12%),radial-gradient(circle_at_85%_40%,rgba(101,173,255,0.08),transparent_18%),radial-gradient(circle_at_80%_80%,rgba(255,122,0,0.18),transparent_18%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(110deg,transparent_74%,rgba(255,122,0,0.06)_82%,transparent_90%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(15,17,21,1)_0%,rgba(15,17,21,0.985)_18%,rgba(15,17,21,0.88)_32%,rgba(15,17,21,0.5)_46%,rgba(15,17,21,0.14)_62%,rgba(15,17,21,0.05)_80%,rgba(15,17,21,0.34)_100%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_88%_10%,rgba(9,10,14,0.52),transparent_28%),linear-gradient(180deg,rgba(15,17,21,0.3),transparent_24%,rgba(15,17,21,0.36)_100%)]" />
      </motion.div>

      <div className="pointer-events-none absolute inset-y-0 left-0 w-full bg-[linear-gradient(90deg,rgba(15,17,21,0.995)_0%,rgba(15,17,21,0.965)_28%,rgba(15,17,21,0.5)_46%,transparent_72%)]" />
      <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-40 bg-[linear-gradient(180deg,transparent,rgba(15,17,21,0.72))]" />

      <div className="pointer-events-none absolute inset-y-0 left-[50.4%] hidden md:block">
        <div
          className="absolute inset-y-[-4%] left-0 w-[4.2rem]"
          style={{
            transform: "skewX(-28deg)",
            clipPath: "polygon(34% 0,100% 0,66% 100%,0 100%)"
          }}
        >
          <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(30,18,20,0)_0%,rgba(24,15,21,0.92)_12%,rgba(18,12,18,0.48)_62%,rgba(30,18,20,0)_100%)]" />
        </div>

        <div
          className="absolute inset-y-[-5%] left-[3.65rem] w-[5.2rem]"
          style={{
            transform: "skewX(-28deg)",
            clipPath: "polygon(28% 0,100% 0,72% 100%,0 100%)"
          }}
        >
          <div className="absolute inset-0 bg-[linear-gradient(180deg,#ff9f28_0%,#ff7a00_56%,#ff5f00_100%)] shadow-[0_16px_38px_rgba(255,122,0,0.18)]" />
          <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(255,255,255,0.15),transparent_30%,transparent_72%,rgba(0,0,0,0.1)_100%)]" />
        </div>

        <div
          className="absolute inset-y-[6%] left-[9.45rem] w-[1.75rem]"
          style={{
            transform: "skewX(-28deg)",
            clipPath: "polygon(28% 0,100% 0,72% 100%,0 100%)"
          }}
        >
          <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(255,144,22,0.72),rgba(255,122,0,0.24)_100%)]" />
        </div>

        <div
          className="absolute inset-y-[14%] left-[11.9rem] w-[1.05rem]"
          style={{
            transform: "skewX(-28deg)",
            clipPath: "polygon(28% 0,100% 0,72% 100%,0 100%)"
          }}
        >
          <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(255,133,12,0.58),rgba(255,122,0,0.12)_100%)]" />
        </div>

        <div
          className="absolute inset-y-[3%] left-[8.95rem] w-[2px]"
          style={{
            transform: "skewX(-28deg)",
            background:
              "linear-gradient(180deg, rgba(255,214,148,0) 0%, rgba(255,214,148,0.94) 16%, rgba(255,214,148,0.62) 54%, rgba(255,214,148,0) 100%)",
            boxShadow: "0 0 12px rgba(255,198,110,0.2)"
          }}
        />
      </div>

      <div
        className="pointer-events-none absolute left-[57.2%] top-[24%] hidden h-[2px] w-[16rem] md:block"
        style={{
          transform: "rotate(-28deg)",
          background:
            "linear-gradient(90deg, rgba(255,146,34,0) 0%, rgba(255,146,34,0.22) 48%, rgba(255,146,34,0) 100%)"
        }}
      />
      <div
        className="pointer-events-none absolute left-[62.2%] bottom-[20%] hidden h-[2px] w-[13rem] md:block"
        style={{
          transform: "rotate(-28deg)",
          background:
            "linear-gradient(90deg, rgba(255,183,95,0) 0%, rgba(255,183,95,0.16) 48%, rgba(255,183,95,0) 100%)"
        }}
      />

      <section className="relative z-10 mx-auto flex min-h-screen w-full max-w-7xl items-center px-6 py-20 sm:px-8 lg:px-12">
        <motion.div
          initial={{ opacity: 0, y: 22 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="flex w-full max-w-[540px] flex-col"
        >
          <div className="mx-auto mt-4 flex w-full max-w-[29rem] flex-col items-center">
            <span className="inline-flex w-fit rounded-full border border-white/10 bg-white/[0.03] px-4 py-2 text-[0.7rem] font-semibold uppercase tracking-[0.34em] text-white/64">
              Built For Performance
            </span>

            <div className="mt-10 flex flex-col items-center text-center sm:mt-12">
              <h1 className="font-display text-6xl font-bold tracking-[-0.05em] text-white sm:text-7xl lg:text-[6.2rem]">
                TrainUp
              </h1>

              <p className="mt-5 max-w-md text-lg text-white/66 sm:text-xl">
                Train smarter. Improve faster.
              </p>

              <div className="relative mt-10 flex justify-center">
                <div className="absolute inset-x-8 inset-y-3 -z-10 rounded-full bg-primary/18 blur-xl" />
                <Button
                  asChild
                  size="lg"
                  className="h-14 min-w-52 rounded-2xl bg-primary px-10 text-base font-semibold text-primary-foreground shadow-[0_14px_30px_rgba(255,122,0,0.22),inset_0_1px_0_rgba(255,255,255,0.14)] transition-all duration-300 hover:-translate-y-0.5 hover:scale-[1.02] hover:bg-primary/92 hover:shadow-[0_18px_36px_rgba(255,122,0,0.28),inset_0_1px_0_rgba(255,255,255,0.18)]"
                >
                  <Link href="/signup">Start Training</Link>
                </Button>
              </div>

              <div className="mt-8 flex items-center justify-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/8 bg-white/[0.04] text-white/76 shadow-[0_10px_30px_rgba(0,0,0,0.2)] transition-transform duration-300 hover:-translate-y-0.5">
                  <Camera className="h-4 w-4" />
                </div>
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/8 bg-white/[0.04] text-white/76 shadow-[0_10px_30px_rgba(0,0,0,0.2)] transition-transform duration-300 hover:-translate-y-0.5">
                  <UploadCloud className="h-4 w-4" />
                </div>
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/8 bg-white/[0.04] text-white/76 shadow-[0_10px_30px_rgba(0,0,0,0.2)] transition-transform duration-300 hover:-translate-y-0.5">
                  <BarChart3 className="h-4 w-4" />
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </section>
    </main>
  );
}
