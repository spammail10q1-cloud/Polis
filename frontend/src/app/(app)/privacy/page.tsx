"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowDownToLine,
  CheckCircle2,
  Database,
  Fingerprint,
  LoaderCircle,
  LockKeyhole,
  Network,
  ScrollText,
  ShieldCheck,
  Trash2,
  Users,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PageHeader } from "@/components/page-header";
import { Panel, LoadError } from "@/components/ui/panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { Meter, Tabs } from "@/components/ui/misc";
import { Sheet } from "@/components/ui/sheet";
import { useQuery } from "@/lib/use-query";
import { useAuth } from "@/components/auth-provider";
import { useToast } from "@/components/toast";
import { apiPatch, apiPost, downloadExport, errorMessage } from "@/lib/api";
import type { AuditEntry, Consent, ConsentState, FederatedResult } from "@/lib/types";
import { cn, formatDate, formatDateTime } from "@/lib/format";

type FederatedResponse = FederatedResult;

const consentLabels: Record<string, string> = {
  ai_processing: "AI processing",
  research_participation: "Research participation",
  federated_learning: "Federated learning",
  analytics: "Product analytics",
};

export default function PrivacyPage() {
  const router = useRouter();
  const { user, refresh: refreshAuth } = useAuth();
  const { push } = useToast();
  const state = useQuery<ConsentState>("/privacy/consent");
  const audit = useQuery<AuditEntry[]>("/privacy/audit");
  const [tab, setTab] = useState<"consent" | "federated" | "audit">("consent");
  const [updating, setUpdating] = useState<string | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [federatedRunning, setFederatedRunning] = useState(false);
  const [federatedResult, setFederatedResult] = useState<FederatedResponse | null>(null);

  if (state.loading && !state.data) return <PrivacyLoading />;
  if (state.error && !state.data) return <LoadError message={state.error} onRetry={state.refresh} />;
  if (!state.data) return null;

  const consent = state.data.consent;
  const budget = state.data.privacy_budget;

  const toggle = async (key: keyof Consent, value: boolean) => {
    setUpdating(key);
    try {
      await apiPatch("/privacy/consent", { [key]: value });
      await state.refresh();
      await refreshAuth();
      push(`${consentLabels[key] ?? key} ${value ? "enabled" : "disabled"}.`, "success");
    } catch (error) {
      push(errorMessage(error), "error");
    } finally {
      setUpdating(null);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const blob = await downloadExport();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `polis-export-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      audit.refresh();
      push("Export generated. Treat the file as sensitive health information.", "success");
    } catch (error) {
      push(errorMessage(error), "error");
    } finally {
      setExporting(false);
    }
  };

  const runFederated = async (rounds: number) => {
    setFederatedRunning(true);
    try {
      const response = await apiPost<FederatedResponse>("/privacy/federated-rounds", { rounds });
      setFederatedResult(response);
      await state.refresh();
      audit.refresh();
      push("Federated demonstration completed. No raw records left the process.", "info");
    } catch (error) {
      push(errorMessage(error), "error");
    } finally {
      setFederatedRunning(false);
    }
  };

  const chartRounds = (federatedResult?.rounds ?? state.data.federated_rounds.map((round) => ({
    round: round.round,
    accuracy: round.accuracy,
    loss: round.loss,
    epsilon: round.epsilon,
    participants: round.participants,
    epsilon_spent_cumulative: 0,
    mechanism: "",
  }))).slice(-8);

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Records policy"
        title="Privacy & Data"
        description="Your health record is highly sensitive. This page shows what is stored, what each consent controls, what leaves the system, and how to export or delete it."
        actions={
          <>
            <Button variant="secondary" onClick={handleExport} loading={exporting}>
              <ArrowDownToLine className="h-3.5 w-3.5" /> Export JSON
            </Button>
            <Button variant="danger" onClick={() => setDeleteOpen(true)}>
              <Trash2 className="h-3.5 w-3.5" /> Delete data
            </Button>
          </>
        }
      />

      <div className="mb-5 grid grid-cols-2 gap-px border border-line bg-line sm:grid-cols-4">
        <PrivacyStat label="Raw data egress" value="None" note="Default deployment" tone="mint" />
        <PrivacyStat
          label="Federated consent"
          value={consent.federated_learning ? "On" : "Off"}
          note="Independent opt-in"
          tone={consent.federated_learning ? "signal" : "muted"}
        />
        <PrivacyStat
          label="Research consent"
          value={consent.research_participation ? "On" : "Off"}
          note="Separate from federated"
          tone={consent.research_participation ? "signal" : "muted"}
        />
        <PrivacyStat
          label="Privacy budget"
          value={`${budget.epsilon_spent.toFixed(2)} ε`}
          note={`Limit ${budget.epsilon_limit.toFixed(1)} ε`}
          tone="violet"
          mono
        />
      </div>

      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { value: "consent", label: "Consent and data" },
          { value: "federated", label: "Federated lab" },
          { value: "audit", label: "Audit trail", count: audit.data?.length },
        ]}
        className="mb-4 [&_button]:min-h-11"
      />

      {tab === "consent" && (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
          <div className="space-y-4">
            <Panel>
              <SectionHeader
                title="What you consent to"
                description="Each permission is separately revocable. Turning off AI processing does not delete your records."
              />
              <div className="divide-y divide-line">
                <ConsentRow
                  title="AI processing"
                  detail="Allow POLIS AI to read your recorded context and compose grounded explanations. Default deployment uses a local deterministic engine; no raw records are sent externally."
                  checked={consent.ai_processing}
                  loading={updating === "ai_processing"}
                  onChange={(value) => toggle("ai_processing", value)}
                />
                <ConsentRow
                  title="Research participation"
                  detail="Allow your de-identified data to contribute to approved research analyses. Does not enable federated learning and is not required to use POLIS."
                  checked={consent.research_participation}
                  loading={updating === "research_participation"}
                  onChange={(value) => toggle("research_participation", value)}
                />
                <ConsentRow
                  title="Federated learning"
                  detail="Independent opt-in for simulated federated training participation. No real training infrastructure or raw-record egress is enabled in this MVP."
                  checked={consent.federated_learning}
                  loading={updating === "federated_learning"}
                  onChange={(value) => toggle("federated_learning", value)}
                />
                <ConsentRow
                  title="Product analytics"
                  detail="Optional, minimal usage telemetry. Disabled by default; no health-record content is included in analytics."
                  checked={consent.analytics}
                  loading={updating === "analytics"}
                  onChange={(value) => toggle("analytics", value)}
                />
              </div>
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-line px-5 py-3 text-[12px] text-dim">
                <span>Consent version {consent.consent_version}</span>
                <span aria-hidden="true">·</span>
                <span>Last updated {relativeConsent(consent)}</span>
              </div>
            </Panel>

            <Panel>
              <SectionHeader
                title="What is stored"
                description="Counts are scoped to your account only."
                action={<Database className="h-4 w-4 text-dim" />}
              />
              <div className="grid gap-px bg-line sm:grid-cols-2">
                {state.data.data_inventory.map((item) => (
                  <div key={item.resource} className="flex items-center justify-between gap-4 bg-panel px-5 py-3">
                    <span className="text-[13px] text-muted">{item.resource}</span>
                    <span className="number text-[14px] text-mist">{item.count}</span>
                  </div>
                ))}
              </div>
            </Panel>

            <Panel>
              <SectionHeader title="Your rights" />
              <div className="grid gap-px bg-line sm:grid-cols-2">
                {state.data.rights.map((right) => (
                  <div key={right} className="flex items-start gap-2.5 bg-panel px-5 py-3.5">
                    <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-mint" />
                    <span className="text-[13px] leading-relaxed text-muted">{right}</span>
                  </div>
                ))}
              </div>
              <div className="border-t border-line px-5 py-4">
                <div className="text-[12px] font-medium text-mist">Retention</div>
                <p className="mt-1 text-[13px] leading-relaxed text-muted">{state.data.retention}</p>
              </div>
            </Panel>
          </div>

          <div className="space-y-4">
            <Panel>
              <SectionHeader
                title="Privacy by design"
                action={<ShieldCheck className="h-4 w-4 text-mint" />}
              />
              <div className="space-y-4 p-5">
                <ArchitectureRow icon={LockKeyhole} title="HttpOnly session cookies" detail="Tokens are never exposed to JavaScript." />
                <ArchitectureRow icon={Fingerprint} title="Scrypt password hashing" detail="Memory-hard hashing with per-user salts." />
                <ArchitectureRow icon={Database} title="Tenant isolation" detail="Every health query is scoped to the authenticated account." />
                <ArchitectureRow icon={ScrollText} title="Access audit" detail="Actions are logged without free-text health content." />
                <ArchitectureRow icon={Network} title="No third-party analytics by default" detail="No wearable or model connector is live in this MVP." />
              </div>
            </Panel>

            <Callout tone="warning" title="No compliance badge">
              POLIS is an experimental research platform, not a certified medical device or covered entity. Encryption,
              consent and deletion features reduce risk but do not by themselves establish GDPR, HIPAA or MDR compliance.
              A production deployment requires legal, security and regulatory assessment.
            </Callout>

            <Panel>
              <SectionHeader title="Take your data with you" />
              <div className="p-5">
                <p className="text-[13px] leading-relaxed text-muted">
                  The JSON export includes your profile, laboratory results, genetics, medications, wearable samples,
                  simulations, consents and audit log. It is a machine-readable copy, not an official medical record.
                </p>
                <Button className="mt-4 w-full" variant="secondary" onClick={handleExport} loading={exporting}>
                  <ArrowDownToLine className="h-3.5 w-3.5" /> Download export
                </Button>
              </div>
            </Panel>

            <Panel>
              <SectionHeader
                title="Erase health data or account"
                action={<Trash2 className="h-4 w-4 text-danger" />}
              />
              <div className="space-y-3 p-5">
                <p className="text-[13px] leading-relaxed text-muted">
                  You can delete all health records while keeping the account, or delete the entire account. Deletion is
                  immediate and irreversible.
                </p>
                {user?.is_demo && <Badge tone="amber">The shared demo account is protected from deletion</Badge>}
                <Button variant="danger" className="w-full" onClick={() => setDeleteOpen(true)}>
                  Open deletion flow
                </Button>
              </div>
            </Panel>
          </div>
        </div>
      )}

      {tab === "federated" && (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
          <Panel emphasis>
            <SectionHeader
              title="Train without centralizing raw records"
              description="An in-process demonstration of local training, update clipping, additive pairwise masking, Gaussian noise and FedAvg over synthetic clients."
              action={<Badge tone="violet" dot>Simulation</Badge>}
            />
            <div className="p-5">
              <div className="grid grid-cols-2 gap-px border border-line bg-line sm:grid-cols-4">
                {[
                  ["Clients", "8 synthetic"],
                  ["Rounds", String(state.data.federated_rounds.length)],
                  ["Aggregation", "FedAvg"],
                  ["Raw egress", "None"],
                ].map(([label, value]) => (
                  <div key={label} className="bg-ink px-4 py-3">
                    <div className="text-[12px] text-muted">{label}</div>
                    <div className="mt-1 text-[13px] text-mist">{value}</div>
                  </div>
                ))}
              </div>

              <div className="mt-4 border border-line bg-ink p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-[12px] font-medium text-mist">Training outcome</span>
                  <span className="font-mono text-[11px] text-dim">Synthetic holdout, {chartRounds.length} rounds</span>
                </div>
                {chartRounds.length ? (
                  <div className="mt-3 h-[220px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={chartRounds} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
                        <CartesianGrid stroke="#20261f" vertical={false} />
                        <XAxis
                          dataKey="round"
                          tick={{ fill: "#8d968a", fontSize: 11, fontFamily: "IBM Plex Mono, monospace" }}
                          tickLine={false}
                          axisLine={{ stroke: "#2a312b" }}
                        />
                        <YAxis
                          domain={[0, 1]}
                          tick={{ fill: "#8d968a", fontSize: 11, fontFamily: "IBM Plex Mono, monospace" }}
                          tickLine={false}
                          axisLine={false}
                          width={32}
                        />
                        <Tooltip
                          cursor={{ stroke: "#3b453c" }}
                          content={({ active, payload, label }) => active && payload?.length ? (
                            <div className="border border-[#3b453c] bg-panel px-3 py-2">
                              <div className="font-mono text-[11px] text-dim">Round {label}</div>
                              {payload.map((item) => (
                                <div key={String(item.name)} className="mt-1 font-mono text-[11px] text-mist">
                                  {item.name}: {Number(item.value).toFixed(3)}
                                </div>
                              ))}
                            </div>
                          ) : null}
                        />
                        <Line type="monotone" dataKey="accuracy" name="Accuracy" stroke="#9adbae" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                        <Line type="monotone" dataKey="loss" name="Loss" stroke="#e8b979" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="py-14 text-center text-[13px] text-dim">No federated rounds have been run in this account.</div>
                )}
              </div>

              <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Users className="h-3.5 w-3.5 text-violet" />
                  <span className="text-[13px] text-muted">
                    Federated consent: {consent.federated_learning ? "enabled" : "not enabled"}
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={!consent.federated_learning || federatedRunning}
                    onClick={() => runFederated(1)}
                    loading={federatedRunning}
                  >
                    Run 1 round
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    disabled={!consent.federated_learning || federatedRunning}
                    onClick={() => runFederated(3)}
                  >
                    Run 3 rounds
                  </Button>
                </div>
              </div>
              {!consent.federated_learning && (
                <Callout tone="warning" title="Independent opt-in required" className="mt-4">
                  <button
                    type="button"
                    onClick={() => toggle("federated_learning", true)}
                    className="min-h-11 text-[13px] font-medium text-amber underline underline-offset-4"
                  >
                    Enable federated consent
                  </button>{" "}
                  to run the local demonstration. This does not imply that production federated learning exists.
                </Callout>
              )}
              {federatedResult && (
                <div role="status" className="mt-4 border border-mint/25 bg-mint/[0.03] px-4 py-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <Badge tone={federatedResult.status === "privacy_budget_exhausted" ? "amber" : "mint"}>
                      {sentenceCase(federatedResult.status)}
                    </Badge>
                    <span className="number text-[12px] text-violet">ε {federatedResult.epsilon_spent_total.toFixed(2)}</span>
                  </div>
                  <p className="mt-2 text-[12.5px] leading-relaxed text-muted">{federatedResult.simulation_notice}</p>
                  <ul className="mt-2 space-y-1 border-t border-line pt-2">
                    {federatedResult.privacy_notes.slice(0, 3).map((note) => (
                      <li key={note} className="flex gap-2 text-[12px] leading-relaxed text-dim">
                        <span aria-hidden="true">·</span>
                        <span>{note}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </Panel>

          <div className="space-y-4">
            <Panel>
              <SectionHeader title="Budget accounting" />
              <div className="space-y-4 p-5">
                <Meter value={budget.epsilon_spent} max={budget.epsilon_limit} label="Differential privacy budget" />
                <p className="text-[12.5px] leading-relaxed text-dim">{budget.label}</p>
                <Callout tone="warning" title="Federated learning is not anonymity">
                  Model updates can leak information. This demo uses clipping, noise and simulated masking, but no formal
                  end-to-end differential privacy proof or production secure-aggregation protocol.
                </Callout>
              </div>
            </Panel>

            <Panel>
              <SectionHeader title="What is still uncertain" />
              <ul className="space-y-2.5 p-5">
                {[
                  "Repeated model updates can leak information even without raw data.",
                  "Metadata such as participation timing can be sensitive.",
                  "Secure aggregation protects updates in transit, not against a malicious server forever.",
                  "Differential privacy reduces but does not eliminate all inference risk.",
                  "This demonstration has no independent security audit.",
                ].map((text) => (
                  <li key={text} className="flex gap-2 text-[13px] leading-relaxed text-dim">
                    <span aria-hidden="true">·</span>
                    <span>{text}</span>
                  </li>
                ))}
              </ul>
            </Panel>

            <Panel>
              <SectionHeader title="Recent demonstration rounds" />
              <div className="divide-y divide-line">
                {(federatedResult?.rounds ?? state.data.federated_rounds).slice(-5).reverse().map((round) => (
                  <div key={`${round.round}-${round.participants}`} className="flex items-center justify-between gap-3 px-5 py-3">
                    <div>
                      <div className="font-mono text-[12px] text-muted">Round {round.round}</div>
                      <div className="mt-0.5 font-mono text-[11px] text-dim">
                        {round.participants} clients · ε {round.epsilon}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="number text-[13px] text-mint">{(round.accuracy * 100).toFixed(1)}%</div>
                      <div className="mt-0.5 font-mono text-[11px] text-dim">loss {round.loss.toFixed(3)}</div>
                    </div>
                  </div>
                ))}
                {(!federatedResult?.rounds.length && !state.data.federated_rounds.length) && (
                  <div className="px-5 py-8 text-center text-[13px] text-dim">No rounds yet.</div>
                )}
              </div>
            </Panel>
          </div>
        </div>
      )}

      {tab === "audit" && (
        <Panel>
          <SectionHeader
            title="Account and data actions"
            description="Free-text health content and request bodies are not recorded."
            action={<Badge tone="muted">{audit.data?.length ?? 0} entries</Badge>}
          />
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px]">
              <thead>
                <tr className="border-b border-line text-left">
                  {["Action", "Resource", "Detail", "Time"].map((heading) => (
                    <th key={heading} scope="col" className="px-5 py-3 text-[12px] font-medium text-muted">{heading}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(audit.data ?? []).map((entry) => (
                  <tr key={entry.id} className="border-b border-line last:border-0">
                    <td className="px-5 py-3 font-mono text-[12px] text-signal">{entry.action}</td>
                    <td className="px-5 py-3 text-[13px] text-muted">{entry.resource_type}</td>
                    <td className="max-w-[420px] px-5 py-3">
                      <div className="truncate font-mono text-[12px] text-dim">
                        {Object.entries(entry.detail).map(([key, value]) => `${key}=${typeof value === "object" ? "…" : String(value)}`).join(" · ") || "No detail recorded"}
                      </div>
                    </td>
                    <td className="px-5 py-3 font-mono text-[12px] text-dim">{formatDateTime(entry.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!audit.data?.length && <div className="px-5 py-12 text-center text-[13px] text-dim">No audit entries.</div>}
          </div>
        </Panel>
      )}

      <DeleteSheet
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        isDemo={Boolean(user?.is_demo)}
        onDeleted={(scope) => {
          setDeleteOpen(false);
          if (scope === "account") {
            router.replace("/login");
          } else {
            state.refresh();
            audit.refresh();
            push("Health records deleted. Account retained.", "success");
          }
        }}
      />
    </div>
  );
}

function SectionHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
      <div className="min-w-0">
        <h2 className="font-display text-[19px] leading-snug text-mist">{title}</h2>
        {description && <p className="mt-1 max-w-2xl text-[13px] leading-relaxed text-muted">{description}</p>}
      </div>
      {action && <div className="shrink-0 pt-0.5">{action}</div>}
    </div>
  );
}

function ConsentRow({
  title,
  detail,
  checked,
  loading,
  onChange,
}: {
  title: string;
  detail: string;
  checked: boolean;
  loading: boolean;
  onChange: (value: boolean) => void;
}) {
  const detailId = `${title.toLowerCase().replaceAll(" ", "-")}-detail`;
  return (
    <div className="flex items-start justify-between gap-4 px-5 py-4">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[14px] text-mist">{title}</span>
          <Badge tone={checked ? "signal" : "muted"}>{checked ? "Enabled" : "Disabled"}</Badge>
        </div>
        <p id={detailId} className="mt-1.5 max-w-xl text-[13px] leading-relaxed text-muted">{detail}</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={`${title} consent`}
        aria-describedby={detailId}
        aria-busy={loading || undefined}
        disabled={loading}
        onClick={() => onChange(!checked)}
        className="-mr-2 flex h-11 w-11 shrink-0 items-center justify-center disabled:opacity-50"
      >
        <span
          className={cn(
            "relative h-5 w-9 rounded-[2px] border transition-colors",
            checked ? "border-signal/50 bg-signal/20" : "border-[#3b453c] bg-raised",
          )}
        >
          <span
            className={cn(
              "absolute top-1/2 h-3 w-3 -translate-y-1/2 rounded-[1px] transition-[left,background-color] duration-150",
              checked ? "left-[18px] bg-signal" : "left-[3px] bg-dim",
            )}
          />
        </span>
      </button>
    </div>
  );
}

function ArchitectureRow({ icon: Icon, title, detail }: { icon: typeof LockKeyhole; title: string; detail: string }) {
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center border border-line bg-ink">
        <Icon className="h-3.5 w-3.5 text-mint" />
      </span>
      <div>
        <div className="text-[13.5px] text-mist">{title}</div>
        <div className="mt-0.5 text-[12.5px] leading-relaxed text-dim">{detail}</div>
      </div>
    </div>
  );
}

function PrivacyStat({
  label,
  value,
  note,
  tone,
  mono = false,
}: {
  label: string;
  value: string;
  note: string;
  tone?: "mint" | "signal" | "muted" | "violet";
  mono?: boolean;
}) {
  return (
    <div className="bg-panel px-4 py-3.5">
      <div className="text-[12px] text-dim">{label}</div>
      <div
        className={cn(
          "mt-1.5 text-[19px] leading-none",
          mono ? "number" : "font-display",
          tone === "mint" ? "text-mint" : tone === "signal" ? "text-signal" : tone === "violet" ? "text-violet" : tone === "muted" ? "text-muted" : "text-mist",
        )}
      >
        {value}
      </div>
      <div className="mt-2 text-[11.5px] text-dim">{note}</div>
    </div>
  );
}

function DeleteSheet({ open, onClose, isDemo, onDeleted }: { open: boolean; onClose: () => void; isDemo: boolean; onDeleted: (scope: "health_data" | "account") => void }) {
  const { push } = useToast();
  const [scope, setScope] = useState<"health_data" | "account">("health_data");
  const [confirmation, setConfirmation] = useState("");
  const [password, setPassword] = useState("");
  const [deleting, setDeleting] = useState(false);

  const submit = async () => {
    if (confirmation !== "DELETE MY DATA") {
      push('Type exactly "DELETE MY DATA".', "error");
      return;
    }
    if (!password) {
      push("Password is required.", "error");
      return;
    }
    setDeleting(true);
    try {
      await apiPost("/privacy/data", { confirmation, password, scope });
      setConfirmation("");
      setPassword("");
      onDeleted(scope);
    } catch (error) {
      push(errorMessage(error), "error");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Sheet open={open} onClose={onClose} title="Delete data" eyebrow="Irreversible action" width="max-w-lg">
      <div className="space-y-5">
        <Callout tone="danger" title="There is no undo">
          Deletion is immediate. Export your data first if you may need a copy. A production deployment may need to
          reconcile backups within its documented retention schedule.
        </Callout>

        <div className="space-y-2">
          <button
            type="button"
            onClick={() => setScope("health_data")}
            className={cn(
              "min-h-11 w-full border px-4 py-3 text-left",
              scope === "health_data" ? "border-amber/40 bg-amber/[0.03]" : "border-line hover:border-[#3b453c]",
            )}
          >
            <div className="text-[13.5px] text-mist">Delete health records, keep account</div>
            <div className="mt-1 text-[12.5px] leading-relaxed text-dim">
              Labs, genetics, medications, wearables, simulations, federated rounds and profile. Consents remain.
            </div>
          </button>
          <button
            type="button"
            onClick={() => setScope("account")}
            disabled={isDemo}
            className={cn(
              "min-h-11 w-full border px-4 py-3 text-left disabled:cursor-not-allowed disabled:opacity-50",
              scope === "account" ? "border-danger/40 bg-danger/[0.03]" : "border-line hover:border-[#3b453c]",
            )}
          >
            <div className="text-[13.5px] text-mist">Delete entire account</div>
            <div className="mt-1 text-[12.5px] leading-relaxed text-dim">
              {isDemo ? "Protected on the shared demonstration account." : "Removes the account, consents, audit entries and all associated records."}
            </div>
          </button>
        </div>

        <label className="block">
          <span className="mb-2 block text-[12px] font-medium text-muted">Type DELETE MY DATA to confirm</span>
          <input
            className="input font-mono"
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
            placeholder="DELETE MY DATA"
            autoComplete="off"
          />
        </label>
        <label className="block">
          <span className="mb-2 block text-[12px] font-medium text-muted">Confirm password</span>
          <input
            type="password"
            className="input"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
          />
        </label>

        <div className="flex justify-end gap-2 border-t border-line pt-4">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="danger" loading={deleting} onClick={submit} disabled={isDemo && scope === "account"}>
            <Trash2 className="h-3.5 w-3.5" /> Delete
          </Button>
        </div>
      </div>
    </Sheet>
  );
}

function relativeConsent(consent: Consent) {
  return consent.updated_at ? formatDate(consent.updated_at) : "not recorded";
}

function sentenceCase(value: string) {
  const text = value.replaceAll("_", " ").replaceAll("-", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function PrivacyLoading() {
  return (
    <div className="flex min-h-[320px] items-center justify-center gap-3" role="status">
      <LoaderCircle className="h-5 w-5 animate-spin text-signal" aria-hidden="true" />
      <span className="text-[13px] text-muted">Loading privacy and data</span>
    </div>
  );
}
