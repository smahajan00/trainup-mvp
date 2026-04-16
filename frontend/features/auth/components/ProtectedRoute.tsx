"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { isAuthenticated } from "../../../lib/auth";

type ProtectedRouteProps = {
  children: React.ReactNode;
};

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const router = useRouter();
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }

    setIsReady(true);
  }, [router]);

  if (!isReady) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-background-dark px-6 py-10">
        <div className="rounded-2xl border border-white/10 bg-charcoal/70 px-6 py-5 text-sm text-muted-gray backdrop-blur">
          Validating your session...
        </div>
      </main>
    );
  }

  return <>{children}</>;
}
