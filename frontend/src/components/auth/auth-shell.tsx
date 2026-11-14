import { AuthTopBar, AuthVisual } from "./auth-visual";

export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <main className="relative grid min-h-screen lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
      <AuthTopBar />
      <section className="relative flex min-h-screen items-center px-6 pb-12 pt-28 sm:px-10 lg:px-16 xl:px-24">
        <div className="w-full max-w-[390px]">{children}</div>
      </section>
      <AuthVisual />
    </main>
  );
}

export function FormField({
  label,
  hint,
  error,
  children,
  optional,
}: {
  label: string;
  hint?: string;
  error?: string;
  children: React.ReactNode;
  optional?: boolean;
}) {
  return (
    <label className="block">
      <span className="mb-2 flex items-center justify-between gap-3">
        <span className="text-[12px] font-medium text-muted">{label}</span>
        {optional && <span className="text-[11px] text-dim">Optional</span>}
      </span>
      {children}
      {error ? (
        <span className="mt-1.5 block text-[12px] text-danger">{error}</span>
      ) : hint ? (
        <span className="mt-1.5 block text-[12px] leading-relaxed text-dim">{hint}</span>
      ) : null}
    </label>
  );
}
