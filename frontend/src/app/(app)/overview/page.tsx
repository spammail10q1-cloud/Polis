"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  BookOpen,
  FlaskConical,
  NotebookPen,
  Pill,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { BodyMap } from "@/components/body-map";
import { Sparkline } from "@/components/charts/sparkline";
import { Panel, PanelHeader, LoadError, Skeleton } from "@/components/ui/panel";
import { Badge, EvidenceBadge } from "@/components/ui/badge";
import { ProgressBar } from "@/components/ui/misc";
import { StatusPill, LiveDot } from "@/components/ui/status";
import { useQuery } from "@/lib/use-query";
import type { Overview, Trend } from "@/lib/types";
import { categoryLabel, cn, formatDate, formatNumber, formatRange, relativeTime, systemStatusLabel } from "@/lib/format";

const keyMarkers = [
  { code: "alt", label: "ALT" },
  { code: "ldl", label: "LDL-C" },
  { code: "egfr", label: "eGFR" },
  { code: "hs_crp", label: "hs-CRP" },
];

const shortSystemStatus: Record<string, string> = {
  available: "Available",
  review: "Review",
  partial: "Partial",
  missing: "Missing",
  experimental: "Experimental",
};

function markerTone(status: string): "amber" | "mint" | "signal" {
  if (status === "high" || status === "low") return "amber";
  if (status === "normal") return "mint";
  return "signal";
}

function systemText(status: string): string {
  if (status === "review") return "text-amber";
  if (status === "available") return "text-mint";
  if (status === "partial") return "text-signal";
  if (status === "experimental") return "text-violet";
  return "text-dim";
}

function systemDot(status: string): string {
  if (status === "review") return "bg-amber";
  if (status === "available") return "bg-mint";
  if (status === "partial") return "bg-signal";
  if (status === "experimental") return "bg-violet";
  return "bg-dim";
}

function progressTone(status: string): "signal" | "amber" | "violet" | "muted" {
  if (status === "review") return "amber";
  if (status === "experimental") return "violet";
  if (status === "available" || status === "partial") return "signal";
  return "muted";
}

