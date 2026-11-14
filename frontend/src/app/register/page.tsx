"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Eye, EyeOff, LoaderCircle, ShieldCheck } from "lucide-react";
import { AuthShell, FormField } from "@/components/auth/auth-shell";
import { useAuth } from "@/components/auth-provider";
import { useToast } from "@/components/toast";
import { errorMessage } from "@/lib/api";
import { validateRegister } from "@/lib/validation";
import { cn } from "@/lib/format";

export default function RegisterPage() {
  const router = useRouter();
  const { user, loading, register } = useAuth();
  const { push } = useToast();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [aiProcessing, setAiProcessing] = useState(false);
  const [research, setResearch] = useState(false);
  const [errors, setErrors] = useState<ReturnType<typeof validateRegister>>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace("/overview");
  }, [loading, user, router]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const nextErrors = validateRegister({ name, email, password, accept_terms: acceptTerms });
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;
    setSubmitting(true);
    setApiError(null);
    try {
      await register({
        name: name.trim(),
        email: email.trim(),
        password,
        accept_terms: acceptTerms,
        ai_processing: aiProcessing,
        research_participation: research,
      });
      push("Account created. Your profile is ready to build.", "success");
      router.replace("/overview");
    } catch (error) {
      setApiError(errorMessage(error));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthShell>
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <Link
          href="/login"
          className="mb-8 inline-flex min-h-11 items-center text-[12px] text-dim underline decoration-line underline-offset-4 transition-colors hover:text-muted"
        >
          Back to sign in
        </Link>
        <div className="eyebrow mb-4">Create your private record</div>
        <h1 className="display text-[36px] text-mist sm:text-[42px]">
          Start with
          <br />
          your own biology.
        </h1>
        <p className="mt-4 text-[14px] leading-relaxed text-muted">
          A new account starts empty. You decide what to add, what to connect, and whether research or federated
          participation is ever enabled.
        </p>

        <form onSubmit={handleSubmit} noValidate className="mt-7 space-y-4">
          <FormField label="Name" error={errors.name}>
            <input
              autoComplete="name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Your name"
              className="input"
              aria-invalid={Boolean(errors.name)}
            />
          </FormField>
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
          <FormField
            label="Password"
            error={errors.password}
            hint="At least 10 characters, including a letter and a number."
          >
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Create a strong password"
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

          <div className="space-y-3.5 border-t border-line pt-4">
            <ConsentCheck
              checked={acceptTerms}
              onChange={setAcceptTerms}
              label="I accept the terms and privacy notice."
              detail="Required to create an account. This is not a substitute for the full privacy documentation."
              error={errors.accept_terms}
            />
            <ConsentCheck
              checked={aiProcessing}
              onChange={setAiProcessing}
              label="Enable AI processing for POLIS AI"
              detail="Optional. Without it, the assistant and external model features stay disabled; the rest of POLIS remains available."
            />
            <ConsentCheck
              checked={research}
              onChange={setResearch}
              label="Participate in research"
              detail="Optional and independently controlled. Does not enable federated learning."
            />
          </div>

          {apiError && (
            <div role="alert" className="border border-danger/30 bg-danger/[0.04] px-3 py-2.5 text-[13px] leading-relaxed text-danger">
              {apiError}
            </div>
          )}

          <button type="submit" disabled={submitting} className="btn btn-primary min-h-11 w-full">
            {submitting && <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />}
            Create account
          </button>
        </form>

        <div className="mt-6 flex items-start gap-2.5">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-dim" aria-hidden="true" />
          <p className="text-[12px] leading-relaxed text-dim">
            Passwords are stored using memory-hard scrypt hashing. Session cookies are HttpOnly. You can export or
            delete your data at any time from Privacy &amp; Data.
          </p>
        </div>
      </motion.div>
    </AuthShell>
  );
}

function ConsentCheck({
  checked,
  onChange,
  label,
  detail,
  error,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  label: string;
  detail: string;
  error?: string;
}) {
  return (
    <label className="flex cursor-pointer items-start gap-3 rounded-[2px] focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-signal">
      <span
        className={cn(
          "mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center border transition-colors",
          checked ? "border-signal bg-signal/15" : "border-dim/60 bg-transparent",
        )}
      >
        <input
          type="checkbox"
          checked={checked}
          onChange={(event) => onChange(event.target.checked)}
          className="sr-only"
        />
        {checked && <span className="h-2 w-2 bg-signal" />}
      </span>
      <span>
        <span className="block text-[13px] leading-snug text-mist/90">{label}</span>
        <span className="mt-1 block text-[12px] leading-relaxed text-dim">{detail}</span>
        {error && <span className="mt-1 block text-[12px] text-danger">{error}</span>}
      </span>
    </label>
  );
}
