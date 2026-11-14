import { AlertTriangle, FlaskConical, Info, ShieldAlert } from "lucide-react";
import { cn } from "@/lib/format";

type Tone = "info" | "warning" | "danger" | "violet" | "neutral";

const styles: Record<Tone, { wrap: string; icon: React.ReactNode; title: string }> = {
  info: {
    wrap: "border-signal/25 bg-signal/[0.035]",
    icon: <Info className="h-4 w-4 text-signal" />,
    title: "text-signal",
  },
  warning: {
    wrap: "border-amber/30 bg-amber/[0.035]",
    icon: <AlertTriangle className="h-4 w-4 text-amber" />,
    title: "text-amber",
  },
  danger: {
    wrap: "border-danger/30 bg-danger/[0.04]",
    icon: <ShieldAlert className="h-4 w-4 text-danger" />,
    title: "text-danger",
  },
  violet: {
    wrap: "border-violet/30 bg-violet/[0.035]",
    icon: <FlaskConical className="h-4 w-4 text-violet" />,
    title: "text-violet",
  },
  neutral: {
    wrap: "border-line bg-panel",
    icon: <Info className="h-4 w-4 text-dim" />,
    title: "text-mist",
  },
};

export function Callout({
  tone = "neutral",
  title,
  children,
  className,
}: {
  tone?: Tone;
  title?: string;
  children: React.ReactNode;
  className?: string;
}) {
  const style = styles[tone];
  return (
    <div className={cn("flex gap-3 rounded-[2px] border px-4 py-3", style.wrap, className)}>
      <div className="mt-0.5 shrink-0">{style.icon}</div>
      <div className="min-w-0">
        {title && <div className={cn("mb-1 text-[13px] font-medium", style.title)}>{title}</div>}
        <div className="text-[13px] leading-relaxed text-muted">{children}</div>
      </div>
    </div>
  );
}