export default function OverviewPage() {
  const router = useRouter();
  const { data, loading, error, refresh } = useQuery<Overview>("/overview");
  const [selectedSystem, setSelectedSystem] = useState<string | null>(null);

  if (loading && !data) return <OverviewSkeleton />;
  if (error && !data) return <LoadError message={error} onRetry={refresh} />;
  if (!data) return null;

  const latestByCode = new Map(data.latest_labs.map((lab) => [lab.code, lab]));
  const trendsByCode = new Map(data.trends.map((trend) => [trend.code, trend]));
  const sleep = data.wearables.summary.find((metric) => metric.metric === "sleep_duration");
  const changedTrends = data.trends
    .filter((trend) => trend.absolute_change !== null && trend.percent_change !== null)
    .sort((a, b) => Math.abs(b.percent_change ?? 0) - Math.abs(a.percent_change ?? 0))
    .slice(0, 5);

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow={`${formatDate(new Date().toISOString(), { weekday: "long" })} / ${data.user.is_demo ? "Demonstration twin" : "Personal twin"}`}
        title={`Welcome back, ${data.user.name.split(" ")[0]}.`}
        description={
          <>
            Your twin is assembled from {data.latest_labs.length} laboratory signals, {data.twin.systems.length}{" "}
            biological systems and {data.active_medications.length} recorded medications. No overall health score is
            calculated.
          </>
        }
        actions={
          <>
            <Link href="/assistant" className="btn btn-secondary">
              Ask POLIS
            </Link>
            <Link href="/what-if" className="btn btn-primary">
              Open What If?
            </Link>
          </>
        }
      />

      {data.latest_labs.length === 0 && (
        <Panel className="mb-4">
          <div className="flex flex-col items-start justify-between gap-4 p-5 sm:flex-row sm:items-center">
            <div>
              <div className="eyebrow mb-2">New biological record</div>
              <h2 className="display text-[22px] text-mist">Your twin needs its first measurements.</h2>
              <p className="mt-2 max-w-xl text-[13px] leading-relaxed text-muted">
                Add a laboratory result, import a report or upload a genetic panel. Nothing is inferred from population
                averages without being labelled, and missing information remains visible.
              </p>
            </div>
            <div className="flex shrink-0 gap-2">
              <Link href="/biomarkers" className="btn btn-secondary">
                Add laboratory data
              </Link>
              <Link href="/genetics" className="btn btn-primary">
                Genetics
              </Link>
            </div>
          </div>
        </Panel>
      )}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.42fr)_minmax(0,0.9fr)]">
        <Panel className="flex min-h-[610px] flex-col" emphasis>
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-3.5 sm:px-5">
            <div className="text-[13px] text-muted">Interactive biological twin</div>
            <Link
              href="/twin"
              className="inline-flex min-h-11 items-center text-[12px] text-signal transition-colors hover:text-mist lg:min-h-0"
            >
              Full twin
            </Link>
          </div>
          <div className="grid flex-1 grid-cols-1 lg:grid-cols-[minmax(0,1fr)_248px]">
            <div className="flex min-h-[500px] flex-col border-b border-line lg:border-b-0 lg:border-r">
              <BodyMap
                systems={data.twin.systems}
                selectedId={selectedSystem}
                onSelect={(id) => {
                  setSelectedSystem(id);
                  router.push(`/twin?system=${id}`);
                }}
                className="min-h-0 flex-1 px-2 py-1"
                compact
              />
            </div>
            <div className="flex min-h-0 flex-col">
              <div className="border-b border-line px-4 py-4">
                <div className="mono-label">Data completeness</div>
                <div className="mt-2 flex items-baseline gap-2">
                  <span className="number text-[32px] text-mist">{data.twin.overall_completeness}</span>
                  <span className="font-mono text-[12px] text-dim">%</span>
                </div>
                <ProgressBar value={data.twin.overall_completeness} className="mt-3" />
                <p className="mt-2.5 text-[12px] leading-relaxed text-dim">
                  Coverage of curated measurements. Not a health score.
                </p>
              </div>
              <div className="scroll-area min-h-0 flex-1 overflow-y-auto px-2 py-2">
                {data.twin.systems.map((system) => (
                  <button
                    key={system.id}
                    onClick={() => router.push(`/twin?system=${system.id}`)}
                    className="group flex min-h-11 w-full flex-col justify-center gap-0.5 px-2.5 py-2 text-left transition-colors hover:bg-raised/50"
                  >
                    <span className="flex w-full items-center gap-2">
                      <span
                        className={cn("h-1.5 w-1.5 shrink-0 rounded-full", systemDot(system.status))}
                        aria-hidden="true"
                      />
                      <span className="flex-1 truncate text-[13px] text-muted transition-colors group-hover:text-mist">
                        {system.name}
                      </span>
                      <span className="shrink-0 font-mono text-[11px] text-dim">{system.completeness}%</span>
                    </span>
                    <span className={cn("pl-[14px] text-[11px]", systemText(system.status))}>
                      {shortSystemStatus[system.status] ?? system.status}
                    </span>
                  </button>
                ))}
              </div>
              <div className="mt-auto border-t border-line px-4">
                <Link
                  href="/twin"
                  className="flex min-h-11 items-center text-[12px] text-dim transition-colors hover:text-signal"
                >
                  Inspect all systems
                </Link>
              </div>
            </div>
          </div>
        </Panel>

        <div className="flex flex-col gap-4">
          <Panel>
            <PanelHeader
              eyebrow="Biological overview"
              title="Signals in context"
              action={<Badge tone="muted">Latest available</Badge>}
            />
            <div className="grid grid-cols-2 gap-x-5 px-5">
              {keyMarkers.map((marker, index) => {
                const lab = latestByCode.get(marker.code);
                const trend = trendsByCode.get(marker.code);
                if (!lab) return null;
                return (
                  <Link
                    key={marker.code}
                    href={`/biomarkers?code=${marker.code}`}
                    className={cn(
                      "group py-4 transition-colors hover:bg-raised/40",
                      index < 2 && "border-b border-line",
                      index % 2 === 0 ? "pr-3" : "pl-3",
                    )}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="mono-label">{marker.label}</div>
                      <StatusPill status={lab.range_status} />
                    </div>
                    <div className="mt-2.5 flex items-baseline gap-1.5">
                      <span className="number text-[26px] text-mist">{formatNumber(lab.value, lab.value >= 100 ? 0 : 1)}</span>
                      <span className="font-mono text-[11px] text-dim">{lab.unit}</span>
                    </div>
                    <div className="mt-1 flex items-center justify-between gap-2">
                      <span className="font-mono text-[11px] text-dim">{formatRange(lab.ref_low, lab.ref_high)}</span>
                      {trend && trend.points.length > 1 && (
                        <span className="flex items-center gap-1 font-mono text-[11px] text-muted">
                          {(trend.absolute_change ?? 0) > 0 ? (
                            <TrendingUp className="h-3 w-3" aria-hidden="true" />
                          ) : (
                            <TrendingDown className="h-3 w-3" aria-hidden="true" />
                          )}
                          {Math.abs(trend.percent_change ?? 0).toFixed(1)}%
                        </span>
                      )}
                    </div>
                    <Sparkline
                      values={trend?.points.map((point) => point.value) ?? [lab.value]}
                      tone={markerTone(lab.range_status)}
                      height={24}
                      className="mt-2.5 opacity-80 transition-opacity group-hover:opacity-100"
                    />
                  </Link>
                );
              })}
            </div>
            {data.latest_labs.length === 0 && (
              <div className="border-t border-line px-5 py-6">
                <p className="text-[13px] leading-relaxed text-muted">
                  No laboratory measurements yet. The overview will populate as soon as you add a result.
                </p>
                <Link href="/biomarkers" className="btn btn-secondary mt-3">
                  Add a result
                </Link>
              </div>
            )}
            <div className="flex items-center justify-between gap-3 border-t border-line px-4 py-3">
              <LiveDot
                tone={sleep ? "signal" : "muted"}
                label={sleep ? `${sleep.average_14d.toFixed(1)} h sleep, 14-day average` : "No sleep data"}
              />
              <Link
                href="/biomarkers"
                className="inline-flex min-h-11 items-center text-[12px] text-dim transition-colors hover:text-mist lg:min-h-0"
              >
                All results
              </Link>
            </div>
          </Panel>

          <Panel emphasis>
            <div className="p-5">
              <div className="eyebrow mb-2.5">What If? / experimental workspace</div>
              <h2 className="display text-[24px] text-mist">How might your body handle a medicine?</h2>
              <p className="mt-2.5 text-[13px] leading-relaxed text-muted">
                POLIS weighs pharmacogenomics, liver and kidney markers, interactions and missing information. It never
                calculates a personalized dose.
              </p>
              <div className="mt-4 space-y-2">
                {data.suggested_simulations.length === 0 && (
                  <p className="border border-line px-3.5 py-3 text-[12px] leading-relaxed text-dim">
                    No personalized suggestions yet. Any simulation will label population assumptions and missing data.
                  </p>
                )}
                {data.suggested_simulations.slice(0, 2).map((suggestion) => (
                  <Link
                    key={suggestion.medication_id}
                    href={`/what-if?med=${suggestion.medication_id}`}
                    className="group flex items-center justify-between gap-3 border border-line px-3.5 py-3 transition-colors hover:border-dim/60 hover:bg-raised/40"
                  >
                    <span className="min-w-0">
                      <span className="block text-[13px] text-mist/90">{suggestion.label}</span>
                      <span className="mt-0.5 block text-[12px] leading-snug text-dim">{suggestion.reason}</span>
                    </span>
                    <span className="shrink-0 text-[11px] text-signal transition-colors group-hover:text-mist">Open</span>
                  </Link>
                ))}
              </div>
              <Link href="/what-if" className="btn btn-secondary mt-4 w-full">
                Open simulation workspace
              </Link>
            </div>
          </Panel>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.06fr)_minmax(0,0.72fr)]">
        <Panel>
          <PanelHeader
            eyebrow="Recent changes"
            title="Longitudinal signals"
            description="Changes are observations. They do not establish cause."
            action={
              <Link href="/biomarkers" className="inline-flex min-h-11 items-center text-[12px] text-dim hover:text-mist lg:min-h-0">
                View all
              </Link>
            }
          />
          <div className="divide-y divide-line">
            {changedTrends.map((trend) => (
              <TrendRow key={trend.code} trend={trend} />
            ))}
            {!changedTrends.length && (
              <div className="px-5 py-8 text-[13px] text-dim">
                Not enough repeated measurements to show a change.
              </div>
            )}
          </div>
        </Panel>

        <Panel>
          <PanelHeader
            eyebrow="Observations"
            title="What the evidence suggests"
            description="Separate from diagnosis and treatment recommendations."
            action={
              <Link href="/insights" className="inline-flex min-h-11 items-center text-[12px] text-dim hover:text-mist lg:min-h-0">
                All insights
              </Link>
            }
          />
          <div className="divide-y divide-line">
            {data.insights.slice(0, 3).map((insight) => (
              <Link
                key={insight.id}
                href="/insights"
                className="group block px-5 py-4 transition-colors hover:bg-raised/40"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-[13px] text-mist/90 transition-colors group-hover:text-mist">{insight.title}</h3>
                  <EvidenceBadge value={insight.sources.length ? "supporting_evidence" : "unknown"} />
                </div>
                <p className="mt-1.5 line-clamp-2 text-[13px] leading-relaxed text-muted">{insight.summary}</p>
                <div className="mt-2 flex items-center gap-2 text-[11px] text-dim">
                  <span>{categoryLabel(insight.category)}</span>
                  <span aria-hidden="true">/</span>
                  <span>
                    {insight.sources.length
                      ? `${insight.sources.length} source${insight.sources.length > 1 ? "s" : ""}`
                      : "data inventory"}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </Panel>

        <Panel>
          <PanelHeader
            eyebrow="Active regimen"
            title="Medications"
            action={
              <Link href="/medications" className="inline-flex min-h-11 items-center text-[12px] text-dim hover:text-mist lg:min-h-0">
                Manage
              </Link>
            }
          />
          <div className="divide-y divide-line">
            {data.active_medications.length === 0 && (
              <div className="px-5 py-7">
                <p className="text-[13px] leading-relaxed text-muted">
                  No active medications recorded. Interaction screening remains empty, not “safe”.
                </p>
                <Link
                  href="/medications"
                  className="mt-3 inline-flex min-h-11 items-center text-[12px] text-signal underline decoration-signal/30 underline-offset-4 hover:text-mist"
                >
                  Add a medication
                </Link>
              </div>
            )}
            {data.active_medications.slice(0, 4).map((medication) => (
              <div key={medication.id} className="flex items-center gap-3 px-5 py-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center border border-line bg-raised/60">
                  <Pill className="h-3.5 w-3.5 text-dim" aria-hidden="true" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[13px] text-mist/90">{medication.name}</div>
                  <div className="mt-0.5 font-mono text-[11px] text-dim">
                    {medication.dose_text}, {medication.frequency}
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="border-t border-line px-5 py-3">
            <div className="flex items-center justify-between gap-3 text-[11px]">
              <span className="text-dim">
                {data.active_medications.length} recorded{" "}
                {data.active_medications.length === 1 ? "entry" : "entries"}
              </span>
              <span className="text-amber">Review with a clinician</span>
            </div>
          </div>
        </Panel>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,0.8fr)]">
        <Panel>
          <PanelHeader
            eyebrow="Data completeness"
            title="Where the model can see, and where it cannot"
            description="Coverage is measured against curated system-specific data, not against a claim of health."
            action={<Badge tone="signal">{data.twin.overall_completeness}% overall</Badge>}
          />
          <div className="grid gap-x-8 gap-y-1 p-5 sm:grid-cols-2">
            {data.twin.systems.map((system) => (
              <Link key={system.id} href={`/twin?system=${system.id}`} className="group block py-2">
                <div className="flex items-center justify-between gap-3">
                  <span className="flex items-center gap-2 text-[13px] text-muted group-hover:text-mist">
                    <span
                      className={cn("h-1.5 w-1.5 shrink-0 rounded-full", systemDot(system.status))}
                      aria-hidden="true"
                    />
                    {system.name}
                  </span>
                  <span className="font-mono text-[11px] text-dim">{system.completeness}%</span>
                </div>
                <ProgressBar
                  value={system.completeness}
                  tone={progressTone(system.status)}
                  className="mt-2"
                />
                <div className={cn("mt-1.5 text-[11px]", systemText(system.status))}>
                  {systemStatusLabel(system.status)}
                </div>
              </Link>
            ))}
          </div>
        </Panel>

        <Panel className="flex flex-col">
          <PanelHeader eyebrow="Provenance" title="What this view is" />
          <div className="flex flex-1 flex-col justify-between p-5">
            <div className="space-y-3.5">
              <ProvenanceRow
                icon={FlaskConical}
                label="Laboratory"
                value={`${data.latest_labs.length} latest signals`}
                detail={
                  data.data_status.last_laboratory
                    ? relativeTime(data.data_status.last_laboratory)
                    : "No laboratory data"
                }
              />
              <ProvenanceRow
                icon={NotebookPen}
                label="Genetics"
                value={data.data_status.genetic_source ?? "Not available"}
                detail="Curated demonstration panel"
              />
              <ProvenanceRow
                icon={Pill}
                label="Medications"
                value={`${data.active_medications.length} active`}
                detail="User-reported, synthetic"
              />
              <ProvenanceRow
                icon={BookOpen}
                label="Wearables"
                value={data.data_status.wearable_ingestion}
                detail="Device estimates"
              />
            </div>
            <p className="mt-5 border-t border-line pt-3 text-[12px] leading-relaxed text-dim">
              POLIS separates established evidence, personal evidence, model estimates and unknowns. Nothing here is a
              diagnosis. Data are synthetic in this demonstration.
            </p>
          </div>
        </Panel>
      </div>
    </div>
  );
}

function TrendRow({ trend }: { trend: Trend }) {
  const change = trend.absolute_change ?? 0;
  const previous = trend.previous !== null ? formatNumber(trend.previous) : "No data";
  const latest = trend.latest !== null ? formatNumber(trend.latest) : "No data";
  const lastPoint = trend.points[trend.points.length - 1];
  const dateLabel = lastPoint?.date ? formatDate(lastPoint.date) : "No date";

  return (
    <Link
      href={`/biomarkers?code=${trend.code}`}
      className="group flex min-h-11 items-center gap-4 px-5 py-3.5 transition-colors hover:bg-raised/40"
    >
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[13px] text-mist/90">{trend.name}</span>
          <span className="font-mono text-[11px] text-dim">{trend.code.toUpperCase()}</span>
        </div>
        <div className="mt-1.5 flex flex-wrap items-center gap-x-1.5 gap-y-0.5 font-mono text-[11px] text-dim">
          <span>
            {previous} to {latest} {trend.unit}
          </span>
          <span aria-hidden="true">/</span>
          <span>{dateLabel}</span>
        </div>
      </div>
      <Sparkline
        values={trend.points.map((point) => point.value)}
        height={28}
        tone="signal"
        className="hidden w-[64px] shrink-0 sm:block"
      />
      <span className="w-16 shrink-0 text-right font-mono text-[11px] text-muted">
        {change > 0 ? "+" : ""}
        {formatNumber(change)} {trend.unit}
      </span>
    </Link>
  );
}

function ProvenanceRow({
  icon: Icon,
  label,
  value,
  detail,
}: {
  icon: typeof FlaskConical;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center border border-line bg-raised/50">
        <Icon className="h-3.5 w-3.5 text-dim" aria-hidden="true" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-[12px] text-muted">{label}</span>
          <span className="truncate text-right text-[12px] text-mist/90">{value}</span>
        </div>
        <div className="mt-0.5 text-right text-[11px] text-dim">{detail}</div>
      </div>
    </div>
  );
}

function OverviewSkeleton() {
  return (
    <div className="animate-fade-in">
      <Skeleton className="mb-3 h-3 w-48" />
      <Skeleton className="mb-3 h-10 w-[420px] max-w-full" />
      <Skeleton className="mb-8 h-4 w-[560px] max-w-full" />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.42fr_0.9fr]">
        <Skeleton className="min-h-[600px] w-full" />
        <div className="space-y-4">
          <Skeleton className="h-[340px] w-full" />
          <Skeleton className="h-[240px] w-full" />
        </div>
      </div>
    </div>
  );
}
