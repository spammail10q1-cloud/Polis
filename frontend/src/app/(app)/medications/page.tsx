"use client";

import { useMemo, useState } from "react";
import {
  BookOpen,
  Pill,
  Plus,
  Search,
  ShieldAlert,
  Trash2,
} from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Panel, PanelHeader, PanelBody, LoadError, Skeleton } from "@/components/ui/panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { Sheet } from "@/components/ui/sheet";
import { Tabs } from "@/components/ui/misc";
import { useQuery } from "@/lib/use-query";
import { useToast } from "@/components/toast";
import { apiDelete, apiPatch, apiPost, errorMessage } from "@/lib/api";
import type { Exposure, Interaction, MedicationCatalog } from "@/lib/types";
import { cn, formatDate } from "@/lib/format";

function sentenceCase(value: string): string {
  const text = value.replaceAll("_", " ").trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : text;
}

export default function MedicationsPage() {
  const { push } = useToast();
  const exposures = useQuery<Exposure[]>("/medications");
  const interactions = useQuery<Interaction[]>("/medications/interactions");
  const catalog = useQuery<MedicationCatalog[]>("/medications/catalog");
  const [tab, setTab] = useState<"active" | "history" | "interactions">("active");
  const [addOpen, setAddOpen] = useState(false);
  const [selected, setSelected] = useState<Exposure | null>(null);

  const active = (exposures.data ?? []).filter((item) => item.status === "active");
  const history = (exposures.data ?? []).filter((item) => item.status !== "active");

  const stopMedication = async (exposure: Exposure) => {
    if (!window.confirm(`Mark ${exposure.name} as stopped? This records your report; it does not change any prescription.`)) return;
    try {
      await apiPatch(`/medications/${exposure.id}`, { status: "stopped", end_date: new Date().toISOString().slice(0, 10) });
      push(`${exposure.name} marked as stopped.`, "success");
      setSelected(null);
      exposures.refresh();
      interactions.refresh();
    } catch (error) {
      push(errorMessage(error), "error");
    }
  };

  const deleteMedication = async (exposure: Exposure) => {
    if (!window.confirm(`Delete the record for ${exposure.name}? This removes it from your medication history.`)) return;
    try {
      await apiDelete(`/medications/${exposure.id}`);
      push("Medication record deleted.", "success");
      setSelected(null);
      exposures.refresh();
      interactions.refresh();
    } catch (error) {
      push(errorMessage(error), "error");
    }
  };

  if (exposures.loading && !exposures.data) return <MedicationSkeleton />;
  if (exposures.error && !exposures.data) return <LoadError message={exposures.error} onRetry={exposures.refresh} />;

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Exposure and interaction context"
        title="Medications"
        description="A record of what you report taking, never a prescription. Interaction screening surfaces known signals for professional review; absence of a flag is not proof of safety."
        actions={
          <Button variant="primary" onClick={() => setAddOpen(true)}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            Add medication
          </Button>
        }
      />

      <div className="mb-4 grid grid-cols-2 gap-px border border-line bg-line sm:grid-cols-4">
        <MedStat label="Active entries" value={String(active.length)} note="User-reported" />
        <MedStat label="Interaction signals" value={String(interactions.data?.length ?? 0)} note="Curated pairs" tone={interactions.data?.length ? "amber" : undefined} />
        <MedStat label="Serious signals" value={String((interactions.data ?? []).filter((item) => ["major", "contraindicated"].includes(item.severity)).length)} note="Professional review" tone="amber" />
        <MedStat label="History entries" value={String(history.length)} note="Stopped or paused" />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.45fr)_minmax(0,0.7fr)]">
        <Panel>
          <Tabs
            value={tab}
            onChange={setTab}
            items={[
              { value: "active", label: "Active", count: active.length },
              { value: "interactions", label: "Interactions", count: interactions.data?.length ?? 0 },
              { value: "history", label: "History", count: history.length },
            ]}
          />
          {tab === "active" && (
            <div className="divide-y divide-line">
              {active.map((exposure) => (
                <button
                  key={exposure.id}
                  onClick={() => setSelected(exposure)}
                  className="group grid w-full grid-cols-1 gap-3 px-5 py-4 text-left transition-colors hover:bg-raised/40 sm:grid-cols-[minmax(0,1fr)_160px_150px]"
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Pill className="h-4 w-4 text-dim" aria-hidden="true" />
                      <span className="text-[16px] text-mist">{exposure.name}</span>
                      {exposure.is_synthetic && <Badge tone="amber">Synthetic</Badge>}
                    </div>
                    <div className="mt-1 text-[13px] text-muted">{exposure.drug_class}</div>
                    {exposure.enzyme_pathways.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {exposure.enzyme_pathways.slice(0, 4).map((pathway) => (
                          <span key={pathway.gene} className="border border-line px-1.5 py-0.5 font-mono text-[11px] text-dim">
                            {pathway.gene}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="min-w-0">
                    <div className="font-mono text-[13px] text-mist">{exposure.dose_text}</div>
                    <div className="mt-1 text-[12px] text-dim">{exposure.frequency}, {exposure.route}</div>
                    {exposure.start_date && <div className="mt-1 text-[12px] text-dim">Since {formatDate(exposure.start_date)}</div>}
                  </div>
                  <div className="text-left sm:text-right">
                    <div className="text-[12px] text-dim">Reason</div>
                    <div className="mt-0.5 line-clamp-2 text-[13px] text-muted">{exposure.reason ?? "Not recorded"}</div>
                  </div>
                </button>
              ))}
              {!active.length && (
                <div className="flex flex-col items-center px-6 py-16 text-center">
                  <Pill className="h-6 w-6 text-dim" aria-hidden="true" />
                  <p className="mt-3 text-[13px] text-muted">No active medications are recorded.</p>
                  <Button variant="secondary" className="mt-4" onClick={() => setAddOpen(true)}>Add your first entry</Button>
                </div>
              )}
            </div>
          )}

          {tab === "interactions" && (
            <div className="divide-y divide-line">
              {(interactions.data ?? []).map((interaction) => (
                <div key={interaction.id} className="px-5 py-4">
                  <div className="flex flex-wrap items-center gap-2.5">
                    <SeverityBadge severity={interaction.severity} />
                    <span className="text-[15px] text-mist">{interaction.drug_a} and {interaction.drug_b}</span>
                  </div>
                  <p className="mt-2 text-[13px] leading-relaxed text-mist/90">{interaction.effect}</p>
                  <p className="mt-1.5 text-[13px] leading-relaxed text-muted">{interaction.mechanism}</p>
                  <div className="mt-3 border-l border-amber/40 pl-3">
                    <div className="text-[12px] font-medium text-amber">Professional review</div>
                    <p className="mt-1 text-[13px] leading-relaxed text-muted">{interaction.management}</p>
                  </div>
                  <div className="mt-2.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12px] text-dim">
                    <BookOpen className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                    <span>{interaction.evidence_level}</span>
                    <span className="text-dim">{interaction.source_title}</span>
                  </div>
                </div>
              ))}
              {!interactions.data?.length && (
                <div className="px-5 py-12 text-center">
                  <ShieldAlert className="mx-auto h-5 w-5 text-mint" aria-hidden="true" />
                  <p className="mt-3 text-[13px] text-muted">No curated interaction was detected among active medications.</p>
                  <p className="mx-auto mt-1.5 max-w-md text-[12px] leading-relaxed text-dim">
                    This is not proof of safety. The curated list is not exhaustive, and interactions depend on dose,
                    timing, genetics, organ function and other factors.
                  </p>
                </div>
              )}
            </div>
          )}

          {tab === "history" && (
            <div className="divide-y divide-line">
              {history.map((exposure) => (
                <div key={exposure.id} className="flex flex-wrap items-center gap-3 px-5 py-3">
                  <Pill className="h-4 w-4 text-dim" aria-hidden="true" />
                  <div className="min-w-0 flex-1">
                    <div className="text-[15px] text-muted">{exposure.name}</div>
                    <div className="mt-0.5 text-[12px] text-dim">{exposure.dose_text}, {exposure.frequency}</div>
                  </div>
                  <Badge tone="muted">{sentenceCase(exposure.status)}</Badge>
                  {exposure.end_date && <span className="text-[12px] text-dim">Until {formatDate(exposure.end_date)}</span>}
                  <button
                    onClick={() => deleteMedication(exposure)}
                    className="flex h-11 w-11 items-center justify-center text-dim hover:text-danger"
                    aria-label={`Delete ${exposure.name}`}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                  </button>
                </div>
              ))}
              {!history.length && <div className="px-5 py-12 text-center text-[13px] text-dim">No stopped or paused medication records.</div>}
            </div>
          )}
        </Panel>

        <div className="space-y-4">
          <Panel>
            <PanelHeader eyebrow="Interaction screen" title="What POLIS checks" />
            <PanelBody className="space-y-3">
              <p className="text-[13px] leading-relaxed text-muted">
                The local curated interaction set covers clinically recognized pairs among the demonstration formulary.
                It is not a comprehensive interaction database.
              </p>
              <ul className="space-y-1.5">
                {["CYP inhibition and induction", "Prodrug activation", "Renal and hepatic clearance", "Pharmacodynamic overlap"].map((item) => (
                  <li key={item} className="border-l border-line pl-3 text-[13px] text-muted">
                    {item}
                  </li>
                ))}
              </ul>
              <Callout tone="warning" title="Do not stop a medicine alone">
                A flagged interaction is a prompt for professional review, not an instruction to stop or change anything.
              </Callout>
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader eyebrow="Medication safety" title="Limitations" />
            <PanelBody className="space-y-2">
              {[
                "The list is user-reported; it may be incomplete or inaccurate.",
                "Dose, timing and adherence can change interaction magnitude.",
                "Pharmacogenomics and organ function modify individual exposure.",
                "Absence of an interaction flag does not establish safety.",
              ].map((text) => (
                <p key={text} className="text-[13px] leading-relaxed text-muted">{text}</p>
              ))}
            </PanelBody>
          </Panel>
        </div>
      </div>

      <AddMedicationSheet
        open={addOpen}
        onClose={() => setAddOpen(false)}
        catalog={catalog.data ?? []}
        onAdded={() => {
          setAddOpen(false);
          exposures.refresh();
          interactions.refresh();
        }}
      />

      <Sheet
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        title={selected?.name ?? "Medication"}
        eyebrow={selected ? `${selected.drug_class}, recorded use` : undefined}
      >
        {selected && (
          <MedicationDetail
            exposure={selected}
            onStop={() => stopMedication(selected)}
            onDelete={() => deleteMedication(selected)}
          />
        )}
      </Sheet>
    </div>
  );
}

function MedicationDetail({ exposure, onStop, onDelete }: { exposure: Exposure; onStop: () => void; onDelete: () => void }) {
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-mono text-[24px] text-mist">{exposure.dose_text}</div>
          <div className="mt-1 text-[13px] text-muted">{exposure.frequency}, {exposure.route}</div>
          <div className="mt-2 flex flex-wrap gap-2">
            <Badge tone="signal">Active record</Badge>
            {exposure.is_synthetic && <Badge tone="amber">Synthetic</Badge>}
          </div>
        </div>
        <div className="text-right">
          <div className="text-[12px] text-dim">Recorded since</div>
          <div className="mt-1 font-mono text-[13px] text-muted">{exposure.start_date ? formatDate(exposure.start_date) : "Not recorded"}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-px border border-line bg-line sm:grid-cols-2">
        <div className="bg-panel p-3.5">
          <div className="text-[12px] text-dim">Reason recorded</div>
          <div className="mt-1.5 text-[13px] text-mist">{exposure.reason ?? "Not recorded"}</div>
        </div>
        <div className="bg-panel p-3.5">
          <div className="text-[12px] text-dim">Prescriber context</div>
          <div className="mt-1.5 text-[13px] text-mist">{exposure.prescriber_specialty ?? "Not recorded"}</div>
        </div>
      </div>

      <div>
        <div className="mb-2 text-[12px] text-dim">Enzyme and transporter context</div>
        <div className="space-y-1.5">
          {exposure.enzyme_pathways.map((pathway) => (
            <div key={`${pathway.gene}-${pathway.role}`} className="flex flex-wrap items-center justify-between gap-2 border border-line px-3 py-2">
              <span className="font-mono text-[12px] text-signal">{pathway.gene}</span>
              <span className="text-right text-[12px] text-muted">{pathway.role}</span>
            </div>
          ))}
          {!exposure.enzyme_pathways.length && <p className="text-[13px] text-dim">No curated enzyme pathway is recorded for this medication.</p>}
        </div>
      </div>

      {exposure.notes && (
        <div>
          <div className="mb-2 text-[12px] text-dim">Notes</div>
          <p className="text-[13px] leading-relaxed text-muted">{exposure.notes}</p>
        </div>
      )}

      <Callout tone="warning" title="This is a record, not a prescription">
        POLIS does not tell you to start, stop or change a medicine. If you are experiencing a side effect or need a
        regimen change, contact your prescriber or pharmacist. For urgent symptoms, seek emergency care.
      </Callout>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
        <button onClick={onDelete} className="btn btn-ghost text-danger hover:bg-danger/[0.08]">
          <Trash2 className="h-4 w-4" aria-hidden="true" /> Delete
        </button>
        <Button variant="secondary" onClick={onStop}>Mark as stopped</Button>
      </div>
    </div>
  );
}

function AddMedicationSheet({
  open,
  onClose,
  catalog,
  onAdded,
}: {
  open: boolean;
  onClose: () => void;
  catalog: MedicationCatalog[];
  onAdded: () => void;
}) {
  const { push } = useToast();
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<MedicationCatalog | null>(null);
  const [dose, setDose] = useState("");
  const [frequency, setFrequency] = useState("once daily");
  const [route, setRoute] = useState("oral");
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);

  const filtered = useMemo(
    () => catalog.filter((item) => `${item.name} ${item.generic_name} ${item.drug_class}`.toLowerCase().includes(query.toLowerCase())).slice(0, 8),
    [catalog, query],
  );

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selected) {
      push("Select a medication from the curated catalog.", "error");
      return;
    }
    if (!dose.trim()) {
      push("Enter the dose exactly as you understand it.", "error");
      return;
    }
    setSaving(true);
    try {
      await apiPost("/medications", {
        medication_id: selected.id,
        dose_text: dose,
        frequency,
        route,
        reason: reason || null,
        start_date: new Date().toISOString().slice(0, 10),
      });
      push("Medication record added.", "success");
      setSelected(null);
      setDose("");
      setReason("");
      setQuery("");
      onAdded();
    } catch (error) {
      push(errorMessage(error), "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Sheet open={open} onClose={onClose} title="Add a medication record" eyebrow="What you report taking" width="max-w-xl">
      <form onSubmit={submit} className="space-y-4">
        <Callout tone="info" title="Use the exact name and dose">
          This is not a prescription. It helps POLIS screen evidence and interactions. Ask your pharmacist if you are
          unsure about a product or dose.
        </Callout>
        <div>
          <label htmlFor="medication-catalog-search" className="mb-2 block text-[13px] text-mist">Curated catalog</label>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-dim" aria-hidden="true" />
            <input
              id="medication-catalog-search"
              className="input pl-9"
              placeholder="Search medication"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
          <div className="mt-2 max-h-[220px] overflow-y-auto border border-line">
            {filtered.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setSelected(item)}
                aria-pressed={selected?.id === item.id}
                className={cn(
                  "flex w-full items-center justify-between gap-3 border-b border-line px-3.5 py-3 text-left transition-colors last:border-b-0 hover:bg-raised/40",
                  selected?.id === item.id && "border-l-2 border-l-signal bg-signal/[0.05]",
                )}
              >
                <span className="min-w-0">
                  <span className="block truncate text-[15px] text-mist">{item.name}</span>
                  <span className="mt-0.5 block truncate text-[12px] text-dim">{item.drug_class}</span>
                </span>
                <Badge tone={item.is_simulation_eligible ? "violet" : "muted"}>
                  {item.is_simulation_eligible ? "Simulation available" : "No simulation"}
                </Badge>
              </button>
            ))}
            {!filtered.length && (
              <div className="px-3.5 py-5">
                <p className="text-[13px] text-muted">No catalog match.</p>
                <p className="mt-1 text-[12px] text-dim">Try a generic name or a drug class.</p>
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label>
            <span className="mb-2 block text-[13px] text-mist">Dose, as recorded</span>
            <input className="input" value={dose} onChange={(event) => setDose(event.target.value)} placeholder="e.g. 20 mg" required />
          </label>
          <label>
            <span className="mb-2 block text-[13px] text-mist">Frequency</span>
            <input className="input" value={frequency} onChange={(event) => setFrequency(event.target.value)} />
          </label>
          <label>
            <span className="mb-2 block text-[13px] text-mist">Route</span>
            <select className="input" value={route} onChange={(event) => setRoute(event.target.value)}>
              {["oral", "inhalation", "topical", "intravenous", "subcutaneous", "other"].map((item) => <option key={item}>{item}</option>)}
            </select>
          </label>
          <label>
            <span className="mb-2 block text-[13px] text-mist">Reason, optional</span>
            <input className="input" value={reason} onChange={(event) => setReason(event.target.value)} placeholder="e.g. blood pressure" />
          </label>
        </div>

        <div className="flex justify-end gap-2 border-t border-line pt-4">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" loading={saving} disabled={!selected}>Add record</Button>
        </div>
      </form>
    </Sheet>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const tone = severity === "contraindicated" || severity === "major" ? "danger" : severity === "moderate" ? "amber" : "muted";
  const label = severity === "contraindicated" ? "Contraindicated" : severity === "major" ? "Major" : severity === "moderate" ? "Moderate" : severity === "minor" ? "Minor" : severity.replaceAll("_", " ");
  return <Badge tone={tone}>{label}</Badge>;
}

function MedStat({ label, value, note, tone }: { label: string; value: string; note: string; tone?: "amber" }) {
  return (
    <div className="bg-panel px-4 py-3.5">
      <div className="text-[12px] text-dim">{label}</div>
      <div className={cn("mt-1.5 number text-[22px]", tone === "amber" ? "text-amber" : "text-mist")}>{value}</div>
      <div className="mt-0.5 text-[12px] text-dim">{note}</div>
    </div>
  );
}

function MedicationSkeleton() {
  return (
    <div>
      <Skeleton className="mb-3 h-3 w-56" />
      <Skeleton className="mb-8 h-10 w-[280px]" />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.45fr_0.7fr]">
        <Skeleton className="h-[500px]" />
        <Skeleton className="h-[300px]" />
      </div>
    </div>
  );
}
