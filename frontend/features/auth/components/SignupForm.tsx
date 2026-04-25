"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Label } from "../../../components/ui/label";
import { getErrorMessage } from "../../../lib/api";
import { saveAuthToken } from "../../../lib/auth";
import { registerUser } from "../../../services/auth";
import { AuthShell } from "./AuthShell";

const signupSchema = z.object({
  full_name: z
    .string()
    .trim()
    .min(1, "Full name is required.")
    .max(255, "Full name must be 255 characters or less."),
  email: z.string().trim().email("Enter a valid email address."),
  password: z.string().min(8, "Password must be at least 8 characters.")
});

type SignupFormValues = z.infer<typeof signupSchema>;

export function SignupForm() {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting }
  } = useForm<SignupFormValues>({
    resolver: zodResolver(signupSchema),
    defaultValues: {
      full_name: "",
      email: "",
      password: ""
    }
  });

  useEffect(() => {
    router.prefetch("/profile");
  }, [router]);

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);

    try {
      const response = await registerUser(values);
      saveAuthToken(response.access_token);
      router.replace("/profile");
    } catch (error) {
      setFormError(getErrorMessage(error));
    }
  });

  return (
    <AuthShell
      title="Create account"
      subtitle="Start training in minutes."
      footerLabel="Already have an account?"
      footerHref="/login"
      footerLinkText="Log in"
    >
      <form className="space-y-5" onSubmit={onSubmit}>
        <div className="space-y-2">
          <Label htmlFor="full_name">Full name</Label>
          <Input
            id="full_name"
            autoComplete="name"
            placeholder="Jordan Carter"
            {...register("full_name")}
          />
          {errors.full_name ? (
            <p className="text-sm text-red-300">{errors.full_name.message}</p>
          ) : null}
        </div>

        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="athlete@trainup.ai"
            {...register("email")}
          />
          {errors.email ? (
            <p className="text-sm text-red-300">{errors.email.message}</p>
          ) : null}
        </div>

        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            placeholder="Choose a strong password"
            {...register("password")}
          />
          {errors.password ? (
            <p className="text-sm text-red-300">{errors.password.message}</p>
          ) : null}
        </div>

        {formError ? (
          <div className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {formError}
          </div>
        ) : null}

        <Button className="w-full" size="lg" disabled={isSubmitting}>
          {isSubmitting ? "Creating account..." : "Create Account"}
        </Button>
      </form>
    </AuthShell>
  );
}
