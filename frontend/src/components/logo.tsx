import { cn } from "@/lib/format";

export function Logo({ compact = false, className }: { compact?: boolean; className?: string }) {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
        <rect x="1" y="1" width="26" height="26" rx="1" stroke="#3b453c" />
        <path d="M9 21V7h6a4.5 4.5 0 0 1 0 9H9" stroke="#7dded6" strokeWidth="1.5" />
        <circle cx="20.5" cy="20.5" r="1.1" fill="#7dded6" />
      </svg>
      {!compact && (
        <div className="leading-none">
          <div className="font-display text-[20px] tracking-[0.01em] text-mist">POLIS</div>
          <div className="mt-1 text-[11px] text-dim">Personal biological record</div>
        </div>
      )}
    </div>
  );
}
