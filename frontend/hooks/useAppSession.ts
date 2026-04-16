"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError, getErrorMessage } from "../lib/api";
import { clearAuthToken, getAuthToken } from "../lib/auth";
import { getCurrentUser } from "../services/auth";
import { getProfile } from "../services/profile";
import type { CurrentUserResponse } from "../types/auth";
import type { ProfileResponse } from "../types/profile";

type AppSessionState = {
  user: CurrentUserResponse | null;
  profile: ProfileResponse | null;
  isLoading: boolean;
  error: string | null;
  logout: () => void;
};

export function useAppSession(): AppSessionState {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUserResponse | null>(null);
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;

    async function loadSession() {
      if (!getAuthToken()) {
        router.replace("/login");
        setIsLoading(false);
        return;
      }

      setError(null);

      try {
        const [currentUser, profileResult] = await Promise.all([
          getCurrentUser(),
          getProfile()
        ]);

        if (ignore) {
          return;
        }

        setUser(currentUser);
        setProfile(profileResult.profile);
      } catch (loadError) {
        if (loadError instanceof ApiError && loadError.status === 401) {
          clearAuthToken();
          router.replace("/login");
          return;
        }

        if (!ignore) {
          setError(getErrorMessage(loadError));
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    loadSession();

    return () => {
      ignore = true;
    };
  }, [router]);

  function logout() {
    clearAuthToken();
    router.replace("/login");
  }

  return {
    user,
    profile,
    isLoading,
    error,
    logout
  };
}
