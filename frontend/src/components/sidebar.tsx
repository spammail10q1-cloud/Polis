"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, X } from "lucide-react";
import { navItems } from "@/lib/nav";
import { cn, initials } from "@/lib/format";
import { useAuth } from "@/components/auth-provider";
import { Logo } from "@/components/logo";

function NavLink({
  item,
  active,
  onClick,
}: {
  item: (typeof navItems)[number];
  active: boolean;
  onClick?: () => void;
}) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      onClick={onClick}
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex min-h-11 items-center gap-3 border-l-2 px-3.5 py-2 text-[13px] transition-colors",
        active
          ? "border-signal bg-raised text-mist"
          : "border-transparent text-muted hover:bg-raised/60 hover:text-mist",
      )}
    >
      <Icon className={cn("h-4 w-4 shrink-0", active ? "text-signal" : "text-dim")} strokeWidth={1.6} />
      <span className="flex-1">{item.label}</span>
      {item.hint && <span className="text-[11px] text-dim">{item.hint}</span>}
    </Link>
  );
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const primary = navItems.filter((item) => item.group === "primary");
  const secondary = navItems.filter((item) => item.group === "secondary");

  const handleLogout = async () => {
    await logout();
    router.replace("/login");
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-[68px] items-center border-b border-line px-5">
        <Link href="/overview" onClick={onNavigate} aria-label="POLIS overview">
          <Logo />
        </Link>
      </div>

      <div className="scroll-area flex-1 overflow-y-auto py-5">
        <div className="mb-2 px-4 text-[11px] font-medium text-dim">Workspace</div>
        <nav className="flex flex-col gap-0.5" aria-label="Workspace">
          {primary.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              active={pathname === item.href || pathname.startsWith(`${item.href}/`)}
              onClick={onNavigate}
            />
          ))}
        </nav>

        <div className="mx-4 my-5 h-px bg-line" />
        <div className="mb-2 px-4 text-[11px] font-medium text-dim">Account</div>
        <nav className="flex flex-col gap-0.5" aria-label="Account">
          {secondary.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              active={pathname === item.href || pathname.startsWith(`${item.href}/`)}
              onClick={onNavigate}
            />
          ))}
        </nav>

        <div className="mx-4 mt-7 border-t border-line pt-4">
          <div className="flex items-center justify-between text-[12px]">
            <span className="text-muted">Simulation core</span>
            <span className="text-violet">Experimental</span>
          </div>
          <div className="mt-1.5 flex items-center justify-between text-[12px]">
            <span className="text-muted">Raw data egress</span>
            <span className="text-mint">None</span>
          </div>
          <p className="mt-3 text-[11px] leading-relaxed text-dim">
            Data stay in the local record unless you explicitly export them.
          </p>
        </div>
      </div>

      <div className="border-t border-line p-3">
        {user && (
          <div className="flex items-center gap-3 px-1 py-1.5">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center border border-line bg-raised font-mono text-[11px] text-mist">
              {initials(user.name)}
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-[12px] text-mist">{user.name}</div>
              <div className="mt-0.5 flex items-center gap-1.5 text-[11px] text-dim">
                {user.is_demo ? <span className="text-amber">Demonstration</span> : <span>Member</span>}
                <span aria-hidden="true">/</span>
                <span>v0.1</span>
              </div>
            </div>
            <button
              onClick={handleLogout}
              aria-label="Sign out"
              title="Sign out"
              className="flex h-11 w-11 items-center justify-center text-dim transition-colors hover:text-mist"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        )}
        <Link
          href="/privacy"
          onClick={onNavigate}
          className="mt-1 flex min-h-9 items-center px-1 text-[12px] text-dim transition-colors hover:text-mist"
        >
          Private by design
        </Link>
      </div>
    </div>
  );
}

export function Sidebar({ mobileOpen, onClose }: { mobileOpen: boolean; onClose: () => void }) {
  useEffect(() => {
    if (!mobileOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [mobileOpen, onClose]);

  return (
    <>
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[248px] border-r border-line bg-ink lg:block">
        <SidebarContent />
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-[90] lg:hidden">
          <button
            onClick={onClose}
            className="absolute inset-0 bg-black/70"
            aria-label="Close menu"
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Navigation"
            className="relative h-full w-[280px] border-r border-line bg-ink"
          >
            <button
              onClick={onClose}
              aria-label="Close navigation"
              autoFocus
              className="absolute right-2 top-3 z-10 flex h-11 w-11 items-center justify-center text-dim hover:text-mist"
            >
              <X className="h-5 w-5" />
            </button>
            <SidebarContent onNavigate={onClose} />
          </div>
        </div>
      )}
    </>
  );
}
