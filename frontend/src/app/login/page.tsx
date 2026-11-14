"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { Eye, EyeOff, LoaderCircle, LockKeyhole } from "lucide-react";
import { AuthShell, FormField } from "@/components/auth/auth-shell";
import { useAuth } from "@/components/auth-provider";
import { useToast } from "@/components/toast";
import { errorMessage } from "@/lib/api";
import { validateLogin } from "@/lib/validation";

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next") || "/overview";
  const { user, loading, login, demoLogin } = useAuth();
  const { push } = useToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<ReturnType<typeof validateLogin>>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [demoSubmitting, setDemoSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace(next.startsWith("/") ? next : "/overview");
  }, [loading, user, router, next]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const nextErrors = validateLogin({ email, password });
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;
    setSubmitting(true);
    setApiError(null);
    try {
      await login(email.trim(), password);
      router.replace(next.startsWith("/") ? next : "/overview");
    } catch (error) {
      setApiError(errorMessage(error));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDemo = async () => {
    setDemoSubmitting(true);
    setApiError(null);
    try {
      await demoLogin();
      push("Demonstration twin loaded. All personal data are synthetic.", "info");
      router.replace("/overview");
    } catch (error) {
      setApiError(errorMessage(error));
    } finally {
      setDemoSubmitting(false);
    }
  };

  return (
    <AuthShell>
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <div className="eyebrow mb-4">Private health intelligence</div>
        <h1 className="display text-[38px] text-mist sm:text-[44px]">
          A living model
          <br />
          of your biology.
        </h1>
        <p className="mt-4 text-[14px] leading-relaxed text-muted">
          POLIS builds a continuously updatable computational twin from your own measurements, genetics and
          context. Provenance, uncertainty and clinical boundaries stay visible.
        </p>

        <button
          onClick={handleDemo}
          disabled={demoSubmitting}
          className="mt-7 flex w-full items-center justify-between gap-4 border border-line bg-panel px-4 py-3.5 text-left transition-colors hover:border-dim/60 hover:bg-raised disabled:opacity-60"
        >
          <span>
            <span className="block text-[14px] text-mist">Explore the demonstration twin</span>
            <span className="mt-1 block text-[12px] text-dim">Synthetic profile, no account required</span>
          </span>
          {demoSubmitting ? (
            <LoaderCircle className="h-4 w-4 shrink-0 animate-spin text-signal" aria-hidden="true" />
          ) : (
            <span className="shrink-0 text-[12px] text-signal">Open</span>
          )}
        </button>

        <div className="my-6 flex items-center gap-3">
          <span className="h-px flex-1 bg-line" />
          <span className="text-[12px] text-dim">or sign in</span>
          <span className="h-px flex-1 bg-line" />
        </div>

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <FormField label="Email" error={errors.email}>
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              className="input"
              aria-invalid={Boolean(errors.email)}
            />
          </FormField>
          <FormField label="Password" error={errors.password}>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="••••••••••"
                className="input pr-12"
                aria-invalid={Boolean(errors.password)}
              />
              <button
                type="button"
                onClick={() => setShowPassword((value) => !value)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                className="absolute right-0 top-1/2 flex h-11 w-11 -translate-y-1/2 items-center justify-center text-dim hover:text-muted"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </FormField>

          {apiError && (
            <div role="alert" className="border border-danger/30 bg-danger/[0.04] px-3 py-2.5 text-[13px] leading-relaxed text-danger">
              {apiError}
            </div>
          )}

          <button type="submit" disabled={submitting} className="btn btn-primary min-h-11 w-full">
            {submitting && <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />}
            Sign in
          </button>
        </form>

        <p className="mt-5 text-center text-[13px] text-dim">
          New to POLIS?{" "}
          <Link href="/register" className="text-muted underline decoration-line underline-offset-4 hover:text-mist">
            Create an account
          </Link>
        </p>

        <div className="mt-10 flex items-start gap-2.5 border-t border-line pt-4">
          <LockKeyhole className="mt-0.5 h-4 w-4 shrink-0 text-dim" aria-hidden="true" />
          <p className="text-[12px] leading-relaxed text-dim">
            Health data are exceptionally sensitive. POLIS is an experimental research platform, not a medical
            device. It does not diagnose, prescribe or replace professional care. Demonstration data are entirely
            synthetic.
          </p>
        </div>
      </motion.div>
    </AuthShell>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen" />}>
      <LoginContent />
    </Suspense>
  );
}
