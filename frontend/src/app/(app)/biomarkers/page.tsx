"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  ArrowUpFromLine,
  FileText,
  FlaskConical,
  Plus,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Trash2,
} from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { TrendChart } from "@/components/charts/trend-chart";
import { Sparkline } from "@/components/charts/sparkline";
import { Panel, PanelHeader, LoadError, Skeleton } from "@/components/ui/panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { StatusPill } from "@/components/ui/status";
import { Sheet } from "@/components/ui/sheet";
import { useQuery } from "@/lib/use-query";
import { apiDelete, errorMessage, uploadFile, apiPost } from "@/lib/api";
import { useToast } from "@/components/toast";
import type { Biomarker, LabResult, Trend } from "@/lib/types";
import { categoryLabel, cn, formatDate, formatNumber, formatRange, relativeTime } from "@/lib/format";

function sentenceCase(value: string): string {
  const text = value.replaceAll("_", " ").trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : text;
}

type UploadResponse = {
  imported: number;
  skipped: number;
  warnings: string[];
  errors: string[];
  results: LabResult[];
};

const categories = ["all", "liver", "kidney", "metabolic", "inflammatory", "hematology", "hormonal", "nutritional", "electrolytes"];

const tableHeadings = ["Biomarker", "Latest", "Laboratory interval", "Status", "Trend", "Measured", "Source"];

