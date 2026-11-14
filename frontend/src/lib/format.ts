import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function titleCase(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
    .trim();
}

export function formatDate(value: string | null | undefined, options: Intl.DateTimeFormatOptions = {}): string {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not available";
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    ...options,
  }).format(date);
}

export function formatDateTime(value: string | null | undefined): string {
  return formatDate(value, { hour: "2-digit", minute: "2-digit" });
}

export function relativeTime(value: string | null | undefined): string {
  if (!value) return "not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "not available";
  const seconds = Math.round((date.getTime() - Date.now()) / 1000);
  const ranges: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 60 * 60 * 24 * 365],
    ["month", 60 * 60 * 24 * 30],
    ["week", 60 * 60 * 24 * 7],
    ["day", 60 * 60 * 24],
    ["hour", 60 * 60],
    ["minute", 60],
  ];
  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  for (const [unit, secondsInUnit] of ranges) {
    if (Math.abs(seconds) >= secondsInUnit || unit === "minute") {
      return formatter.format(Math.round(seconds / secondsInUnit), unit);
    }
  }
  return "just now";
}

export function formatNumber(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(value);
}

export function formatValue(value: number | null | undefined, unit = "", digits = 1): string {
  if (value === null || value === undefined) return "n/a";
  const rendered = formatNumber(value, digits);
  return unit ? `${rendered} ${unit}` : rendered;
}

export function formatRange(low: number | null, high: number | null, unit = ""): string {
  if (low === null && high === null) return "No interval supplied";
  if (low === null) return `≤ ${formatNumber(high)} ${unit}`;
  if (high === null) return `≥ ${formatNumber(low)} ${unit}`;
  return `${formatNumber(low)}–${formatNumber(high)} ${unit}`;
}

export function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function clamp(value: number, low: number, high: number): number {
  return Math.min(high, Math.max(low, value));
}

export function categoryLabel(category: string): string {
  const labels: Record<string, string> = {
    liver: "Liver",
    kidney: "Kidneys",
    metabolic: "Metabolic",
    inflammatory: "Inflammation",
    hematology: "Hematology",
    hormonal: "Hormonal",
    nutritional: "Nutrition",
    electrolytes: "Electrolytes",
  };
  return labels[category] ?? titleCase(category);
}

export function rangeTone(status: string): "ok" | "warn" | "danger" | "muted" {
  if (status === "normal" || status === "available" || status === "device_estimate") return "ok";
  if (status === "review" || status === "high" || status === "low") return "warn";
  if (status === "missing" || status === "indeterminate") return "muted";
  if (status === "partial") return "muted";
  return "muted";
}

export function systemStatusLabel(status: string): string {
  return (
    {
      available: "Measurements available",
      review: "Review indicated",
      partial: "Partial data",
      missing: "Data missing",
      experimental: "Experimental",
    }[status] ?? titleCase(status)
  );
}

export function percent(part: number, whole: number): number {
  if (!whole) return 0;
  return Math.round((part / whole) * 100);
}
