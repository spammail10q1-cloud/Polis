import { cn } from "@/lib/format";

const statusStyles: Record<string, string> = {
  normal: "text-mint border-mint/30 bg-mint/[0.06]",
  available: "text-mint border-mint/30 bg-mint/[0.06]",
  high: "text-amber border-amber/35 bg-amber/[0.07]",
  low: "text-amber border-amber/35 bg-amber/[0.07]",
  review: "text-amber border-amber/35 bg-amber/[0.07]",
  partial: "text-signal border-signal/30 bg-signal/[0.06]",
  indeterminate: "text-dim border-line bg-transparent",
  missing: "text-dim border-line bg-transparent",
  experimental: "text-violet border-violet/30 bg-violet/[0.06]",
  device_estimate: "text-signal border-signal/30 bg-signal/[0.06]",
};

const labels: Record<string, string> = {
  normal: "In interval",
  available: "Available",
  high: "Above interval",
  low: "Below interval",
  review: "Review",
  partial: "Partial",
  indeterminate: "Indeterminate",
  missing: "Missing",
  experimental: "Experimental",
  device_estimate: "Device estimate",
};

export function StatusPill({ status, className }: { status: string; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center whitespace-nowrap rounded-[2px] border px-2 py-0.5 text-[11px] font-medium",
        statusStyles[status] ?? "text-dim border-line",
        className,
      )}
    >
      {labels[status] ?? status.replaceAll("_", " ")}
    </span>
  );
}

export function LiveDot({ tone = "signal", label }: { tone?: "signal" | "amber" | "muted"; label?: string }) {
  const color = tone === "signal" ? "bg-signal" : tone === "amber" ? "bg-amber" : "bg-dim";
  return (
    <span className="inline-flex items-center gap-2">
      <span className={cn("h-1.5 w-1.5 rounded-full", color)} aria-hidden="true" />
      {label && <span className="text-[12px] text-muted">{label}</span>}
    </span>
  );
}