function BiomarkersContent() {
  const params = useSearchParams();
  const requestedCode = params.get("code");
  const { push } = useToast();
  const labs = useQuery<LabResult[]>("/labs?latest_only=true");
  const trends = useQuery<Trend[]>("/labs/trends");
  const biomarkers = useQuery<Biomarker[]>("/labs/biomarkers");
  const [category, setCategory] = useState<string>("all");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<LabResult | null>(null);
  const [manualOpen, setManualOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);

  useEffect(() => {
    if (!requestedCode || !labs.data) return;
    const match = labs.data.find((lab) => lab.code === requestedCode);
    if (match) setSelected(match);
  }, [requestedCode, labs.data]);

  const trendMap = useMemo(() => new Map((trends.data ?? []).map((trend) => [trend.code, trend])), [trends.data]);
  const filtered = useMemo(() => {
    const categoryOrder = ["liver", "metabolic", "kidney", "inflammatory", "hematology", "hormonal", "nutritional", "electrolytes"];
    const codeOrder: Record<string, number> = {
      alt: 0, ast: 1, alp: 2, ggt: 3, bilirubin: 4, albumin: 5,
      ldl: 0, hdl: 1, total_cholesterol: 2, triglycerides: 3, apoB: 4, hba1c: 5, glucose: 6, insulin: 7,
      egfr: 0, creatinine: 1, cystatin_c: 2, bun: 3, urine_acr: 4,
      hs_crp: 0, esr: 1,
      hemoglobin: 0, hematocrit: 1, wbc: 2, rbc: 3, platelets: 4, ferritin: 5,
      tsh: 0, free_t4: 1, free_t3: 2, cortisol: 3, testosterone: 4, estradiol: 5,
      vitamin_d: 0, vitamin_b12: 1,
      sodium: 0, potassium: 1, calcium: 2, magnesium: 3,
    };
    return (labs.data ?? [])
      .filter((lab) => {
        const categoryMatch = category === "all" || lab.category === category;
        const queryMatch = !query || `${lab.name} ${lab.code}`.toLowerCase().includes(query.toLowerCase());
        return categoryMatch && queryMatch;
      })
      .sort((a, b) => {
        const categoryDiff = categoryOrder.indexOf(a.category) - categoryOrder.indexOf(b.category);
        if (categoryDiff !== 0) return categoryDiff;
        const codeDiff = (codeOrder[a.code] ?? 99) - (codeOrder[b.code] ?? 99);
        return codeDiff !== 0 ? codeDiff : a.name.localeCompare(b.name);
      });
  }, [labs.data, category, query]);

  const abnormal = (labs.data ?? []).filter((lab) => lab.range_status === "high" || lab.range_status === "low").length;
  const selectedTrend = selected ? trendMap.get(selected.code) : undefined;
  const unavailable = (labs.data ?? []).filter((lab) => lab.range_status === "indeterminate").length;

  const reloadAll = () => {
    labs.refresh();
    trends.refresh();
  };

  const handleDelete = async (lab: LabResult) => {
    if (!window.confirm(`Delete the ${formatDate(lab.measured_at)} ${lab.name} result?`)) return;
    try {
      await apiDelete(`/labs/${lab.id}`);
      push("Laboratory result deleted.", "success");
      setSelected(null);
      reloadAll();
    } catch (error) {
      push(errorMessage(error), "error");
    }
  };

  if (labs.loading && !labs.data) return <BiomarkerSkeleton />;
  if (labs.error && !labs.data) return <LoadError message={labs.error} onRetry={labs.refresh} />;

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Laboratory record, source-specific intervals"
        title="Biomarkers"
        description="Every result keeps its own unit, reference interval, date, source and quality status. POLIS never merges incompatible ranges."
        actions={
          <>
            <Button onClick={() => setUploadOpen(true)} variant="secondary">
              <ArrowUpFromLine className="h-4 w-4" aria-hidden="true" />
              Import report
            </Button>
            <Button onClick={() => setManualOpen(true)} variant="primary">
              <Plus className="h-4 w-4" aria-hidden="true" />
              Add result
            </Button>
          </>
        }
      />

      <div className="mb-4 grid grid-cols-2 gap-px border border-line bg-line sm:grid-cols-4">
        <SummaryCell label="Latest markers" value={String(labs.data?.length ?? 0)} note="Distinct biomarkers" />
        <SummaryCell label="Outside interval" value={String(abnormal)} note="Review observations" tone="amber" />
        <SummaryCell label="No usable interval" value={String(unavailable)} note="Status indeterminate" tone="muted" />
        <SummaryCell label="Repeated series" value={String((trends.data ?? []).filter((trend) => trend.points.length > 1).length)} note="Historical trends" />
      </div>

      <Panel>
        <PanelHeader
          title="Latest results by system"
          description="Each row keeps the unit, interval and source recorded with that result."
          action={
            <button
              onClick={reloadAll}
              className="btn btn-ghost h-11 w-11 p-0"
              aria-label="Refresh laboratory results"
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
            </button>
          }
        />

        <div className="flex flex-col gap-3 border-b border-line px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
          <div
            className="flex flex-wrap gap-1"
            role="group"
            aria-label="Filter results by biological system"
          >
            {categories.map((item) => (
              <button
                key={item}
                onClick={() => setCategory(item)}
                aria-pressed={category === item}
                className={cn(
                  "min-h-11 shrink-0 border px-3 py-2 text-[13px] transition-colors sm:min-h-9",
                  category === item
                    ? "border-signal/40 bg-signal/[0.06] text-signal"
                    : "border-transparent text-muted hover:border-line hover:text-mist",
                )}
              >
                {item === "all" ? "All systems" : categoryLabel(item)}
              </button>
            ))}
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <label htmlFor="biomarker-filter" className="text-[12px] text-dim">
              Filter
            </label>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-dim" aria-hidden="true" />
              <input
                id="biomarker-filter"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Markers by name or code"
                className="input h-11 w-full pl-9 sm:w-[240px]"
              />
            </div>
          </div>
        </div>

        {(labs.data?.length ?? 0) === 0 ? (
          <div className="flex flex-col items-center px-6 py-16 text-center">
            <FlaskConical className="h-6 w-6 text-dim" aria-hidden="true" />
            <h2 className="mt-3 text-[16px] text-mist">No laboratory results yet</h2>
            <p className="mt-2 max-w-md text-[13px] leading-relaxed text-muted">
              Add a result manually, import a CSV or FHIR Observation, or upload a text-based PDF report. Units and
              reference intervals are required; POLIS will not guess them.
            </p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              <Button variant="secondary" onClick={() => setUploadOpen(true)}>Import report</Button>
              <Button variant="primary" onClick={() => setManualOpen(true)}>Add result</Button>
            </div>
          </div>
        ) : (
          <div>
            <div
              className="scroll-area overflow-x-auto focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-signal"
              tabIndex={0}
              role="region"
              aria-label="Laboratory results table. Scroll horizontally to see every column."
            >
              <table className="w-full min-w-[900px] border-collapse text-left">
                <caption className="sr-only">
                  Latest laboratory results. Each row shows the value, source interval, status, trend and provenance.
                </caption>
                <thead>
                  <tr className="border-b border-line bg-ink/40">
                    {tableHeadings.map((heading) => (
                      <th
                        key={heading}
                        scope="col"
                        className="whitespace-nowrap px-4 py-3 text-[12px] font-medium text-dim"
                      >
                        {heading}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((lab) => {
                    const trend = trendMap.get(lab.code);
                    return (
                      <tr
                        key={lab.id}
                        onClick={() => setSelected(lab)}
                        className="cursor-pointer border-b border-line transition-colors last:border-0 hover:bg-raised/40"
                      >
                        <td className="px-4 py-3.5">
                          <button
                            type="button"
                            onClick={() => setSelected(lab)}
                            aria-label={`Open ${lab.name} result`}
                            className="min-h-11 text-left text-[13px] text-mist hover:text-signal"
                          >
                            {lab.name}
                          </button>
                          <div className="mt-1 text-[12px] text-dim">
                            <span className="font-mono">{lab.code}</span>
                            <span>, {categoryLabel(lab.category)}</span>
                            {lab.quality_status === "needs_review" && <span className="text-amber">, review needed</span>}
                          </div>
                        </td>
                        <td className="whitespace-nowrap px-4 py-3.5">
                          <span className="number text-[14px] text-mist">
                            {formatNumber(lab.value, Math.abs(lab.value) < 10 ? 2 : 1)}
                          </span>
                          <span className="ml-1.5 font-mono text-[12px] text-dim">{lab.unit}</span>
                          {lab.converted_from && (
                            <div className="mt-0.5 text-[11px] text-dim">Converted from {lab.converted_from}</div>
                          )}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3.5 font-mono text-[12px] text-muted">
                          {formatRange(lab.ref_low, lab.ref_high, lab.unit)}
                        </td>
                        <td className="px-4 py-3.5"><StatusPill status={lab.range_status} /></td>
                        <td className="px-4 py-3.5">
                          {trend && trend.points.length > 1 ? (
                            <Sparkline
                              values={trend.points.map((point) => point.value)}
                              height={24}
                              className="w-[76px]"
                              tone={lab.range_status === "high" || lab.range_status === "low" ? "amber" : "signal"}
                            />
                          ) : (
                            <span className="text-[12px] text-dim">One result</span>
                          )}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3.5">
                          <div className="font-mono text-[12px] text-muted">{formatDate(lab.measured_at)}</div>
                          <div className="mt-0.5 text-[11px] text-dim">{relativeTime(lab.measured_at)}</div>
                        </td>
                        <td className="max-w-[190px] px-4 py-3.5">
                          <div className="truncate text-[12px] text-muted" title={lab.source}>{lab.source}</div>
                          <div className="mt-0.5 text-[11px] text-dim">{sentenceCase(lab.quality_status)}</div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {!filtered.length && (
              <div className="border-t border-line px-6 py-14 text-center">
                <SlidersHorizontal className="mx-auto h-5 w-5 text-dim" aria-hidden="true" />
                <p className="mt-3 text-[13px] text-muted">No results match this filter.</p>
                <p className="mt-1 text-[12px] text-dim">Try another system, clear the search field or add a laboratory result.</p>
              </div>
            )}
          </div>
        )}
      </Panel>

      <Callout tone="info" title="Reference intervals are local to the laboratory" className="mt-4">
        POLIS classifies a result only against the interval supplied with that result. Population intervals shown in
        biomarker catalogs are orientation only and are never silently substituted. A result without a usable interval
        remains <span className="text-mist">indeterminate</span>.
      </Callout>

      <Sheet
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        title={selected?.name ?? "Biomarker"}
        eyebrow={selected ? `${categoryLabel(selected.category)}, ${selected.code}` : undefined}
      >
        {selected && (
          <BiomarkerDetail
            lab={selected}
            trend={selectedTrend}
            biomarker={biomarkers.data?.find((item) => item.code === selected.code)}
            onDelete={() => handleDelete(selected)}
          />
        )}
      </Sheet>

      <ManualEntrySheet
        open={manualOpen}
        onClose={() => setManualOpen(false)}
        biomarkers={biomarkers.data ?? []}
        onSaved={() => {
          setManualOpen(false);
          reloadAll();
        }}
      />

      <ImportSheet
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onImported={() => {
          reloadAll();
        }}
      />
    </div>
  );
}

function BiomarkerDetail({ lab, trend, biomarker, onDelete }: { lab: LabResult; trend?: Trend; biomarker?: Biomarker; onDelete: () => void }) {
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-baseline gap-2">
            <span className="number text-[34px] text-mist">{formatNumber(lab.value, Math.abs(lab.value) < 10 ? 2 : 1)}</span>
            <span className="font-mono text-[12px] text-dim">{lab.unit}</span>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <StatusPill status={lab.range_status} />
            {lab.is_synthetic && <Badge tone="amber">Synthetic</Badge>}
            {lab.quality_status === "needs_review" && <Badge tone="amber">Needs review</Badge>}
          </div>
        </div>
        <div className="text-right">
          <div className="font-mono text-[12px] text-muted">{formatDate(lab.measured_at)}</div>
          <div className="mt-0.5 font-mono text-[12px] text-dim">{relativeTime(lab.measured_at)}</div>
          <div className="mt-1 text-[12px] text-dim">{lab.source}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-px border border-line bg-line sm:grid-cols-2">
        <div className="bg-panel p-3.5">
          <div className="text-[12px] text-dim">Laboratory interval</div>
          <div className="mt-1.5 font-mono text-[13px] text-mist">{formatRange(lab.ref_low, lab.ref_high, lab.unit)}</div>
          {lab.ref_text && <div className="mt-1 text-[12px] text-dim">Reported as {lab.ref_text}</div>}
        </div>
        <div className="bg-panel p-3.5">
          <div className="text-[12px] text-dim">Quality and confidence</div>
          <div className="mt-1.5 text-[13px] text-mist">{sentenceCase(lab.quality_status)}</div>
          <div className="mt-1 text-[12px] text-dim">Model confidence {Math.round(lab.confidence * 100)}%</div>
        </div>
        {lab.converted_from && (
          <div className="bg-panel p-3.5 sm:col-span-2">
            <div className="text-[12px] text-dim">Unit conversion</div>
            <div className="mt-1 text-[13px] leading-relaxed text-muted">
              Entered in {lab.converted_from}; converted explicitly to the canonical unit. The original unit is retained
              in provenance.
            </div>
          </div>
        )}
      </div>

      {trend ? (
        <div className="border border-line pb-3 pt-3.5">
          <div className="mb-1 flex items-center justify-between gap-3 px-3.5">
            <span className="text-[12px] text-dim">Recorded history</span>
            <span className="font-mono text-[12px] text-dim">
              {trend.points.length} measurement{trend.points.length === 1 ? "" : "s"}
            </span>
          </div>
          <TrendChart trend={trend} height={220} />
          <p className="mt-1 px-3.5 text-[12px] leading-relaxed text-dim">{trend.interpretation}</p>
        </div>
      ) : (
        <Callout tone="neutral">Only one result is available, so no trend can be inferred.</Callout>
      )}

      <div>
        <div className="mb-2 text-[12px] text-dim">Context recorded with this result</div>
        {Object.keys(lab.context).length ? (
          <div className="divide-y divide-line border border-line">
            {Object.entries(lab.context).map(([key, value]) => (
              <div key={key} className="flex items-start justify-between gap-4 px-3.5 py-2.5">
                <span className="text-[12px] text-dim">{sentenceCase(key)}</span>
                <span className="text-right text-[13px] text-muted">{String(value)}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-[13px] text-dim">No additional context was supplied.</p>
        )}
      </div>

      {biomarker && (
        <div className="border-t border-line pt-4">
          <div className="mb-1.5 text-[12px] text-dim">About this marker</div>
          <p className="text-[13px] leading-relaxed text-muted">{biomarker.description}</p>
          <p className="mt-1.5 text-[12px] leading-relaxed text-dim">{biomarker.reference_note}</p>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
        <span className="font-mono text-[11px] text-dim">Result ID {lab.id}</span>
        <button onClick={onDelete} className="btn btn-ghost text-danger hover:bg-danger/[0.08]">
          <Trash2 className="h-4 w-4" aria-hidden="true" /> Delete result
        </button>
      </div>
    </div>
  );
}

function SummaryCell({ label, value, note, tone = "default" }: { label: string; value: string; note: string; tone?: "default" | "amber" | "muted" }) {
  return (
    <div className="bg-panel px-4 py-3.5">
      <div className="text-[12px] text-dim">{label}</div>
      <div className={cn("mt-1.5 number text-[22px]", tone === "amber" ? "text-amber" : tone === "muted" ? "text-muted" : "text-mist")}>{value}</div>
      <div className="mt-0.5 text-[12px] text-dim">{note}</div>
    </div>
  );
}

function ManualEntrySheet({
  open,
  onClose,
  biomarkers,
  onSaved,
}: {
  open: boolean;
  onClose: () => void;
  biomarkers: Biomarker[];
  onSaved: () => void;
}) {
  const { push } = useToast();
  const [code, setCode] = useState("alt");
  const [value, setValue] = useState("");
  const [unit, setUnit] = useState("U/L");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [refLow, setRefLow] = useState("");
  const [refHigh, setRefHigh] = useState("");
  const [source, setSource] = useState("Self-entered");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const selectedBiomarker = biomarkers.find((item) => item.code === code);

  useEffect(() => {
    if (selectedBiomarker) setUnit(selectedBiomarker.canonical_unit);
  }, [selectedBiomarker]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!value || Number(value) <= 0) {
      push("Enter a positive numeric value.", "error");
      return;
    }
    setSaving(true);
    try {
      await apiPost("/labs/manual", {
        code,
        value: Number(value),
        unit,
        measured_at: `${date}T12:00:00Z`,
        ref_low: refLow ? Number(refLow) : null,
        ref_high: refHigh ? Number(refHigh) : null,
        source: source || "Self-entered",
        notes: notes || null,
      });
      push("Laboratory result added. It is marked self-reported.", "success");
      setValue("");
      setRefLow("");
      setRefHigh("");
      setNotes("");
      onSaved();
    } catch (error) {
      push(errorMessage(error), "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Sheet open={open} onClose={onClose} title="Add a laboratory result" eyebrow="Manual entry" width="max-w-xl">
      <form onSubmit={submit} className="space-y-4">
        <Callout tone="warning">
          Enter values exactly as reported by the laboratory. If you do not have a reference interval, leave it blank.
          The result will remain indeterminate rather than being compared to a population range.
        </Callout>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label className="sm:col-span-2">
            <span className="mb-2 block text-[13px] text-mist">Biomarker</span>
            <select className="input" value={code} onChange={(event) => setCode(event.target.value)}>
              {biomarkers.map((item) => (
                <option key={item.code} value={item.code}>{item.name} ({item.code})</option>
              ))}
            </select>
          </label>
          <label>
            <span className="mb-2 block text-[13px] text-mist">Value</span>
            <input className="input" type="number" step="any" value={value} onChange={(event) => setValue(event.target.value)} required />
          </label>
          <label>
            <span className="mb-2 block text-[13px] text-mist">Unit</span>
            <input className="input" value={unit} onChange={(event) => setUnit(event.target.value)} required />
            {selectedBiomarker && <span className="mt-1 block text-[12px] text-dim">Canonical unit: {selectedBiomarker.canonical_unit}</span>}
          </label>
          <label>
            <span className="mb-2 block text-[13px] text-mist">Measurement date</span>
            <input className="input" type="date" value={date} onChange={(event) => setDate(event.target.value)} max={new Date().toISOString().slice(0, 10)} required />
          </label>
          <label>
            <span className="mb-2 block text-[13px] text-mist">Laboratory or source</span>
            <input className="input" value={source} onChange={(event) => setSource(event.target.value)} />
          </label>
          <label>
            <span className="mb-2 block text-[13px] text-mist">Reference low</span>
            <input className="input" type="number" step="any" value={refLow} onChange={(event) => setRefLow(event.target.value)} placeholder="Optional" />
          </label>
          <label>
            <span className="mb-2 block text-[13px] text-mist">Reference high</span>
            <input className="input" type="number" step="any" value={refHigh} onChange={(event) => setRefHigh(event.target.value)} placeholder="Optional" />
          </label>
          <label className="sm:col-span-2">
            <span className="mb-2 block text-[13px] text-mist">Context and notes</span>
            <textarea className="input min-h-20" value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Fasting state, medication timing, assay notes" />
          </label>
        </div>
        <div className="flex justify-end gap-2 border-t border-line pt-4">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" loading={saving}>Add result</Button>
        </div>
      </form>
    </Sheet>
  );
}

function FileField({
  id,
  accept,
  label,
  hint,
  file,
  onChange,
}: {
  id: string;
  accept: string;
  label: string;
  hint: string;
  file: File | null;
  onChange: React.ChangeEventHandler<HTMLInputElement>;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-2 block text-[13px] text-mist">{label}</label>
      <input
        id={id}
        type="file"
        accept={accept}
        aria-describedby={`${id}-hint`}
        onChange={onChange}
        className="block min-h-11 w-full cursor-pointer border border-line bg-ink px-3 py-2 text-[13px] text-muted file:mr-3 file:min-h-9 file:cursor-pointer file:rounded-[2px] file:border file:border-line file:bg-raised file:px-3 file:py-1.5 file:text-[13px] file:text-mist"
      />
      <p id={`${id}-hint`} className="mt-1.5 text-[12px] text-dim">{file ? file.name : hint}</p>
    </div>
  );
}

function ImportSheet({ open, onClose, onImported }: { open: boolean; onClose: () => void; onImported: () => void }) {
  const { push } = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) return;
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const response = await uploadFile<UploadResponse>("/labs/upload", file);
      setResult(response);
      push(`${response.imported} result${response.imported === 1 ? "" : "s"} imported.`, "success");
      onImported();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setUploading(false);
    }
  };

  return (
    <Sheet open={open} onClose={onClose} title="Import a laboratory report" eyebrow="CSV, FHIR or PDF" width="max-w-xl">
      <form onSubmit={submit} className="space-y-4">
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          {[
            { type: "CSV", detail: "Code, value, unit, date and reference interval columns." },
            { type: "FHIR JSON", detail: "Observation resources in a Bundle, with valueQuantity." },
            { type: "PDF", detail: "Text-based reports only; heuristic extraction, marked for review." },
          ].map((item) => (
            <div key={item.type} className="border border-line p-3">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-signal/80" aria-hidden="true" />
                <span className="text-[13px] text-mist">{item.type}</span>
              </div>
              <p className="mt-1.5 text-[12px] leading-relaxed text-dim">{item.detail}</p>
            </div>
          ))}
        </div>

        <FileField
          id="biomarker-report-file"
          accept=".csv,.json,.pdf,text/csv,application/json,application/pdf"
          label="Report file"
          hint="CSV, JSON or a text-based PDF. Maximum 12 MB."
          file={file}
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />

        {error && (
          <div className="border border-danger/30 bg-danger/[0.05] px-3.5 py-2.5 text-[13px] leading-relaxed text-danger">
            {error}
          </div>
        )}
        {result && (
          <div className="space-y-1.5 border border-mint/25 bg-mint/[0.04] px-3.5 py-3">
            <div className="text-[13px] font-medium text-mint">
              {result.imported} imported, {result.skipped} skipped
            </div>
            {result.warnings.map((warning) => (
              <p key={warning} className="text-[12px] leading-relaxed text-muted">{warning}</p>
            ))}
            {result.errors.map((item) => (
              <p key={item} className="text-[12px] leading-relaxed text-amber">{item}</p>
            ))}
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
          <span className="text-[12px] text-dim">Uploads are processed locally by the API.</span>
          <div className="flex gap-2">
            <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
            <Button type="submit" variant="primary" loading={uploading} disabled={!file}>Import</Button>
          </div>
        </div>

        <Callout tone="warning">
          PDF extraction is heuristic. Every PDF-derived result is marked for review. Verify values, units, dates and
          reference intervals against the original report before relying on them.
        </Callout>
      </form>
    </Sheet>
  );
}

function BiomarkerSkeleton() {
  return (
    <div>
      <Skeleton className="mb-3 h-3 w-56" />
      <Skeleton className="mb-8 h-10 w-[300px]" />
      <Skeleton className="mb-4 h-16 w-full" />
      <Skeleton className="h-[520px] w-full" />
    </div>
  );
}

export default function BiomarkersPage() {
  return (
    <Suspense fallback={<BiomarkerSkeleton />}>
      <BiomarkersContent />
    </Suspense>
  );
}
