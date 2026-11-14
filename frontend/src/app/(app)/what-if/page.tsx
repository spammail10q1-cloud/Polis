"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  ArrowDown,
  Beaker,
  CheckCircle2,
  ChevronDown,
  CircleDashed,
  Clock3,
  Dna,
  ExternalLink,
  LoaderCircle,
  Pill,
  RotateCcw,
  Search,
  TriangleAlert,
} from "lucide-react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PageHeader } from "@/components/page-header";
import { Panel, PanelHeader, PanelBody } from "@/components/ui/panel";
import { Badge, EvidenceBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { ProgressBar } from "@/components/ui/misc";
import { useQuery } from "@/lib/use-query";
import { useToast } from "@/components/toast";
import { apiFetch, apiPost, errorMessage } from "@/lib/api";
import type {
  Exposure,
  LabResult,
  MedicationCatalog,
  Phenotype,
  SimulationResponse,
  SimulationResult,
  TwinOverview,
} from "@/lib/types";
import { clamp, cn, formatDate, formatNumber, relativeTime } from "@/lib/format";

type SimulationListItem = {
  id: string;
  medication_name: string;
  dose_text: string | null;
  status: string;
  created_at: string;
  headline: string | null;
};

const runStages = [
  "Mapping your recorded biological context",
  "Screening curated interactions and allergies",
  "Retrieving versioned evidence",
  "Running the experimental model",
];

function WhatIfContent() {
  const params = useSearchParams();
  const requestedMed = params.get("med");
  const { push } = useToast();
  const catalog = useQuery<MedicationCatalog[]>("/medications/catalog");
  const phenotypes = useQuery<Phenotype[]>("/genetics/pharmacogenomics");
  const labs = useQuery<LabResult[]>("/labs?latest_only=true");
  const meds = useQuery<Exposure[]>("/medications?active_only=true");
  const twin = useQuery<TwinOverview>("/twin");
  const history = useQuery<SimulationListItem[]>("/simulations");
  const [selected, setSelected] = useState<MedicationCatalog | null>(null);
  const [query, setQuery] = useState("");
  const [dose, setDose] = useState("Illustrative dose");
  const [route, setRoute] = useState("oral");
  const [frequency, setFrequency] = useState("single dose");
  const [context, setContext] = useState("");
  const [result, setResult] = useState<SimulationResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [stage, setStage] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (requestedMed && catalog.data) {
      const match = catalog.data.find((item) => item.id === requestedMed);
      if (match) setSelected(match);
    }
  }, [requestedMed, catalog.data]);

  useEffect(() => {
    if (!running) return;
    setStage(0);
    const interval = window.setInterval(() => {
      setStage((current) => Math.min(runStages.length - 1, current + 1));
    }, 900);
    return () => window.clearInterval(interval);
  }, [running]);

  const filteredCatalog = useMemo(() => {
    if (!catalog.data) return [];
    const value = query.trim().toLowerCase();
    if (!value) return catalog.data.slice(0, 7);
    return catalog.data.filter((item) => `${item.name} ${item.generic_name} ${item.drug_class}`.toLowerCase().includes(value)).slice(0, 7);
  }, [catalog.data, query]);

  const latest = useMemo(() => new Map((labs.data ?? []).map((lab) => [lab.code, lab])), [labs.data]);

  const chooseMedication = (medication: MedicationCatalog) => {
    setSelected(medication);
    setRoute("oral");
    setResult(null);
    setError(null);
    setQuery("");
  };

  const run = async () => {
    if (!selected) {
      push("Select a medication first.", "error");
      return;
    }
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const response = await apiPost<SimulationResponse>("/simulations", {
        medication_id: selected.id,
        dose_text: dose,
        route,
        frequency,
        context: context || null,
      });
      setResult(response);
      history.refresh();
      push("Experimental simulation completed. Review uncertainty and missing data.", "info");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setRunning(false);
    }
  };

  const loadHistorical = async (id: string) => {
    try {
      setRunning(true);
      const response = await apiFetch<SimulationResponse>(`/simulations/${id}`);
      setResult(response);
      const med = catalog.data?.find((item) => item.id === response.result.medication.id);
      if (med) setSelected(med);
      setError(null);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setRunning(false);
    }
  };

  if (catalog.loading && !catalog.data) return <WhatIfSkeleton />;

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Experimental simulation workspace"
        title="What If?"
        description="A structured, evidence-labelled exploration of how a medicine might behave with your recorded biology. It is not a prescription, a dose calculation, or a prediction of benefit or harm."
        actions={
          <>
            <Badge tone="violet">Experimental model</Badge>
            <Badge tone="muted">No dose output</Badge>
          </>
        }
      />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[250px_minmax(340px,0.86fr)_minmax(0,1.55fr)]">
        <div className="order-3 space-y-4 xl:order-1 xl:sticky xl:top-[74px] xl:self-start">
          <Panel>
            <PanelHeader eyebrow="Your context" title="Biological input" description="What the model can see before you run anything." />
            <div className="space-y-4 p-4">
              <div>
                <div className="flex items-baseline justify-between gap-3">
                  <span className="font-mono text-[11px] text-dim">Data coverage</span>
                  {twin.data && twin.data.overall_completeness != null ? (
                    <span className="font-mono text-[13px] text-mist">
                      {twin.data.overall_completeness}
                      <span className="text-[11px] text-dim">%</span>
                    </span>
                  ) : (
                    <span className="font-mono text-[11px] text-dim">Not available</span>
                  )}
                </div>
                <ProgressBar value={twin.data?.overall_completeness ?? 0} className="mt-2" />
                <p className="mt-2 text-[11px] leading-relaxed text-dim">Coverage, not a health score.</p>
              </div>

              <ContextSection title="Pharmacogenomics" icon={Dna} count={phenotypes.data?.length}>
                {(phenotypes.data ?? []).slice(0, 5).map((phenotype) => (
                  <div key={phenotype.gene} className="flex items-center justify-between gap-2 py-1">
                    <span className="font-mono text-[12px] text-signal">{phenotype.gene}</span>
                    <span className="truncate text-right text-[12px] text-muted">{phenotype.phenotype}</span>
                  </div>
                ))}
                {(phenotypes.data?.length ?? 0) > 5 && (
                  <div className="pt-1 font-mono text-[11px] text-dim">and {(phenotypes.data?.length ?? 0) - 5} more</div>
                )}
                {!phenotypes.data?.length && <div className="py-1 text-[12px] text-dim">No curated phenotypes.</div>}
              </ContextSection>

              <ContextSection title="Organ context" icon={Beaker}>
                {[
                  { code: "alt", label: "ALT" },
                  { code: "egfr", label: "eGFR" },
                  { code: "bilirubin", label: "Bilirubin" },
                ].map((item) => {
                  const lab = latest.get(item.code);
                  if (!lab) return null;
                  return (
                    <div key={item.code} className="flex items-center justify-between gap-2 py-1.5">
                      <div>
                        <div className="font-mono text-[12px] text-muted">{item.label}</div>
                        <div className="font-mono text-[11px] text-dim">{formatDate(lab.measured_at, { year: undefined })}</div>
                      </div>
                      <div className="text-right">
                        <span className="font-mono text-[13px] text-mist">{formatNumber(lab.value)}</span>
                        <span className="ml-1 font-mono text-[11px] text-dim">{lab.unit}</span>
                      </div>
                    </div>
                  );
                })}
                {!latest.size && <div className="py-1 text-[12px] text-dim">No laboratory data.</div>}
              </ContextSection>

              <ContextSection title="Active medications" icon={Pill} count={meds.data?.length}>
                {(meds.data ?? []).map((medication) => (
                  <div key={medication.id} className="py-1.5">
                    <div className="text-[13px] text-muted">{medication.name}</div>
                    <div className="mt-0.5 font-mono text-[11px] text-dim">{medication.dose_text}, {medication.frequency}</div>
                  </div>
                ))}
                {!meds.data?.length && <div className="py-1 text-[12px] text-dim">None recorded.</div>}
              </ContextSection>
            </div>
          </Panel>

          <Callout tone="neutral" title="Grounded in evidence">
            The workspace retrieves curated labeling, guidelines and citations from the local corpus. It does not send
            raw records to an external model.
          </Callout>
        </div>

        <div className="order-1 space-y-4 xl:order-2">
          <Panel emphasis>
            <PanelHeader eyebrow="Intervention" title="Define a hypothetical exposure" />
            <div className="space-y-4 p-4">
              <div>
                <span className="mb-2 block font-mono text-[12px] text-dim">Medication</span>
                {selected ? (
                  <div className="border border-signal/25 bg-signal/[0.04] p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="text-[14px] text-mist">{selected.name}</div>
                        <div className="mt-0.5 text-[12px] text-dim">{selected.drug_class}</div>
                      </div>
                      <button
                        type="button"
                        onClick={() => { setSelected(null); setResult(null); }}
                        aria-label={`Change medication, currently ${selected.name}`}
                        className="min-h-11 shrink-0 cursor-pointer px-2 font-mono text-[12px] text-dim transition-colors hover:text-mist"
                      >
                        Change
                      </button>
                    </div>
                    <div className="mt-2 flex items-center gap-2">
                      <Badge tone={selected.is_simulation_eligible ? "violet" : "amber"}>
                        {selected.is_simulation_eligible ? "Model available" : "Refusal only"}
                      </Badge>
                    </div>
                  </div>
                ) : (
                  <div>
                    <label htmlFor="what-if-medication-search" className="mb-1.5 block text-[12px] text-dim">
                      Search catalog
                    </label>
                    <div className="relative">
                      <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-dim" aria-hidden="true" />
                      <input
                        id="what-if-medication-search"
                        value={query}
                        onChange={(event) => setQuery(event.target.value)}
                        placeholder="Search curated medications"
                        className="input pl-9"
                      />
                    </div>
                    <div className="mt-2 max-h-[240px] overflow-y-auto border border-line">
                      {filteredCatalog.map((medication) => (
                        <button
                          type="button"
                          key={medication.id}
                          onClick={() => chooseMedication(medication)}
                          className="flex min-h-11 w-full cursor-pointer items-center justify-between gap-3 border-b border-line px-3 py-2.5 text-left last:border-0 hover:bg-raised/60"
                        >
                          <span className="min-w-0">
                            <span className="block truncate text-[13px] text-mist">{medication.name}</span>
                            <span className="mt-0.5 block truncate text-[11px] text-dim">{medication.drug_class}</span>
                          </span>
                          <span className={cn("shrink-0 font-mono text-[11px]", medication.is_simulation_eligible ? "text-violet" : "text-amber")}>
                            {medication.is_simulation_eligible ? "Model available" : "Refusal only"}
                          </span>
                        </button>
                      ))}
                      {!filteredCatalog.length && <div className="px-3 py-6 text-[12px] text-dim">No curated medication matches.</div>}
                    </div>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-2">
                <label>
                  <span className="mb-1.5 block font-mono text-[12px] text-dim">Dose or label</span>
                  <input className="input" value={dose} onChange={(event) => setDose(event.target.value)} />
                </label>
                <label>
                  <span className="mb-1.5 block font-mono text-[12px] text-dim">Route</span>
                  <select className="input" value={route} onChange={(event) => setRoute(event.target.value)}>
                    {["oral", "intravenous", "inhalation", "subcutaneous"].map((item) => <option key={item}>{item}</option>)}
                  </select>
                </label>
                <label>
                  <span className="mb-1.5 block font-mono text-[12px] text-dim">Frequency</span>
                  <select className="input" value={frequency} onChange={(event) => setFrequency(event.target.value)}>
                    {["single dose", "once daily", "twice daily", "weekly"].map((item) => <option key={item}>{item}</option>)}
                  </select>
                </label>
                <div>
                  <span className="mb-1.5 block font-mono text-[12px] text-dim">Timing context</span>
                  <div className="flex min-h-[42px] items-center border border-line bg-ink px-3 py-2 font-mono text-[12px] leading-relaxed text-muted">
                    {frequency === "single dose" ? "hypothetical" : "steady state not modeled"}
                  </div>
                </div>
              </div>

              <label>
                <span className="mb-1.5 block font-mono text-[12px] text-dim">Additional context (optional)</span>
                <textarea
                  className="input min-h-16"
                  value={context}
                  onChange={(event) => setContext(event.target.value)}
                  placeholder="For example: with food, recent illness, or a question for your clinician."
                />
              </label>

              <Button onClick={run} loading={running} className="w-full" variant="primary" disabled={!selected}>
                Run experimental analysis
              </Button>

              <Callout tone="warning">
                The dose field is context only. POLIS does not calculate a personalized dose, target concentration, or
                recommendation. Never start, stop, or change a medicine based on this output.
              </Callout>

              <div className="border-t border-line pt-3">
                <div className="mb-2 font-mono text-[12px] text-dim">Suggested explorations</div>
                <div className="flex flex-wrap gap-1.5">
                  {[
                    { id: "clopidogrel", label: "Clopidogrel" },
                    { id: "simvastatin", label: "Simvastatin" },
                    { id: "metoprolol", label: "Metoprolol" },
                    { id: "warfarin", label: "Warfarin" },
                  ].map((item) => {
                    const med = catalog.data?.find((entry) => entry.id === item.id);
                    if (!med) return null;
                    return (
                      <button
                        type="button"
                        key={item.id}
                        onClick={() => chooseMedication(med)}
                        className="chip min-h-11 cursor-pointer hover:border-signal/40 hover:text-mist"
                      >
                        {item.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </Panel>

          <Panel>
            <PanelHeader eyebrow="Recent simulations" title="Audit trail" />
            <div className="divide-y divide-line">
              {(history.data ?? []).slice(0, 4).map((item) => (
                <button
                  type="button"
                  key={item.id}
                  onClick={() => loadHistorical(item.id)}
                  className="flex min-h-14 w-full cursor-pointer items-center gap-3 px-4 py-3 text-left hover:bg-raised/60"
                >
                  <Clock3 className="h-3.5 w-3.5 shrink-0 text-dim" aria-hidden="true" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[13px] text-muted">{item.medication_name}</div>
                    <div className="mt-0.5 font-mono text-[11px] text-dim">{relativeTime(item.created_at)}, {item.status.replaceAll("_", " ")}</div>
                  </div>
                </button>
              ))}
              {!history.data?.length && <div className="px-4 py-8 text-center text-[12px] text-dim">No simulations run yet.</div>}
            </div>
          </Panel>
        </div>

        <div className="order-2 min-w-0 xl:order-3">
          {running ? (
            <RunProgress stage={stage} medication={selected?.name} />
          ) : error ? (
            <Panel>
              <PanelBody>
                <Callout tone="danger" title="The request could not be simulated">{error}</Callout>
                <div className="mt-4">
                  <Button onClick={run} variant="secondary"><RotateCcw className="h-3.5 w-3.5" aria-hidden="true" /> Try again</Button>
                </div>
              </PanelBody>
            </Panel>
          ) : result ? (
            <ResultWorkspace data={result} />
          ) : (
            <EmptyWorkspace />
          )}
        </div>
      </div>
    </div>
  );
}

function ContextSection({
  title,
  icon: Icon,
  count,
  children,
}: {
  title: string;
  icon: typeof Dna;
  count?: number;
  children: React.ReactNode;
}) {
  return (
    <div className="border-t border-line pt-3">
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 font-mono text-[11px] text-dim">
          <Icon className="h-3.5 w-3.5" aria-hidden="true" /> {title}
        </span>
        {count !== undefined && <span className="font-mono text-[11px] text-dim">{count}</span>}
      </div>
      {children}
    </div>
  );
}

function RunProgress({ stage, medication }: { stage: number; medication?: string }) {
  return (
    <Panel className="min-h-[540px]">
      <PanelBody className="flex min-h-[500px] flex-col justify-center">
        <div className="mx-auto w-full max-w-[400px]">
          <div className="flex items-center gap-2 font-mono text-[12px] text-signal">
            <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
            Experimental model running
          </div>
          <h2 className="display mt-3 text-[28px] text-mist">{medication ?? "Hypothetical exposure"}</h2>
          <p className="mt-1 text-[13px] text-muted">Reviewing your recorded context and the retrieved evidence.</p>

          <ol className="mt-6 space-y-3" aria-label="Simulation progress">
            {runStages.map((label, index) => (
              <li
                key={label}
                aria-current={index === stage ? "step" : undefined}
                className={cn("flex items-start gap-2.5 text-[13px] leading-relaxed", index <= stage ? "text-mist/90" : "text-dim")}
              >
                {index < stage ? (
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-mint" aria-hidden="true" />
                ) : index === stage ? (
                  <LoaderCircle className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-signal" aria-hidden="true" />
                ) : (
                  <CircleDashed className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                )}
                <span>{label}</span>
              </li>
            ))}
          </ol>

          <p className="mt-6 border-t border-line pt-4 text-[12px] leading-relaxed text-dim">
            The model is a one-compartment educational approximation, not a validated PBPK model. No dose is calculated.
          </p>
        </div>
      </PanelBody>
    </Panel>
  );
}

function EmptyWorkspace() {
  return (
    <Panel className="min-h-[540px]" emphasis>
      <div className="flex min-h-[540px] flex-col justify-center px-6 py-12 sm:px-10">
        <div className="mx-auto w-full max-w-[560px]">
          <div className="eyebrow">Awaiting an intervention</div>
          <h2 className="display mt-2 max-w-[480px] text-[30px] leading-[1.1] text-mist sm:text-[34px]">
            Explore a plausible response, not a prescription.
          </h2>
          <p className="mt-3 max-w-[520px] text-[14px] leading-relaxed text-muted">
            Select a medicine and run the analysis. The result will show how your recorded data applies, a mechanistic
            explanation, curated interaction flags, uncertainty, missing information, and questions for professional review.
          </p>

          <dl className="mt-7 grid grid-cols-1 gap-px border border-line bg-line sm:grid-cols-2">
            {[
              ["Clinical evidence", "Established labeling, guidelines, and curated sources."],
              ["Personal evidence", "Your recorded labs, genetics, and medications."],
              ["Model estimate", "A modeled interval, never a dose."],
              ["Unknown", "Missing information is named, never invented."],
            ].map(([term, detail]) => (
              <div key={term} className="bg-panel px-4 py-3">
                <dt className="font-mono text-[12px] text-mist">{term}</dt>
                <dd className="mt-1 text-[12px] leading-relaxed text-dim">{detail}</dd>
              </div>
            ))}
          </dl>

          <p className="mt-6 max-w-[480px] text-[12px] leading-relaxed text-dim">
            Some medicines intentionally return a structured refusal. That is a safety boundary, not a missing feature.
          </p>
        </div>
      </div>
    </Panel>
  );
}

function ResultWorkspace({ data }: { data: SimulationResponse }) {
  const result = data.result;
  const isRefusal = result.status === "not_supported";
  return (
    <div className="@container space-y-4 animate-fade-in">
      <Panel emphasis>
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line px-5 py-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={isRefusal ? "amber" : "violet"}>
                {isRefusal ? "No simulation generated" : "Model estimate"}
              </Badge>
              <Badge tone="muted">{result.model.version}</Badge>
              {result.synthetic_data && <Badge tone="amber">Synthetic data</Badge>}
            </div>
            <h2 className="display mt-3 text-[26px] text-mist sm:text-[30px]">
              {result.medication.name}
              <span className="ml-2 font-sans text-[13px] text-dim">{result.medication.drug_class}</span>
            </h2>
            <p className="mt-1.5 font-mono text-[12px] text-dim">
              Simulated {formatDate(data.created_at)}. Status: {result.status.replaceAll("_", " ")}.
            </p>
          </div>
          <div className="text-right">
            <div className="font-mono text-[11px] text-dim">Engine</div>
            <div className="mt-1 max-w-[190px] font-mono text-[11px] leading-relaxed text-dim">{result.model.name}</div>
          </div>
        </div>
        <div className="p-5">
          <div className={cn("border-l-2 pl-4", isRefusal ? "border-amber" : "border-signal")}>
            <p className="text-[14px] leading-relaxed text-mist/90">{result.headline}</p>
            {result.reason && <p className="mt-2 text-[13px] leading-relaxed text-muted">{result.reason}</p>}
          </div>

          {result.safety_flags.length > 0 && (
            <div className="mt-4 space-y-2">
              {result.safety_flags.slice(0, 3).map((flag) => (
                <Callout
                  key={flag.title}
                  tone={flag.severity === "danger" ? "danger" : flag.severity === "warning" ? "warning" : "info"}
                  title={flag.title}
                >
                  {flag.detail}
                </Callout>
              ))}
            </div>
          )}

          {result.medication.warnings.length > 0 && (
            <div className="mt-4 border border-amber/25 bg-amber/[0.04] px-4 py-3">
              <div className="font-mono text-[11px] text-amber">Medication labeling context</div>
              <ul className="mt-2 space-y-1.5">
                {result.medication.warnings.slice(0, 3).map((warning) => (
                  <li key={warning} className="flex items-start gap-2 text-[13px] leading-relaxed text-muted">
                    <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-amber/70" aria-hidden="true" />
                    {warning}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {!isRefusal && result.summary_metrics && !result.pathway_index && (
            <div className="mt-5 grid grid-cols-2 gap-px border border-line bg-line @2xl:grid-cols-4">
              {result.summary_metrics.map((metric) => (
                <div key={metric.key} className="bg-panel p-3.5">
                  <div className="font-mono text-[11px] text-dim">{metric.label}</div>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="number text-[20px] text-mist">{formatNumber(metric.value, 2)}</span>
                    <span className="font-mono text-[11px] text-dim">{metric.unit}</span>
                  </div>
                  <div className="mt-1 font-mono text-[12px] text-amber">
                    {formatNumber(metric.low, 2)} to {formatNumber(metric.high, 2)}
                  </div>
                  <EvidenceBadge value={metric.classification} className="mt-2" />
                </div>
              ))}
            </div>
          )}

          {!isRefusal && result.curve && (
            <div className="mt-5 border border-line">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-2.5">
                <span className="font-mono text-[11px] text-muted">Illustrative concentration-time</span>
                <div className="flex flex-wrap items-center gap-4 font-mono text-[11px] text-dim">
                  <span className="flex items-center gap-1.5"><i className="h-0.5 w-4 bg-signal" aria-hidden="true" /> Median</span>
                  <span className="flex items-center gap-1.5"><i className="h-2 w-4 border-y border-signal/40 bg-signal/15" aria-hidden="true" /> 5-95% interval</span>
                  <span className="flex items-center gap-1.5"><i className="w-4 border-t border-dashed border-dim" aria-hidden="true" /> Reference</span>
                </div>
              </div>
              <ExposureChart result={result} />
              <p className="border-t border-line px-4 py-2.5 text-[12px] leading-relaxed text-dim">{result.curve.note}</p>
            </div>
          )}

          {!isRefusal && result.pathway_index && (
            <div className="mt-5">
              <PathwayIndex result={result} />
            </div>
          )}
        </div>
      </Panel>

      {isRefusal && (
        <Panel>
          <PanelHeader
            eyebrow="Structured refusal"
            title="Why no estimate was generated"
            description="This is a deliberate safety boundary. The information below is still available for professional review."
            action={<Badge tone="amber">No model output</Badge>}
          />
          <div className="p-5">
            {result.missing_information.length > 0 && (
              <div>
                <div className="mb-2 font-mono text-[12px] text-dim">Missing or required information</div>
                <ul className="space-y-2">
                  {result.missing_information.map((item) => (
                    <li key={item} className="flex items-start gap-2 text-[13px] leading-relaxed text-muted">
                      <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber" aria-hidden="true" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {result.assumptions.length > 0 && (
              <div className="mt-4 border-t border-line pt-3">
                <div className="mb-2 font-mono text-[12px] text-dim">Context assumptions</div>
                <p className="text-[13px] leading-relaxed text-muted">{result.assumptions.join(" ")}</p>
              </div>
            )}
          </div>
        </Panel>
      )}

      {!isRefusal && (
        <Panel>
          <PanelHeader
            eyebrow="Pathway visualization"
            title="From hypothetical input to modeled output"
            description="A mechanistic map of what the model does and does not represent."
            action={<EvidenceBadge value="experimental_hypothesis" />}
          />
          <div className="p-5">
            <PathwayFlow result={result} />
          </div>
        </Panel>
      )}

      {!isRefusal && (
        <div className="grid grid-cols-1 gap-4 @2xl:grid-cols-2">
          <Panel>
            <PanelHeader
              eyebrow="Personal data relevance"
              title="What was used"
              action={<Badge tone="muted">{result.model_inputs?.length ?? 0} {(result.model_inputs?.length ?? 0) === 1 ? "input" : "inputs"}</Badge>}
            />
            <div className="divide-y divide-line">
              {(result.model_inputs ?? []).map((input) => (
                <div key={input.label} className="px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-[13px] text-mist/90">{input.label}</div>
                      <div className="mt-1 text-[13px] text-muted">{input.value}</div>
                    </div>
                    <EvidenceBadge value={input.classification} />
                  </div>
                  <div className="mt-1.5 text-[12px] leading-relaxed text-dim">{input.detail}</div>
                  <div className="mt-1 font-mono text-[11px] text-dim">{input.source}</div>
                </div>
              ))}
              {(result.model_inputs ?? []).length === 0 && (
                <div className="px-4 py-6 text-[12px] text-dim">No recorded personal inputs were used for this simulation.</div>
              )}
            </div>
          </Panel>

          <div className="space-y-4">
            <Panel>
              <PanelHeader
                eyebrow="Uncertainty"
                title="What the interval means"
                action={<Badge tone="amber">{result.uncertainty?.level}</Badge>}
              />
              <PanelBody className="space-y-2.5">
                {(result.uncertainty?.statements ?? []).map((statement) => (
                  <p key={statement} className="text-[13px] leading-relaxed text-muted">{statement}</p>
                ))}
                <p className="border-t border-line pt-2.5 font-mono text-[11px] leading-relaxed text-dim">
                  {result.uncertainty?.interval_definition}
                </p>
              </PanelBody>
            </Panel>

            <Panel>
              <PanelHeader
                eyebrow="Missing information"
                title="What remains unknown"
                action={<Badge tone="amber">{result.missing_information.length === 1 ? "1 item" : `${result.missing_information.length} items`}</Badge>}
              />
              <div className="max-h-[290px] overflow-y-auto px-4 py-3">
                <ul className="space-y-2">
                  {result.missing_information.map((item) => (
                    <li key={item} className="flex items-start gap-2 text-[13px] leading-relaxed text-muted">
                      <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber" aria-hidden="true" />
                      {item}
                    </li>
                  ))}
                </ul>
                {result.missing_information.length === 0 && (
                  <p className="text-[13px] leading-relaxed text-muted">No missing information was recorded for this simulation.</p>
                )}
              </div>
            </Panel>
          </div>
        </div>
      )}

      {result.interactions.length > 0 && (
        <Panel>
          <PanelHeader
            eyebrow="Interaction screen"
            title="Curated signals for professional review"
            description="Known risk flags are separated from the experimental model estimate."
            action={<Badge tone={result.interactions.some((item) => ["major", "contraindicated"].includes(item.severity)) ? "danger" : "amber"}>{result.interactions.length === 1 ? "1 signal" : `${result.interactions.length} signals`}</Badge>}
          />
          <div className="divide-y divide-line">
            {result.interactions.map((interaction) => (
              <div key={interaction.id} className="px-5 py-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={interaction.severity === "contraindicated" || interaction.severity === "major" ? "danger" : "amber"}>
                    <span className="capitalize">{interaction.severity}</span>
                  </Badge>
                  <span className="text-[13px] text-mist">{interaction.other_medication}</span>
                  <span className="font-mono text-[11px] text-dim">{interaction.evidence_level}</span>
                </div>
                <p className="mt-2 text-[13px] leading-relaxed text-muted">{interaction.effect}</p>
                <p className="mt-1 text-[12px] leading-relaxed text-dim">{interaction.mechanism}</p>
                <p className="mt-2 border-l border-amber/40 pl-3 text-[13px] leading-relaxed text-amber">{interaction.management}</p>
              </div>
            ))}
          </div>
        </Panel>
      )}

      <div className="grid grid-cols-1 gap-4 @4xl:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <Panel>
          <PanelHeader eyebrow="Auditable reasoning" title="How this result was assembled" />
          <div className="px-4 py-4">
            <div className="relative space-y-0">
              {result.reasoning_steps.map((step, index) => (
                <div key={step.order} className="relative flex gap-3 pb-4 last:pb-0">
                  {index < result.reasoning_steps.length - 1 && (
                    <span className="absolute left-[9px] top-6 h-[calc(100%-16px)] w-px bg-line" aria-hidden="true" />
                  )}
                  <span
                    className={cn(
                      "relative z-10 mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border font-mono text-[11px]",
                      step.status === "blocked"
                        ? "border-danger/40 bg-danger/10 text-danger"
                        : step.status === "flagged"
                          ? "border-amber/40 bg-amber/10 text-amber"
                          : "border-mint/30 bg-mint/[0.06] text-mint",
                    )}
                  >
                    {step.order}
                  </span>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[13px] text-mist/90">{step.title}</span>
                      <EvidenceBadge value={step.evidence_class} />
                      <span
                        className={cn(
                          "font-mono text-[11px] capitalize",
                          step.status === "blocked" ? "text-danger" : step.status === "flagged" ? "text-amber" : "text-mint",
                        )}
                      >
                        {step.status.replaceAll("_", " ")}
                      </span>
                    </div>
                    <p className="mt-1 text-[12px] leading-relaxed text-dim">{step.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Panel>

        <Panel>
          <PanelHeader eyebrow="Clinician review" title="Questions worth asking" action={<Badge tone="amber">Not advice</Badge>} />
          <div className="px-4 py-3">
            <p className="mb-3 text-[13px] leading-relaxed text-muted">
              These questions are generated from the recorded context and known limitations. They are not
              recommendations. A qualified clinician or pharmacist should review any medication decision.
            </p>
            <ol className="space-y-2.5">
              {result.clinician_questions.map((question, index) => (
                <li key={question} className="flex items-start gap-2.5">
                  <span className="mt-0.5 font-mono text-[11px] text-dim">{String(index + 1).padStart(2, "0")}</span>
                  <span className="text-[13px] leading-relaxed text-muted">{question}</span>
                </li>
              ))}
            </ol>
          </div>
        </Panel>
      </div>

      {result.pharmacokinetics && !isRefusal && (
        <Panel>
          <PanelHeader eyebrow="Mechanistic explanation" title="Absorption, distribution, metabolism, elimination" />
          <div className="grid grid-cols-1 gap-px bg-line @md:grid-cols-2 @4xl:grid-cols-3">
            {[
              ["Absorption", result.pharmacokinetics.absorption],
              ["Distribution", result.pharmacokinetics.distribution],
              ["Metabolism", result.pharmacokinetics.metabolism],
              ["Elimination", result.pharmacokinetics.elimination],
              ["Personalization", result.pharmacokinetics.personalization],
            ].map(([label, text]) => (
              <div key={label} className={cn("bg-panel p-4", label === "Personalization" && "@md:col-span-2")}>
                <div className="font-mono text-[11px] text-dim">{label}</div>
                <p className="mt-2 text-[13px] leading-relaxed text-muted">{text}</p>
              </div>
            ))}
          </div>
          {result.medication.parameter_sources && result.medication.parameter_sources.length > 0 && (
            <details className="group border-t border-line">
              <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 font-mono text-[12px] text-dim hover:text-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal">
                Published parameters and cited assumptions
                <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" aria-hidden="true" />
              </summary>
              <div className="border-t border-line">
                {result.medication.parameter_sources.map((parameter) => (
                  <div key={parameter.parameter} className="grid gap-1 border-b border-line px-4 py-3 last:border-0 sm:grid-cols-[190px_1fr]">
                    <div className="font-mono text-[11px] text-dim">{parameter.parameter}</div>
                    <div>
                      <div className="font-mono text-[12px] text-muted">{parameter.value}</div>
                      <div className="mt-1 text-[11px] leading-relaxed text-dim">{parameter.source}</div>
                    </div>
                  </div>
                ))}
              </div>
            </details>
          )}
        </Panel>
      )}

      {result.assumptions.length > 0 && (
        <Panel>
          <PanelHeader
            eyebrow="Assumptions"
            title="What the model had to assume"
            action={<Badge tone="amber">{result.assumptions.length === 1 ? "1 assumption" : `${result.assumptions.length} assumptions`}</Badge>}
          />
          <div className="px-4 py-3">
            <ul className="space-y-2">
              {result.assumptions.map((assumption) => (
                <li key={assumption} className="flex items-start gap-2 text-[13px] leading-relaxed text-muted">
                  <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-amber/70" aria-hidden="true" />
                  {assumption}
                </li>
              ))}
            </ul>
          </div>
        </Panel>
      )}

      {!isRefusal && result.sensitivity && (
        <SensitivityPanel sensitivity={result.sensitivity} />
      )}

      <Panel>
        <PanelHeader
          eyebrow="Evidence"
          title="Sources retrieved for this analysis"
          action={<Badge tone="muted">{result.evidence.length === 1 ? "1 source" : `${result.evidence.length} sources`}</Badge>}
        />
        <div className="divide-y divide-line">
          {result.evidence.map((source) => (
            <a
              key={source.id}
              href={source.url}
              target="_blank"
              rel="noreferrer noopener"
              className="group block px-5 py-3.5 hover:bg-raised/50"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-[11px] text-signal">{source.organization}</span>
                    {source.published_at && <span className="font-mono text-[11px] text-dim">{source.published_at}</span>}
                    <EvidenceBadge value="established_clinical_evidence" />
                  </div>
                  <h3 className="mt-1.5 text-[13px] leading-snug text-mist group-hover:text-signal">{source.title}</h3>
                  {source.snippet && <p className="mt-1 line-clamp-2 text-[12px] leading-relaxed text-dim">{source.snippet}</p>}
                </div>
                <ExternalLink className="h-3.5 w-3.5 shrink-0 text-dim" aria-hidden="true" />
              </div>
            </a>
          ))}
          {!result.evidence.length && <div className="px-5 py-8 text-center text-[12px] text-dim">No sources were retrieved for this simulation.</div>}
        </div>
      </Panel>

      <Callout tone="danger" title="Safety and interpretation">
        {result.disclaimer}
      </Callout>
    </div>
  );
}

function ExposureChart({ result }: { result: SimulationResult }) {
  if (!result.curve) return null;
  const curve = result.curve;
  const data = curve.times.map((time, index) => ({
    time,
    low: curve.p05[index],
    band: Math.max(0, curve.p95[index] - curve.p05[index]),
    median: curve.median[index],
    p05: curve.p05[index],
    p95: curve.p95[index],
  }));
  return (
    <div className="h-[270px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 16, right: 16, bottom: 4, left: -12 }}>
          <CartesianGrid stroke="#2a312b" vertical={false} />
          <XAxis
            dataKey="time"
            tick={{ fill: "#8d968a", fontSize: 12, fontFamily: "IBM Plex Mono, monospace" }}
            tickLine={false}
            axisLine={{ stroke: "#2a312b" }}
            tickFormatter={(value: number) => `${value}h`}
            minTickGap={30}
          />
          <YAxis
            tick={{ fill: "#8d968a", fontSize: 12, fontFamily: "IBM Plex Mono, monospace" }}
            tickLine={false}
            axisLine={false}
            width={46}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const point = payload[0]?.payload as { time: number; median: number; p05: number; p95: number } | undefined;
              if (!point) return null;
              return (
                <div className="border border-[#3b453c] bg-[#111512] px-3 py-2">
                  <div className="font-mono text-[11px] text-dim">{point.time}h</div>
                  <div className="mt-1 number text-[14px] text-mist">{formatNumber(point.median, 3)}×</div>
                  <div className="mt-0.5 font-mono text-[11px] text-amber">
                    5-95%: {formatNumber(point.p05, 3)} to {formatNumber(point.p95, 3)}
                  </div>
                </div>
              );
            }}
            cursor={{ stroke: "#3b453c", strokeDasharray: "2 3" }}
          />
          <Area type="monotone" dataKey="low" stackId="band" stroke="none" fill="transparent" isAnimationActive={false} />
          <Area type="monotone" dataKey="band" stackId="band" stroke="none" fill="rgba(125,222,214,.10)" isAnimationActive={false} />
          <ReferenceLine y={1} stroke="#3b453c" strokeDasharray="3 4" />
          <Line type="monotone" dataKey="median" stroke="#7dded6" strokeWidth={1.8} dot={false} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function PathwayIndex({ result }: { result: SimulationResult }) {
  const index = result.pathway_index;
  if (!index) return null;
  const scaleMax = Math.max(1.5, index.high * 1.25);
  const percent = clamp((index.value / scaleMax) * 100, 0, 100);
  const lowPercent = clamp((index.low / scaleMax) * 100, 0, 100);
  const highPercent = clamp((index.high / scaleMax) * 100, 0, 100);
  return (
    <div className="border border-violet/25 bg-violet/[0.03] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-mono text-[11px] text-dim">{index.label}</div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="number text-[28px] text-violet">{formatNumber(index.value, 2)}×</span>
            <span className="font-mono text-[11px] text-dim">relative to reference</span>
          </div>
          <div className="mt-1 font-mono text-[12px] text-amber">
            5-95% {formatNumber(index.low, 2)} to {formatNumber(index.high, 2)}
          </div>
        </div>
        <EvidenceBadge value="model_estimate" />
      </div>

      <div className="relative mt-5 h-10">
        <div className="absolute inset-x-0 top-3.5 h-1 bg-raised" />
        <div className="absolute top-3.5 h-1 bg-violet" style={{ width: `${percent}%` }} />
        <div className="absolute top-1.5 h-5 border-l border-violet" style={{ left: `${lowPercent}%` }} />
        <div className="absolute top-1.5 h-5 border-r border-violet" style={{ left: `${highPercent}%` }} />
        <div className="absolute top-1 h-6 border-l border-dashed border-dim" style={{ left: `${(1 / scaleMax) * 100}%` }} />
        <span className="absolute top-6 -translate-x-1/2 font-mono text-[11px] text-dim" style={{ left: `${(1 / scaleMax) * 100}%` }}>
          1.0× reference
        </span>
        <div className="absolute top-0 h-5 w-px bg-mist" style={{ left: `${percent}%` }} />
      </div>

      <p className="mt-3 text-[12px] leading-relaxed text-dim">{index.basis}</p>

      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[420px]">
          <thead>
            <tr className="border-b border-line text-left">
              {["Gene", "Phenotype", "Weight", "Activity", "Interaction"].map((label) => (
                <th key={label} className="py-1.5 pr-3 font-mono text-[11px] font-normal text-dim">{label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {index.contributions.map((row) => (
              <tr key={row.gene} className="border-b border-line last:border-0">
                <td className="py-1.5 pr-3 font-mono text-[12px] text-signal">{row.gene}</td>
                <td className="py-1.5 pr-3 text-[12px] text-muted">{row.phenotype}</td>
                <td className="py-1.5 pr-3 font-mono text-[12px] text-dim">{(row.weight * 100).toFixed(0)}%</td>
                <td className="py-1.5 pr-3 font-mono text-[12px] text-dim">{row.activity_factor.toFixed(2)}×</td>
                <td className={cn("py-1.5 pr-3 font-mono text-[12px]", row.interaction_factor !== 1 ? "text-amber" : "text-dim")}>
                  {row.interaction_factor.toFixed(2)}×
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-[11px] leading-relaxed text-dim">{index.note}</p>
    </div>
  );
}

function PathwayFlow({ result }: { result: SimulationResult }) {
  const genes = result.pgx ?? [];
  const isProdrug = Boolean(result.pathway_index);
  const outputValue = isProdrug && result.pathway_index
    ? `${result.pathway_index.value.toFixed(2)}×`
    : `${(result.summary_metrics?.find((metric) => metric.key === "relative_auc")?.value ?? 0).toFixed(2)}×`;
  return (
    <div className="space-y-0">
      <div className="border border-line p-3.5">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <div className="mb-1.5 font-mono text-[11px] text-dim">Hypothetical input</div>
            <div className="text-[14px] text-mist">{result.medication.name}</div>
          </div>
          <EvidenceBadge value="personalized_evidence" />
        </div>
        <div className="mt-1.5 text-[12px] leading-relaxed text-dim">Dose is context only. No personalized dose is calculated.</div>
      </div>

      <FlowConnector label={isProdrug ? "activation" : "metabolism"} />

      <div className="border border-line p-3.5">
        <div className="mb-2 font-mono text-[11px] text-dim">Biological processing</div>
        <div className="space-y-1.5">
          {genes.map((gene) => (
            <div key={gene.gene} className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border border-line px-2.5 py-2">
              <div className="min-w-0">
                <span className="font-mono text-[12px] text-signal">{gene.gene}</span>
                <span className="ml-2 text-[12px] text-dim">{gene.phenotype}{!gene.known && " (assumed)"}</span>
              </div>
              <div className="font-mono text-[11px] text-dim">
                {gene.known ? `${gene.activity_factor.toFixed(2)}× activity` : "population assumption"}
                {gene.interaction_factor !== 1 && <span className="ml-2 text-amber">{gene.interaction_factor.toFixed(2)}× DDI</span>}
              </div>
            </div>
          ))}
          {!genes.length && <div className="text-[12px] text-dim">No curated enzyme pathway is modeled for this medicine.</div>}
        </div>
      </div>

      <FlowConnector label={isProdrug ? "active metabolite" : "clearance"} />

      <div className="border border-line p-3.5">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <div className="mb-1.5 font-mono text-[11px] text-dim">Modeled output</div>
            <div className="text-[14px] text-mist">{isProdrug ? "Relative activation potential" : "Relative systemic exposure"}</div>
          </div>
          <EvidenceBadge value="model_estimate" />
        </div>
        <div className="mt-2 number text-[26px] text-violet">{outputValue}</div>
        <div className="mt-2 border-t border-line pt-2 text-[12px] leading-relaxed text-dim">
          {isProdrug ? "Downstream platelet effect is not modeled." : "Efficacy, toxicity and tissue concentrations are not modeled."}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 font-mono text-[11px] text-dim">
        <span className="flex items-center gap-1.5"><i className="h-1.5 w-1.5 rounded-full bg-signal" aria-hidden="true" /> Personal evidence</span>
        <span className="flex items-center gap-1.5"><i className="h-1.5 w-1.5 rounded-full bg-violet" aria-hidden="true" /> Model estimate</span>
        <span className="flex items-center gap-1.5"><i className="h-1.5 w-1.5 rounded-full bg-dim" aria-hidden="true" /> Unknown or assumption</span>
      </div>
    </div>
  );
}

function FlowConnector({ label }: { label: string }) {
  return (
    <div className="flex h-9 items-center gap-3 px-4">
      <span className="font-mono text-[11px] text-dim">{label}</span>
      <span className="h-px flex-1 bg-line" aria-hidden="true" />
      <ArrowDown className="h-3.5 w-3.5 text-signal/60" aria-hidden="true" />
    </div>
  );
}

function SensitivityPanel({ sensitivity }: { sensitivity: NonNullable<SimulationResult["sensitivity"]> }) {
  const max = Math.max(1, ...sensitivity.drivers.flatMap((driver) => [Math.abs(driver.effect_low), Math.abs(driver.effect_high)]));
  return (
    <Panel>
      <PanelHeader
        eyebrow="Sensitivity analysis"
        title="What the model depends on"
        description="A local one-at-a-time perturbation. This is model-parameter influence, not a causal effect on your health."
        action={<Badge tone="violet">Not causal</Badge>}
      />
      <div className="space-y-3 p-5">
        <div className="grid grid-cols-[minmax(0,1fr)_minmax(56px,1fr)_80px] gap-3 font-mono text-[11px] text-dim sm:grid-cols-[150px_1fr_110px]">
          <span>Model input</span>
          <span className="flex justify-between"><span>-{max.toFixed(0)}%</span><span className="hidden sm:inline">Effect on output</span><span>+{max.toFixed(0)}%</span></span>
          <span className="text-right">Low / high</span>
        </div>
        {sensitivity.drivers.map((driver) => {
          const lowPosition = 50 + (driver.effect_low / max) * 45;
          const highPosition = 50 + (driver.effect_high / max) * 45;
          const left = Math.min(lowPosition, highPosition);
          const width = Math.abs(highPosition - lowPosition);
          return (
            <div key={driver.parameter} className="grid grid-cols-[minmax(0,1fr)_minmax(56px,1fr)_80px] items-center gap-3 sm:grid-cols-[150px_1fr_110px]">
              <div className="min-w-0">
                <div className="truncate font-mono text-[12px] text-muted">{driver.parameter}</div>
                <div className="mt-0.5 font-mono text-[11px] text-dim">{driver.change}{!driver.known && ", assumption"}</div>
              </div>
              <div className="relative h-5">
                <div className="absolute inset-x-0 top-1/2 h-px bg-line" />
                <div className="absolute top-1/2 h-px -translate-y-1/2 bg-amber/50" style={{ left: `${left}%`, width: `${width}%` }} />
                <span className="absolute top-1/2 h-3 w-px -translate-x-1/2 -translate-y-1/2 bg-amber" style={{ left: `${lowPosition}%` }} />
                <span className="absolute top-1/2 h-3 w-px -translate-x-1/2 -translate-y-1/2 bg-amber" style={{ left: `${highPosition}%` }} />
                <span className="absolute bottom-0 left-1/2 h-2 w-px -translate-x-1/2 bg-line" />
              </div>
              <div className="text-right font-mono text-[12px] text-amber">
                <span>{driver.effect_low > 0 ? "+" : ""}{driver.effect_low}%</span>
                <span className="mx-1 text-dim">/</span>
                <span>{driver.effect_high > 0 ? "+" : ""}{driver.effect_high}%</span>
              </div>
            </div>
          );
        })}
        <p className="border-t border-line pt-3 text-[12px] leading-relaxed text-dim">{sensitivity.method} {sensitivity.note}</p>
      </div>
    </Panel>
  );
}

function WhatIfSkeleton() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center" role="status" aria-live="polite">
      <LoaderCircle className="h-5 w-5 animate-spin text-signal" aria-hidden="true" />
      <p className="mt-3 font-mono text-[12px] text-dim">Loading your recorded context</p>
    </div>
  );
}

export default function WhatIfPage() {
  return (
    <Suspense fallback={<WhatIfSkeleton />}>
      <WhatIfContent />
    </Suspense>
  );
}
