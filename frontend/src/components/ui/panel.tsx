import { cn } from "@/lib/format";

export function Panel({
  children,
  className,
  emphasis,
}: {
  children: React.ReactNode;
  className?: string;
  emphasis?: boolean;
}) {
  return <section className={cn("panel", emphasis && "panel-emphasis", className)}>{children}</section>;
}

export function PanelHeader({
  eyebrow,
  title,
  description,
  action,
  className,
}: {
  eyebrow?: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-start justify-between gap-4 border-b border-line px-5 py-4", className)}>
      <div className="min-w-0">
        {eyebrow && <div className="eyebrow mb-1.5">{eyebrow}</div>}
        <h2 className="text-[16px] font-medium tracking-[-0.01em] text-mist">{title}</h2>
        {description && <p className="mt-1 max-w-2xl text-[13px] leading-relaxed text-muted">{description}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export function PanelBody({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("p-5", className)}>{children}</div>;
}

export function Hairline({ className }: { className?: string }) {
  return <div className={cn("hairline", className)} />;
}

export function Stat({
  label,
  value,
  unit,
  note,
  tone = "default",
}: {
  label: string;
  value: React.ReactNode;
  unit?: string;
  note?: string;
  tone?: "default" | "signal" | "amber" | "violet" | "danger";
}) {
  const color = {
    default: "text-mist",
    signal: "text-signal",
    amber: "text-amber",
    violet: "text-violet",
    danger: "text-danger",
  }[tone];
  return (
    <div className="min-w-0">
      <div className="mono-label">{label}</div>
      <div className="mt-2 flex items-baseline gap-1.5">
        <span className={cn("number text-[27px] leading-none", color)}>{value}</span>
        {unit && <span className="font-mono text-[11px] text-dim">{unit}</span>}
      </div>
      {note && <div className="mt-2 text-[12px] leading-relaxed text-dim">{note}</div>}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse bg-raised", className)} />;
}

export function LoadError({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="panel-flat flex flex-col items-center gap-3 px-6 py-10 text-center">
      <div className="text-[12px] font-medium text-danger">Data unavailable</div>
      <p className="max-w-md text-[13px] leading-relaxed text-muted">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn btn-secondary mt-1">
          Try again
        </button>
      )}
    </div>
  );
}
