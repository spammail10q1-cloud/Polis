"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, MessageSquareText, ShieldCheck } from "lucide-react";
import { pageMeta } from "@/lib/nav";
import { formatDate, relativeTime } from "@/lib/format";
import { useQuery } from "@/lib/use-query";
import type { Overview } from "@/lib/types";

export function Topbar({ onMenu }: { onMenu: () => void }) {
  const pathname = usePathname();
  const meta = pageMeta[pathname] ?? pageMeta["/overview"];
  const { data } = useQuery<Overview>("/overview");
  const lastLab = data?.data_status.last_laboratory;
  const completeness = data?.data_status.data_completeness;
  const today = formatDate(new Date().toISOString(), { weekday: "short", day: "2-digit", month: "short" });

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-4 border-b border-line bg-ink px-4 sm:px-6">
      <div className="flex min-w-0 items-center gap-2">
        <button
          onClick={onMenu}
          aria-label="Open navigation"
          className="-ml-2 flex h-11 w-11 items-center justify-center text-muted hover:text-mist lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div className="flex min-w-0 items-center gap-2 text-[13px]">
          <span className="hidden text-dim sm:inline">POLIS</span>
          <span className="hidden text-dim sm:inline" aria-hidden="true">/</span>
          <span className="truncate text-mist">{meta.title}</span>
        </div>
      </div>

      <div className="flex items-center gap-3 sm:gap-4">
        <div className="hidden items-center gap-2 text-[12px] text-dim md:flex">
          <span>{lastLab ? `Lab sync ${relativeTime(lastLab)}` : "No laboratory sync"}</span>
          {completeness !== undefined && (
            <>
              <span className="h-3 w-px bg-line" aria-hidden="true" />
              <span>{completeness}% complete</span>
            </>
          )}
        </div>
        <div className="hidden items-center gap-1.5 text-[12px] text-muted sm:flex">
          <ShieldCheck className="h-4 w-4 text-mint" />
          <span>Local-first</span>
        </div>
        <span className="hidden text-[12px] text-dim xl:inline">{today}</span>
        <Link href="/assistant" className="btn btn-secondary min-h-9 px-3 text-[12px]">
          <MessageSquareText className="h-4 w-4 text-signal" />
          Ask POLIS
        </Link>
      </div>
    </header>
  );
}
