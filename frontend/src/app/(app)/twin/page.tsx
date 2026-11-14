"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { PageHeader } from "@/components/page-header";
import { BodyMap } from "@/components/body-map";
import { Panel, PanelHeader, PanelBody, LoadError, Skeleton } from "@/components/ui/panel";
import { Badge, EvidenceBadge } from "@/components/ui/badge";
import { Callout } from "@/components/ui/callout";
import { ProgressBar } from "@/components/ui/misc";
import { StatusPill } from "@/components/ui/status";
import { useQuery } from "@/lib/use-query";
import type { TwinOverview, TwinSystemDetail } from "@/lib/types";
import { cn, formatDate, formatNumber, formatRange, relativeTime, systemStatusLabel } from "@/lib/format";

function systemStatusTone(status: string) {
  if (status === "available") return "text-mint";
  if (status === "review" || status === "partial") return "text-amber";
  if (status === "experimental") return "text-violet";
  return "text-dim";
}

function TwinContent() {
  const router = useRouter();
  const params = useSearchParams();
  const requested = params.get("system");
  const { data, loading, error, refresh } = useQuery<TwinOverview>("/twin");
  const valid = data?.systems.some((system) => system.id === requested);
  const [selected, setSelected] = useState(valid ? requested! : "liver");

  useEffect(() => {
    if (data && requested && data.systems.some((system) => system.id === requested)) {
      setSelected(requested);
    }
  }, [data, requested]);

  const detail = useQuery<TwinSystemDetail>(`/twin/systems/${selected}`, { enabled: Boolean(data) });

  if (loading && !data) return <TwinSkeleton />;
  if (error && !data) return <LoadError message={error} onRetry={refresh} />;
  if (!data) return null;

  const choose = (id: string) => {
    setSelected(id);
    router.replace(`/twin?system=${id}`, { scroll: false });
  };

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Anatomical navigation, explanatory model"
        title="The digital body"
        description="Select a system to inspect its available measurements, genetic context, evidence quality and uncertainty. The illustration is a navigation interface, not a scan of your organs."
        actions={
          <>
            <Badge tone="neutral">{data.overall_completeness}% data coverage</Badge>
            <Link href="/what-if" className="btn btn-secondary">
              Explore an intervention
            </Link>
          </>
        }
      />

      <div className="mb-4 grid grid-cols-2 gap-px border border-line bg-line sm:grid-cols-4">
        <MiniStat label="Systems mapped" value="10" note="Curated starter model" />
        <MiniStat
          label="Last updated"
          value={data.last_updated ? relativeTime(data.last_updated) : "No data"}
          note="Across all signals"
        />
        <MiniStat
          label="Synthetic data"
          value={data.synthetic_data ? "Yes" : "No"}
          note="Demonstration profile"
          tone={data.synthetic_data ? "amber" : "mint"}
        />
        <MiniStat label="Health score" value="None" note="By design" tone="muted" />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,0.82fr)_minmax(0,1.25fr)]">
        <Panel className="self-start overflow-hidden xl:sticky xl:top-[72px]">
          <PanelHeader
            eyebrow="Anterior projection"
            title="Select a physiological system"
            action={<span className="text-[12px] text-dim">Navigation only</span>}
          />
          <BodyMap
            systems={data.systems}
            selectedId={selected}
            onSelect={choose}
            className="h-[560px] px-2"
          />
          <div className="grid grid-cols-1 gap-px bg-line sm:grid-cols-2">
            {data.systems.map((system) => {
              const active = selected === system.id;
              return (
                <button
                  key={system.id}
                  onClick={() => choose(system.id)}
                  aria-pressed={active}
                  className={cn(
                    "relative min-h-11 px-4 py-2.5 text-left transition-colors",
                    active ? "bg-raised" : "bg-panel hover:bg-raised/50",
                  )}
                >
                  {active && <span className="absolute inset-y-0 left-0 w-0.5 bg-signal" aria-hidden="true" />}
                  <span className="flex items-baseline justify-between gap-3">
                    <span className={cn("truncate text-[13px]", active ? "text-mist" : "text-muted")}>{system.name}</span>
                    <span className="shrink-0 font-mono text-[11px] text-dim">{system.completeness}%</span>
                  </span>
                  <span className={cn("mt-0.5 block text-[11px]", systemStatusTone(system.status))}>
                    {systemStatusLabel(system.status)}
                  </span>
                </button>
              );
            })}
          </div>
        </Panel>

        <div className="space-y-4">
          {detail.loading && !detail.data ? (
            <Skeleton className="h-[420px] w-full" />
          ) : detail.error ? (
            <LoadError message={detail.error} onRetry={detail.refresh} />
          ) : detail.data ? (
            <SystemDetail detail={detail.data} overview={data} onSelect={choose} />
          ) : null}
        </div>
      </div>

      <Callout tone="warning" title="Interpretation boundary" className="mt-4">
        {data.disclaimer} Status reflects data availability and whether values fall outside the reporting laboratory's
        interval. An organ is never classified as diseased from these signals.
      </Callout>
    </div>
  );
}

