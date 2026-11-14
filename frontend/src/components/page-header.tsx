import { cn } from "@/lib/format";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  className,
}: {
  eyebrow: string;
  title: string;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mb-8 flex flex-col justify-between gap-5 sm:flex-row sm:items-end", className)}>
      <div className="max-w-3xl">
        <div className="eyebrow mb-2.5">{eyebrow}</div>
        <h1 className="display text-[34px] text-mist sm:text-[46px]">{title}</h1>
        {description && <p className="mt-3 max-w-2xl text-[14px] leading-relaxed text-muted">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
