import { cn } from "@/lib/format";

type Tone = "neutral" | "signal" | "violet" | "amber" | "danger" | "mint" | "muted";

const toneClasses: Record<Tone, string> = {
  neutral: "border-line bg-raised/70 text-mist/85",
  signal: "border-signal/30 bg-signal/[0.07] text-signal",
  violet: "border-violet/30 bg-violet/[0.07] text-violet",
  amber: "border-amber/35 bg-amber/[0.07] text-amber",
  danger: "border-danger/35 bg-danger/[0.07] text-danger",
  mint: "border-mint/30 bg-mint/[0.06] text-mint",
  muted: "border-line bg-transparent text-dim",
};

export function Badge({
  children,
  tone = "neutral",
  className,
  dot,
}: {
  children: React.ReactNode;
  tone?: Tone;
  className?: string;
  dot?: boolean;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 whitespace-nowrap rounded-[2px] border px-2 py-0.5 text-[11px] font-medium",
        toneClasses[tone],
        className,
      )}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}

const evidenceTone: Record<string, Tone> = {
  established_clinical_evidence: "mint",
  established: "mint",
  personalized_evidence: "signal",
  personalized: "signal",
  model_estimate: "violet",
  estimate: "violet",
  experimental_hypothesis: "violet",
  experimental: "violet",
  supporting_evidence: "signal",
  unknown: "muted",
};

const evidenceLabel: Record<string, string> = {
  established_clinical_evidence: "Clinical evidence",
  established: "Clinical evidence",
  personalized_evidence: "Personal evidence",
  personalized: "Personal evidence",
  model_estimate: "Model estimate",
  estimate: "Model estimate",
  experimental_hypothesis: "Experimental hypothesis",
  experimental: "Experimental",
  supporting_evidence: "Supporting evidence",
  unknown: "Unknown",
};

export function EvidenceBadge({ value, className }: { value: string; className?: string }) {
  return (
    <Badge tone={evidenceTone[value] ?? "neutral"} className={className} dot>
      {evidenceLabel[value] ?? value.replaceAll("_", " ")}
    </Badge>
  );
}
