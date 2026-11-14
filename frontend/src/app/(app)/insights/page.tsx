"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { BookOpen, ChevronDown, Play, ShieldQuestion } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Panel, PanelHeader, PanelBody, LoadError, Skeleton } from "@/components/ui/panel";
import { Badge, EvidenceBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { Tabs } from "@/components/ui/misc";
import { useToast } from "@/components/toast";
import { apiPost, errorMessage } from "@/lib/api";
import { useQuery } from "@/lib/use-query";
import type { CausalCatalog, CausalResult, Insight, Overview } from "@/lib/types";
import { cn } from "@/lib/format";

const filters = ["All", "Liver", "Cardiovascular", "Pharmacogenomics", "Kidneys", "Sleep & recovery", "Data quality"];

export default function InsightsPage() {
  const { data, loading, error, refresh } = useQuery<Overview>("/overview");
  const [filter, setFilter] = useState("All");
  const [view, setView] = useState<"observations" | "causal">("observations");

  const insights = useMemo(() => {
    const list = data?.insights ?? [];
    return filter === "All" ? list : list.filter((insight) => insight.category === filter);
  }, [data, filter]);

  const categoryCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const insight of data?.insights ?? []) {
      counts.set(insight.category, (counts.get(insight.category) ?? 0) + 1);
    }
    return counts;
  }, [data]);

  if (loading && !data) return <InsightSkeleton />;
  if (error && !data) return <LoadError message={error} onRetry={refresh} />;
  if (!data) return null;

  const warningCount = data.insights.filter((insight) => insight.tone === "warning").length;
  const evidenceCount = new Set(data.insights.flatMap((insight) => insight.sources.map((source) => source.id))).size;

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Evidence-linked observations"
        title="Insights"
        description="What the available data suggest, what they do not, and which sources support the interpretation. These are observations, not diagnoses or treatment recommendations."
        actions={
          <>
            <Badge tone={warningCount > 0 ? "amber" : "muted"}>{warningCount} review observations</Badge>
            <Link href="/assistant" className="btn btn-secondary">
              Ask about an insight
            </Link>
          </>
        }
      />

      <Tabs
        value={view}
        onChange={setView}
        items={[
          { value: "observations", label: "Evidence observations", count: data.insights.length },
          { value: "causal", label: "Causal lab" },
        ]}
        className="mb-4"
      />

      {view === "causal" ? (
        <CausalLab />
      ) : (
        <>
          <div className="mb-4 grid grid-cols-2 gap-px overflow-hidden rounded-[2px] border border-line bg-line sm:grid-cols-4">
            <InsightStat label="Observations" value={String(data.insights.length)} note="Generated from current data" />
            <InsightStat label="Review signals" value={String(warningCount)} note="Not diagnoses" tone="amber" />
            <InsightStat label="Unique sources" value={String(evidenceCount)} note="Versioned evidence" tone="signal" />
            <InsightStat label="Overall score" value="None" note="By design" tone="muted" />
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.55fr)_minmax(300px,0.58fr)]">
            <div>
              <div className="mb-3 flex flex-wrap items-center gap-1" role="group" aria-label="Filter observations by category">
                {filters.map((item) => {
                  const count = item === "All" ? data.insights.length : categoryCounts.get(item) ?? 0;
                  const active = filter === item;
                  return (
                    <button
                      key={item}
                      onClick={() => setFilter(item)}
                      aria-pressed={active}
                      className={cn(
                        "flex min-h-9 items-center gap-1.5 rounded-[2px] border px-2.5 py-1.5 text-[12px] transition-colors",
                        active
                          ? "border-signal/40 bg-signal/[0.06] text-signal"
                          : "border-transparent text-muted hover:border-line hover:text-mist",
                      )}
                    >
                      {item}
                      <span className={cn("font-mono text-[11px]", active ? "text-signal/70" : "text-dim")}>{count}</span>
                    </button>
                  );
                })}
              </div>

              <div className="space-y-3">
                {insights.map((insight, index) => (
                  <InsightCard key={insight.id} insight={insight} index={index + 1} />
                ))}
                {!insights.length && (
                  <Panel>
                    <div className="px-6 py-14 text-center text-[13px] text-dim">No observations in this category.</div>
                  </Panel>
                )}
              </div>
            </div>

            <div className="space-y-4">
              <Panel>
                <PanelHeader
                  eyebrow="How to read this"
                  title="Evidence is not a diagnosis"
                  action={<ShieldQuestion className="h-4 w-4 text-amber/80" aria-hidden="true" />}
                />
                <ol className="space-y-3 p-4">
                  {[
                    "Observations are generated from synthetic demonstration data, not a real person.",
                    "An out-of-range value or a trend does not establish a cause.",
                    "Citations support the general interpretation, not a recommendation for you.",
                    "Missing data reduce what can be concluded and are shown explicitly.",
                    "A conversation with your clinician is the appropriate next step for any concern.",
                  ].map((text, index) => (
                    <li key={text} className="flex gap-3">
                      <span className="mt-0.5 shrink-0 font-mono text-[11px] text-dim">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                      <p className="text-[13px] leading-relaxed text-muted">{text}</p>
                    </li>
                  ))}
                </ol>
              </Panel>

              <Panel>
                <PanelHeader eyebrow="Review signals" title="Most important to discuss" />
                <div className="divide-y divide-line">
                  {data.insights
                    .filter((insight) => insight.tone === "warning")
                    .slice(0, 3)
                    .map((insight) => (
                      <div key={insight.id} className="px-4 py-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge tone="amber">Review</Badge>
                          <span className="text-[13px] leading-snug text-mist">{insight.title}</span>
                        </div>
                        <p className="mt-1.5 text-[12px] leading-relaxed text-dim">{insight.summary}</p>
                      </div>
                    ))}
                  {!data.insights.some((insight) => insight.tone === "warning") && (
                    <p className="px-4 py-4 text-[12px] leading-relaxed text-dim">
                      No review signals in the current data. The full list of observations remains above.
                    </p>
                  )}
                </div>
                <div className="border-t border-line px-4">
                  <Link
                    href="/biomarkers"
                    className="link-underline inline-flex min-h-10 items-center text-[12px] text-muted hover:text-mist"
                  >
                    Inspect the underlying results
                  </Link>
                </div>
              </Panel>

              <Callout tone="violet" title="A question worth exploring">
                <p>
                  Bring an observation into What If? to see how a medicine's mechanism connects to your liver, kidney and
                  pharmacogenomic context.
                </p>
                <Link href="/what-if" className="btn btn-secondary mt-3 w-full">
                  Open What If?
                </Link>
              </Callout>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function CausalLab() {
  const { push } = useToast();
  const catalog = useQuery<CausalCatalog>("/causal/catalog");
  const [treatment, setTreatment] = useState("sleep_duration");
  const [outcome, setOutcome] = useState("hrv");
  const [delta, setDelta] = useState(0.5);
  const [result, setResult] = useState<CausalResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const treatmentSpec = catalog.data?.treatments.find((item) => item.code === treatment);
  const outcomeSpec = catalog.data?.outcomes.find((item) => item.code === outcome);

  const chooseTreatment = (code: string) => {
    setTreatment(code);
    const spec = catalog.data?.treatments.find((item) => item.code === code);
    setDelta(spec?.default_delta ?? 0);
    setResult(null);
    setError(null);
  };

  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      const response = await apiPost<CausalResult>("/causal/simulate", { treatment, outcome, delta });
      setResult(response);
      if (response.status === "insufficient_data") {
        push("Not enough complete wearable days for a stable exploratory estimate.", "info");
      }
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setRunning(false);
    }
  };

  if (catalog.loading && !catalog.data) {
    return <Skeleton className="h-[520px] w-full" />;
  }
  if (catalog.error && !catalog.data) {
    return <LoadError message={catalog.error} onRetry={catalog.refresh} />;
  }
  if (!catalog.data) return null;

  return (
    <div className="space-y-4">
      <Callout tone="warning" title="A hypothesis laboratory, not a causal oracle">
        {catalog.data.disclaimer} This model assumes a linear form and no unmeasured confounding. It is built on
        complete same-day wearable estimates from one person. The estimate is a model-dependent counterfactual, not a
        discovered causal effect.
      </Callout>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(280px,0.72fr)_minmax(0,1.28fr)]">
        <Panel className="self-start">
          <PanelHeader eyebrow="Intervention studio" title="Ask a do-operator question" />
          <div className="space-y-4 p-4">
            <label className="block">
              <span className="mb-2 block text-[12px] text-muted">Treatment</span>
              <select className="input" value={treatment} onChange={(event) => chooseTreatment(event.target.value)}>
                {catalog.data.treatments.map((item) => (
                  <option key={item.code} value={item.code}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-2 block text-[12px] text-muted">Hypothetical change</span>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  className="input"
                  step={treatmentSpec?.delta_step ?? 0.25}
                  min={treatmentSpec?.min_delta}
                  max={treatmentSpec?.max_delta}
                  value={delta}
                  onChange={(event) => {
                    setDelta(Number(event.target.value));
                    setResult(null);
                  }}
                />
                <span className="chip">{treatmentSpec?.unit ?? ""}</span>
              </div>
              <div className="mt-2 flex flex-wrap gap-1">
                {[
                  -(treatmentSpec?.default_delta ?? 0),
                  -(treatmentSpec?.default_delta ?? 0) / 2,
                  (treatmentSpec?.default_delta ?? 0) / 2,
                  treatmentSpec?.default_delta ?? 0,
                ].map((preset) => (
                  <button
                    key={preset}
                    onClick={() => {
                      setDelta(Number(preset.toFixed(2)));
                      setResult(null);
                    }}
                    className="chip min-h-9 transition-colors hover:border-muted/50 hover:text-mist"
                  >
                    {preset > 0 ? "+" : ""}
                    {Number(preset.toFixed(2))} {treatmentSpec?.unit}
                  </button>
                ))}
              </div>
            </label>
            <div>
              <span className="mb-2 block text-[12px] text-muted">Outcome</span>
              <div className="grid grid-cols-2 gap-2">
                {catalog.data.outcomes.map((item) => (
                  <button
                    key={item.code}
                    onClick={() => {
                      setOutcome(item.code);
                      setResult(null);
                    }}
                    aria-pressed={outcome === item.code}
                    className={cn(
                      "rounded-[2px] border px-2.5 py-2 text-left transition-colors",
                      outcome === item.code
                        ? "border-signal/60 bg-signal/[0.08]"
                        : "border-line hover:border-muted/40",
                    )}
                  >
                    <div className="text-[12px] text-mist">{item.label}</div>
                    <div className="mt-0.5 font-mono text-[11px] text-dim">{item.unit}</div>
                  </button>
                ))}
              </div>
            </div>
            <div className="rounded-[2px] border border-violet/20 bg-violet/[0.03] px-3 py-2.5">
              <div className="font-mono text-[11px] text-violet">do-operator</div>
              <div className="mt-1 font-mono text-[12px] leading-relaxed text-mist">
                do({treatment} = observed + {delta} {treatmentSpec?.unit})
              </div>
              <div className="mt-1 text-[11px] leading-relaxed text-dim">
                The measured confounder is held at its observed value.
              </div>
            </div>
            <Button onClick={run} loading={running} variant="primary" className="w-full" disabled={catalog.data.outcomes.length === 0}>
              <Play className="h-3.5 w-3.5" aria-hidden="true" /> Run exploratory model
            </Button>
            {error && (
              <Callout tone="danger" title="Request rejected">
                {error}
              </Callout>
            )}
          </div>
        </Panel>

        <div className="space-y-4">
          {!result ? (
            <Panel className="min-h-[430px]">
              <div className="flex min-h-[430px] flex-col justify-center px-6 py-10 sm:px-10">
                <p className="mono-label">No model run yet</p>
                <h2 className="mt-3 max-w-lg font-display text-[25px] leading-tight text-mist">
                  Correlation is not permission to intervene.
                </h2>
                <p className="mt-3 max-w-lg text-[13px] leading-relaxed text-muted">
                  This lab makes the assumptions behind a counterfactual explicit. It can show what a model would say
                  under those assumptions, not what your body will do.
                </p>
                <dl className="mt-6 grid w-full max-w-lg grid-cols-1 gap-px overflow-hidden rounded-[2px] border border-line bg-line sm:grid-cols-3">
                  {[
                    ["DAG", "explicit structure"],
                    ["do-operator", "hypothetical shift"],
                    ["interval", "bootstrap uncertainty"],
                  ].map(([label, detail]) => (
                    <div key={label} className="bg-panel px-3 py-3">
                      <dt className="font-mono text-[12px] text-mist">{label}</dt>
                      <dd className="mt-1 text-[11px] leading-relaxed text-dim">{detail}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            </Panel>
          ) : result.status === "insufficient_data" ? (
            <Panel>
              <PanelHeader
                eyebrow="Structured result"
                title="Not enough observational data"
                action={<Badge tone="amber">No estimate</Badge>}
              />
              <div className="p-5">
                <p className="text-[13px] leading-relaxed text-muted">{result.reason}</p>
                <ul className="mt-4 space-y-2">
                  {(result.missing_information ?? []).map((item) => (
                    <li key={item} className="flex items-start gap-2.5 text-[12px] leading-relaxed text-dim">
                      <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-amber/70" aria-hidden="true" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </Panel>
          ) : (
            <>
              <Panel emphasis>
                <PanelHeader
                  eyebrow="Counterfactual estimate"
                  title={`Change ${treatmentSpec?.label.toLowerCase()} by ${delta > 0 ? "+" : ""}${delta} ${treatmentSpec?.unit}`}
                  action={<EvidenceBadge value="experimental_hypothesis" />}
                />
                <div className="p-5">
                  <div className="flex flex-wrap items-end justify-between gap-4 border-b border-line pb-4">
                    <div>
                      <div className="flex items-baseline gap-2">
                        <span className="number text-[42px] leading-none text-mist">
                          {result.estimate?.value !== undefined
                            ? `${result.estimate.value > 0 ? "+" : ""}${result.estimate.value}`
                            : "n/a"}
                        </span>
                        <span className="font-mono text-[11px] text-dim">{result.estimate?.unit}</span>
                      </div>
                      <div className="mt-2 font-mono text-[11px] text-violet">
                        5th to 95th percentile interval {result.estimate?.low} to {result.estimate?.high}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="mono-label">Sample</div>
                      <div className="mt-1 text-[14px] text-mist">{result.model?.n_days} complete days</div>
                      <div className="mt-0.5 font-mono text-[11px] text-dim">R² {result.model?.r_squared}</div>
                    </div>
                  </div>
                  <p className="mt-3 text-[13px] leading-relaxed text-muted">
                    Under the stated model, the intervention is associated with a modeled{" "}
                    <span className="text-mist">{result.estimate?.direction}</span> in {result.outcome?.label.toLowerCase()}.
                    This is not a prediction of what will happen and not evidence that changing sleep or steps causes
                    this outcome.
                  </p>

                  <div className="mt-5 border border-line bg-ink p-3">
                    <div className="mono-label mb-2">Directed acyclic graph used by this query</div>
                    <CausalDag result={result} />
                  </div>

                  {result.points && result.points.length > 0 && result.model && (
                    <div className="mt-4 border border-line bg-ink">
                      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-3 py-2">
                        <span className="text-[12px] text-muted">Observed same-day pairs</span>
                        <span className="font-mono text-[11px] text-dim">
                          {result.points.length} of {result.available_days} days shown
                        </span>
                      </div>
                      <CausalScatter result={result} />
                    </div>
                  )}

                  {result.evidence && result.evidence.length > 0 && (
                    <div className="mt-4 space-y-2">
                      {result.evidence.map((source) => (
                        <a
                          key={source.id}
                          href={source.url}
                          target="_blank"
                          rel="noreferrer noopener"
                          className="flex items-start gap-2.5 rounded-[2px] border border-line bg-ink px-3 py-2.5 transition-colors hover:border-muted/40"
                        >
                          <BookOpen className="mt-0.5 h-3.5 w-3.5 shrink-0 text-signal/80" aria-hidden="true" />
                          <span className="min-w-0 flex-1">
                            <span className="block text-[12px] leading-snug text-mist">{source.title}</span>
                            <span className="mt-0.5 block font-mono text-[11px] text-dim">
                              {source.organization} · {source.published_at}
                            </span>
                          </span>
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              </Panel>

              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <Panel>
                  <PanelHeader eyebrow="Model equation" title="What was estimated" />
                  <PanelBody>
                    <pre className="overflow-x-auto whitespace-pre-wrap rounded-[2px] border border-line bg-ink p-3 font-mono text-[12px] leading-relaxed text-mist">
                      {result.model?.equation}
                    </pre>
                    <p className="mt-3 text-[12px] leading-relaxed text-dim">
                      {result.estimate?.interval_definition} Coefficient:{" "}
                      <span className="font-mono text-muted">{result.model?.coefficient}</span>
                      {result.model?.confounder_coefficient !== undefined
                        ? ` · confounder coefficient: ${result.model.confounder_coefficient}`
                        : ""}
                    </p>
                  </PanelBody>
                </Panel>
                <Panel>
                  <PanelHeader
                    eyebrow="Model assumptions"
                    title="What must be true"
                    action={<Badge tone="amber">Strong assumptions</Badge>}
                  />
                  <div className="max-h-[280px] overflow-y-auto px-4 py-3">
                    <ul className="space-y-2.5">
                      {(result.assumptions ?? []).map((item) => (
                        <li key={item} className="flex items-start gap-2.5 text-[12px] leading-relaxed text-muted">
                          <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-amber/60" aria-hidden="true" />
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                </Panel>
              </div>

              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <Panel>
                  <PanelHeader eyebrow="Limitations" title="Why this is not causal proof" />
                  <div className="px-4 py-3">
                    <ul className="space-y-2.5">
                      {(result.limitations ?? []).map((item) => (
                        <li key={item} className="flex items-start gap-2.5 text-[12px] leading-relaxed text-dim">
                          <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-amber/50" aria-hidden="true" />
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                </Panel>
                <Panel>
                  <PanelHeader eyebrow="Alternative explanations" title="What else could explain it" />
                  <div className="px-4 py-3">
                    <ul className="space-y-2.5">
                      {(result.alternative_explanations ?? []).map((item) => (
                        <li key={item} className="flex items-start gap-2.5 text-[12px] leading-relaxed text-dim">
                          <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-signal/60" aria-hidden="true" />
                          {item}
                        </li>
                      ))}
                    </ul>
                    <p className="mt-3 border-t border-line pt-3 text-[11px] leading-relaxed text-dim">
                      {result.disclaimer}
                    </p>
                  </div>
                </Panel>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function CausalDag({ result }: { result: CausalResult }) {
  const nodes = result.dag?.nodes ?? [];
  return (
    <div className="overflow-x-auto">
      <div className="flex min-w-[520px] items-stretch justify-between gap-3">
        <div className="w-[140px] rounded-[2px] border border-signal/25 bg-signal/[0.04] px-3 py-2.5">
          <div className="font-mono text-[11px] text-signal">Treatment</div>
          <div className="mt-1 text-[13px] leading-snug text-mist">
            {nodes.find((node) => node.role === "treatment")?.label}
          </div>
        </div>
        <div className="flex flex-1 flex-col items-center justify-center">
          <span className="font-mono text-[11px] text-dim">modeled effect</span>
          <div className="mt-1.5 flex w-full items-center">
            <span className="h-px flex-1 bg-violet/40" />
            <span className="-ml-px h-1.5 w-1.5 rotate-45 border-r border-t border-violet/60" aria-hidden="true" />
          </div>
        </div>
        <div className="w-[150px] rounded-[2px] border border-violet/25 bg-violet/[0.04] px-3 py-2.5">
          <div className="font-mono text-[11px] text-violet">Outcome</div>
          <div className="mt-1 text-[13px] leading-snug text-mist">
            {nodes.find((node) => node.role === "outcome")?.label}
          </div>
        </div>
        <div className="w-[140px] rounded-[2px] border border-dashed border-amber/30 bg-amber/[0.02] px-3 py-2.5">
          <div className="font-mono text-[11px] text-amber">Unmeasured</div>
          <div className="mt-1 text-[12px] leading-snug text-muted">assumed not confounding</div>
        </div>
      </div>
      <div className="mt-3 font-mono text-[11px] leading-relaxed text-dim">
        Measured confounder adjusted:{" "}
        {(result.dag?.nodes.find((node) => node.role === "confounder")?.label ?? "not recorded").toLowerCase()}. Edges
        are assumptions, not discoveries.
      </div>
    </div>
  );
}

function CausalScatter({ result }: { result: CausalResult }) {
  const points = result.points ?? [];
  if (!points.length || !result.model) return null;
  const width = 620;
  const height = 240;
  const padding = 40;
  const xs = points.map((point) => point.treatment);
  const ys = points.map((point) => point.outcome);
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  const yMin = Math.min(...ys);
  const yMax = Math.max(...ys);
  const xRange = xMax - xMin || 1;
  const yRange = yMax - yMin || 1;
  const xScale = (value: number) => padding + ((value - xMin) / xRange) * (width - padding * 2);
  const yScale = (value: number) => height - padding - ((value - yMin) / yRange) * (height - padding * 2);
  const lineY1 = result.model.intercept + result.model.coefficient * xMin;
  const lineY2 = result.model.intercept + result.model.coefficient * xMax;
  return (
    <div className="overflow-x-auto px-3 py-3">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-[240px] w-full min-w-[620px]"
        role="img"
        aria-label="Scatter plot of observed treatment and outcome pairs with fitted linear slope"
      >
        {[0, 0.25, 0.5, 0.75, 1].map((fraction) => (
          <line
            key={fraction}
            x1={padding}
            x2={width - padding}
            y1={padding + fraction * (height - padding * 2)}
            y2={padding + fraction * (height - padding * 2)}
            stroke="#2a312b"
          />
        ))}
        <line
          x1={xScale(xMin)}
          y1={yScale(lineY1)}
          x2={xScale(xMax)}
          y2={yScale(lineY2)}
          stroke="#bba9e8"
          strokeWidth={1.6}
        />
        {points.map((point) => (
          <circle
            key={point.date}
            cx={xScale(point.treatment)}
            cy={yScale(point.outcome)}
            r={2.4}
            fill="rgba(125,222,214,0.55)"
          />
        ))}
        <text x={padding} y={height - 12} fill="#8d968a" fontSize="12" fontFamily="IBM Plex Mono, monospace">
          {result.treatment?.label} ({result.treatment?.unit})
        </text>
        <text x={padding} y={20} fill="#8d968a" fontSize="12" fontFamily="IBM Plex Mono, monospace">
          {result.outcome?.label} ({result.outcome?.unit})
        </text>
      </svg>
    </div>
  );
}

function InsightCard({ insight, index }: { insight: Insight; index: number }) {
  return (
    <Panel className="overflow-hidden">
      <div className="p-4 sm:p-5">
        <div className="flex items-start gap-3 sm:gap-4">
          <div className="hidden w-6 shrink-0 pt-1 font-mono text-[11px] text-dim sm:block">
            {String(index).padStart(2, "0")}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1.5">
              <span className="text-[12px] text-dim">{insight.category}</span>
              <span className="h-3 w-px bg-line" aria-hidden="true" />
              <EvidenceBadge value={insight.sources.length ? "supporting_evidence" : "unknown"} />
              {insight.tone === "warning" && <Badge tone="amber">Review</Badge>}
              <span className="ml-auto font-mono text-[11px] text-dim">
                {insight.sources.length} {insight.sources.length === 1 ? "source" : "sources"}
              </span>
            </div>
            <h2 className="mt-2.5 font-display text-[16px] leading-snug text-mist">{insight.title}</h2>
            <p className="mt-2 text-[13px] leading-relaxed text-muted">{insight.summary}</p>

            <details className="group mt-4 border-t border-line pt-3">
              <summary className="flex min-h-9 cursor-pointer list-none items-center justify-between gap-2 text-[12px] text-muted transition-colors hover:text-mist focus-visible:[outline:2px_solid_#7dded6] focus-visible:outline-offset-2">
                <span>Evidence, data basis and limitations</span>
                <ChevronDown
                  className="h-4 w-4 shrink-0 text-dim transition-transform group-open:rotate-180"
                  aria-hidden="true"
                />
              </summary>
              <div className="mt-4 space-y-4">
                <div>
                  <div className="mono-label mb-1.5">Interpretation</div>
                  <p className="text-[13px] leading-relaxed text-muted">{insight.evidence}</p>
                </div>
                <div>
                  <div className="mono-label mb-1.5">Data basis</div>
                  <ul className="space-y-1.5">
                    {insight.data_basis.map((item) => (
                      <li key={item} className="flex items-start gap-2.5 font-mono text-[11px] leading-relaxed text-dim">
                        <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-signal/70" aria-hidden="true" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <div className="mono-label mb-1.5">Limitations</div>
                  <p className="text-[12px] leading-relaxed text-dim">{insight.limitations}</p>
                </div>
                {insight.sources.length > 0 && (
                  <div>
                    <div className="mono-label mb-2">Sources</div>
                    <div className="space-y-1.5">
                      {insight.sources.map((source) => (
                        <a
                          key={source.id}
                          href={source.url}
                          target="_blank"
                          rel="noreferrer noopener"
                          className="flex items-start gap-2.5 rounded-[2px] border border-line bg-ink px-3 py-2 transition-colors hover:border-muted/40"
                        >
                          <BookOpen className="mt-0.5 h-3.5 w-3.5 shrink-0 text-signal/80" aria-hidden="true" />
                          <span className="min-w-0 flex-1">
                            <span className="block text-[12px] leading-snug text-mist">{source.title}</span>
                            <span className="mt-0.5 block font-mono text-[11px] text-dim">
                              {source.organization} · {source.published_at ?? "undated"}
                            </span>
                          </span>
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </details>
          </div>
        </div>
      </div>
    </Panel>
  );
}

function InsightStat({
  label,
  value,
  note,
  tone,
}: {
  label: string;
  value: string;
  note: string;
  tone?: "amber" | "signal" | "muted";
}) {
  return (
    <div className="bg-panel px-4 py-3.5">
      <div className="text-[12px] text-dim">{label}</div>
      <div
        className={cn(
          "mt-1.5 number text-[24px] leading-none",
          tone === "amber" ? "text-amber" : tone === "signal" ? "text-signal" : tone === "muted" ? "text-muted" : "text-mist",
        )}
      >
        {value}
      </div>
      <div className="mt-1 text-[11px] text-dim">{note}</div>
    </div>
  );
}

function InsightSkeleton() {
  return (
    <div>
      <Skeleton className="mb-3 h-3 w-52" />
      <Skeleton className="mb-8 h-10 w-[300px]" />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.55fr_0.58fr]">
        <Skeleton className="h-[600px]" />
        <Skeleton className="h-[420px]" />
      </div>
    </div>
  );
}
