"use client";

import { cn } from "@/lib/format";

export function Tabs<T extends string>({
  value,
  onChange,
  items,
  className,
}: {
  value: T;
  onChange: (value: T) => void;
  items: { value: T; label: string; count?: number }[];
  className?: string;
}) {
  return (
    <div className={cn("flex gap-1 overflow-x-auto border-b border-line", className)}>
      {items.map((item) => (
        <button
          key={item.value}
          onClick={() => onChange(item.value)}
          aria-pressed={value === item.value}
          className={cn(
            "relative shrink-0 px-3 py-2.5 text-[13px] transition-colors",
            value === item.value ? "text-mist" : "text-muted hover:text-mist",
          )}
        >
          {item.label}
          {item.count !== undefined && <span className="ml-1.5 font-mono text-[11px] text-dim">{item.count}</span>}
          {value === item.value && <span className="absolute inset-x-2 -bottom-px h-0.5 bg-signal" />}
        </button>
      ))}
    </div>
  );
}

export function ProgressBar({
  value,
  tone = "signal",
  className,
  height = "h-1.5",
}: {
  value: number;
  tone?: "signal" | "violet" | "amber" | "muted";
  className?: string;
  height?: string;
}) {
  const colors = {
    signal: "bg-signal",
    violet: "bg-violet",
    amber: "bg-amber",
    muted: "bg-dim",
  };
  return (
    <div
      className={cn("w-full overflow-hidden rounded-[1px] bg-raised", height, className)}
      role="progressbar"
      aria-valuenow={Math.round(value)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className={cn("h-full transition-[width] duration-300", colors[tone])}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}

export function Meter({
  value,
  max,
  tone = "violet",
  label,
}: {
  value: number;
  max: number;
  tone?: "signal" | "violet" | "amber";
  label?: string;
}) {
  const percent = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div>
      {label && <div className="mono-label mb-2">{label}</div>}
      <ProgressBar value={percent} tone={tone} />
      <div className="mt-1.5 flex justify-between font-mono text-[11px] text-dim">
        <span>{value.toFixed(2)} spent</span>
        <span>{max.toFixed(1)} limit</span>
      </div>
    </div>
  );
}