function SystemDetail({
  detail,
  overview,
  onSelect,
}: {
  detail: TwinSystemDetail;
  overview: TwinOverview;
  onSelect: (id: string) => void;
}) {
  return (
    <>
      <Panel emphasis>
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line px-5 py-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="mono-label">Selected system</span>
              <StatusPill status={detail.status} />
            </div>
            <h2 className="mt-2 font-display text-[28px] leading-tight text-mist">{detail.name}</h2>
            <p className="mt-1 text-[13px] text-muted">{detail.tagline}</p>
          </div>
          <div className="w-full min-w-[160px] sm:w-[170px]">
            <div className="flex items-baseline justify-between">
              <span className="mono-label">Coverage</span>
              <span className="font-mono text-[12px] text-mist">{detail.completeness}%</span>
            </div>
            <ProgressBar
              value={detail.completeness}
              className="mt-2"
              tone={detail.status === "review" ? "amber" : "signal"}
            />
            <div className="mt-2 text-[11px] text-dim">
              {detail.measurements_detail.length
                ? `${detail.measurements} of ${detail.measurements_detail.length} curated signals`
                : "No curated signals"}
            </div>
          </div>
        </div>
        <div className="px-5 py-4">
          <p className="text-[13px] leading-relaxed text-muted">{detail.description}</p>
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {detail.signals.map((signal, index) => (
              <div key={`${signal.label}-${index}`} className="border border-line bg-ink px-3 py-2.5">
                <div className="flex items-start justify-between gap-2">
                  <span className="font-mono text-[11px] text-dim">{signal.label}</span>
                  <StatusPill status={signal.status} />
                </div>
                <div className="mt-1.5 text-[14px] text-mist">{signal.value}</div>
                {signal.meta && (
                  <div className="mt-1 text-[11px] leading-relaxed text-dim">
                    {signal.meta.replaceAll(" · ", ", ")}
                  </div>
                )}
              </div>
            ))}
          </div>
          {!detail.signals.length && (
            <div className="mt-3 border border-dashed border-line px-4 py-5 text-[12px] text-dim">
              No directly relevant measurements are available for this system.
            </div>
          )}
        </div>
      </Panel>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Panel>
          <PanelHeader
            eyebrow="Measurement detail"
            title="Available signals"
            description="Lab intervals stay with the result that supplied them."
          />
          <div className="divide-y divide-line">
            {detail.measurements_detail.map((measurement) => (
              <div key={`${measurement.kind}-${measurement.code}`} className="flex items-start gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="truncate text-[13px] text-mist">{measurement.name}</span>
                    <span className="text-[11px] text-dim">
                      {measurement.kind === "wearable" ? "Wearable" : "Laboratory"}
                    </span>
                    <StatusPill status={measurement.status} />
                  </div>
                  <div className="mt-1 font-mono text-[11px] text-dim">
                    {measurement.date
                      ? `${formatDate(measurement.date)}${measurement.source ? `, ${measurement.source}` : ""}`
                      : measurement.label.replaceAll(" · ", ", ")}
                  </div>
                </div>
                <div className="shrink-0 text-right">
                  <div className="font-mono text-[13px] text-mist">
                    {measurement.value !== null
                      ? `${formatNumber(measurement.value)} ${measurement.unit ?? ""}`
                      : "No data"}
                  </div>
                  <div className="mt-0.5 font-mono text-[11px] text-dim">
                    {measurement.ref_low !== undefined
                      ? formatRange(measurement.ref_low ?? null, measurement.ref_high ?? null)
                      : measurement.label.replaceAll(" · ", ", ")}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Panel>

        <div className="space-y-4">
          <Panel>
            <PanelHeader eyebrow="Personal evidence" title="Genetic factors" />
            <div className="divide-y divide-line">
              {detail.genetic_factors.map((factor) => (
                <div key={factor.gene} className="px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[12px] text-mist">{factor.gene}</span>
                    <Badge tone={factor.is_synthetic ? "amber" : "neutral"}>
                      {factor.is_synthetic ? "Synthetic" : "Uploaded"}
                    </Badge>
                  </div>
                  <dl className="mt-2 grid grid-cols-[76px_minmax(0,1fr)] gap-x-2 gap-y-1">
                    <dt className="text-[11px] text-dim">Diplotype</dt>
                    <dd className="font-mono text-[12px] text-muted">{factor.diplotype}</dd>
                    <dt className="text-[11px] text-dim">Phenotype</dt>
                    <dd className="text-[12px] text-mist">{factor.phenotype}</dd>
                  </dl>
                  <div className="mt-2 text-[11px] leading-relaxed text-dim">{factor.limitations}</div>
                </div>
              ))}
              {!detail.genetic_factors.length && (
                <div className="px-4 py-5 text-[12px] text-dim">No curated phenotype intersects this system.</div>
              )}
            </div>
          </Panel>

          <Panel>
            <PanelHeader eyebrow="Context" title="Risk factors and limitations" />
            <div className="px-4 py-3">
              {detail.risk_factors.length ? (
                <ul className="list-disc space-y-1.5 pl-4 marker:text-amber/70">
                  {detail.risk_factors.map((factor) => (
                    <li key={factor} className="text-[12px] leading-relaxed text-muted">
                      {factor}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-[12px] text-dim">No self-reported condition is mapped to this system.</p>
              )}
              <div className="mt-3 border-t border-line pt-3">
                {detail.limitations.map((limitation) => (
                  <p key={limitation} className="mb-1.5 text-[11px] leading-relaxed text-dim last:mb-0">
                    {limitation}
                  </p>
                ))}
              </div>
            </div>
          </Panel>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Panel>
          <PanelHeader
            eyebrow="Evidence quality"
            title="What supports this view"
            action={<EvidenceBadge value="supporting_evidence" />}
          />
          <PanelBody className="space-y-3">
            <p className="text-[13px] leading-relaxed text-muted">{detail.evidence_quality}</p>
            <div className="flex flex-wrap gap-1.5">
              {detail.pathways.map((pathway) => (
                <Badge key={pathway} tone="muted">
                  {pathway.replaceAll("-", " ")}
                </Badge>
              ))}
            </div>
            <div className="border-t border-line pt-3">
              <div className="mono-label mb-2">Connected systems</div>
              <div className="flex flex-wrap gap-1.5">
                {detail.connected_systems.map((system) => {
                  const target = overview.systems.find((item) => item.name === system);
                  return target ? (
                    <button
                      key={system}
                      onClick={() => onSelect(target.id)}
                      className="chip min-h-11 hover:border-muted/40 hover:text-mist sm:min-h-8"
                    >
                      {system}
                    </button>
                  ) : (
                    <span key={system} className="chip">
                      {system}
                    </span>
                  );
                })}
              </div>
            </div>
          </PanelBody>
        </Panel>

        <Panel>
          <PanelHeader eyebrow="Uncertainty" title="What cannot be concluded" />
          <PanelBody>
            <p className="text-[13px] leading-relaxed text-muted">{detail.uncertainty}</p>
            <Callout tone="info" className="mt-3">
              POLIS never converts a status into a diagnosis. Discuss abnormal results with a qualified clinician, in
              the context of symptoms, examination and additional testing.
            </Callout>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link href="/biomarkers" className="btn btn-secondary">
                Inspect biomarkers
              </Link>
              <Link href="/what-if" className="btn btn-ghost">
                Consider an intervention
              </Link>
            </div>
          </PanelBody>
        </Panel>
      </div>
    </>
  );
}

function MiniStat({
  label,
  value,
  note,
  tone = "default",
}: {
  label: string;
  value: string;
  note: string;
  tone?: "default" | "amber" | "mint" | "muted";
}) {
  return (
    <div className="bg-panel px-4 py-3">
      <div className="mono-label">{label}</div>
      <div
        className={cn(
          "mt-1.5 text-[14px] text-mist",
          tone === "amber" && "text-amber",
          tone === "mint" && "text-mint",
          tone === "muted" && "text-muted",
        )}
      >
        {value}
      </div>
      <div className="mt-0.5 text-[11px] text-dim">{note}</div>
    </div>
  );
}

function TwinSkeleton() {
  return (
    <div>
      <Skeleton className="mb-3 h-3 w-48" />
      <Skeleton className="mb-8 h-10 w-[340px]" />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[0.82fr_1.25fr]">
        <Skeleton className="h-[660px] w-full" />
        <Skeleton className="h-[500px] w-full" />
      </div>
    </div>
  );
}

export default function TwinPage() {
  return (
    <Suspense fallback={<TwinSkeleton />}>
      <TwinContent />
    </Suspense>
  );
}
