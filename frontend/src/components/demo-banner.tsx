import Link from "next/link";
import { FlaskConical } from "lucide-react";

export function DemoBanner() {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-amber/20 bg-amber/[0.035] px-4 py-2 sm:px-6">
      <div className="flex min-w-0 items-center gap-2.5">
        <FlaskConical className="h-4 w-4 shrink-0 text-amber" />
        <p className="truncate text-[12px] text-amber">
          <span className="sm:hidden">Demo data: synthetic</span>
          <span className="hidden sm:inline">Demonstration data: synthetic, not real patient information</span>
        </p>
      </div>
      <Link
        href="/privacy"
        className="shrink-0 text-[12px] text-amber underline decoration-amber/40 underline-offset-4 hover:text-mist"
      >
        Data controls
      </Link>
    </div>
  );
}
