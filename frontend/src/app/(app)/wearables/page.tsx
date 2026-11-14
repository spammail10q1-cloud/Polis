"use client";

import { useState } from "react";
import Link from "next/link";
import {
  PlugZap,
  Upload,
  Watch,
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
import { Panel, PanelHeader, PanelBody, LoadError, Skeleton } from "@/components/ui/panel";
import { Badge } from "@/components/ui/badge";
import { Callout } from "@/components/ui/callout";
import { Button } from "@/components/ui/button";
import { Tabs } from "@/components/ui/misc";
import { Sheet } from "@/components/ui/sheet";
import { useQuery } from "@/lib/use-query";
import { uploadFile, errorMessage } from "@/lib/api";
import { useToast } from "@/components/toast";
import type { WearableImportResult, WearableOverview, WearableSeries } from "@/lib/types";
import { cn, formatDate, formatNumber, relativeTime } from "@/lib/format";

const metricTabs = [
  { value: "sleep_duration", label: "Sleep" },
  { value: "hrv", label: "HRV" },
  { value: "resting_hr", label: "Resting HR" },
  { value: "steps", label: "Steps" },
] as const;

const integrationStatus: Record<string, { label: string; tone: "amber" | "signal" | "muted" }> = {
  sample_data_only: { label: "Sample data only", tone: "amber" },
  integration_interface_ready: { label: "Interface ready", tone: "signal" },
  not_configured: { label: "Not configured", tone: "muted" },
};

function deviceText(value: string): string {
  const text = value.replace(/\s*[\u2014\u2013]\s*/g, ", ").replaceAll("_", " ").trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export default function WearablesPage() {
  const overview = useQuery<WearableOverview>("/wearables");
  const [metric, setMetric] = useState<(typeof metricTabs)[number]["value"]>("sleep_duration");
  const [importOpen, setImportOpen] = useState(false);
  const series = useQuery<WearableSeries>(`/wearables/series?metric=${metric}&days=30`);

  if (overview.loading && !overview.data) return <WearableSkeleton />;
  if (overview.error && !overview.data) return <LoadError message={overview.error} onRetry={overview.refresh} />;
  if (!overview.data) return null;

  const device = [...overview.data.devices].sort((a, b) => new Date(b.last_synced_at ?? 0).getTime() - new Date(a.last_synced_at ?? 0).getTime())[0];
  const latest = (metricKey: string) => overview.data?.metrics.find((item) => item.metric === metricKey);
  const allSynthetic = overview.data.devices.length > 0 && overview.data.devices.every((item) => item.is_synthetic);
  const hasImported = overview.data.devices.some((item) => !item.is_synthetic);
  const sourceLabel = overview.data.devices.length === 0
    ? "No source"
    : allSynthetic
      ? "Sample data"
      : hasImported && overview.data.devices.some((item) => item.is_synthetic)
        ? "Mixed sources"
        : "User import";
  const sourceTone = overview.data.devices.length === 0 ? "muted" : allSynthetic || sourceLabel === "Mixed sources" ? "amber" : "neutral";

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Device estimates and 30-day series"
        title="Wearables"
        description="Consumer devices add continuous context, but they are not laboratory measurements. POLIS labels every device estimate and never presents an integration as live until OAuth and real ingestion are implemented."
        actions={
          <>
            <Badge tone={sourceTone}>{sourceLabel}</Badge>
            <Button variant="primary" onClick={() => setImportOpen(true)}>
              <Upload className="h-4 w-4" aria-hidden="true" /> Import data
            </Button>
          </>
        }
      />

      <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <Panel emphasis>
          <div className="flex flex-wrap items-start justify-between gap-4 p-5">
            <div className="flex items-start gap-3.5">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center border border-line">
                <Watch className="h-5 w-5 text-muted" aria-hidden="true" />
              </span>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-[18px] text-mist">{device ? deviceText(device.name) : "No device"}</h2>
                  {device && (
                    <Badge tone={device.is_synthetic ? "amber" : "signal"}>
                      {device.is_synthetic ? "Synthetic sample" : "User import"}
                    </Badge>
                  )}
                </div>
                <p className="mt-1 text-[13px] text-muted">
                  {device ? `${deviceText(device.provider)}, last sample ${relativeTime(device.last_synced_at)}` : "No device data recorded."}
                </p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {["Sleep staging", "HRV", "Respiratory rate", "Activity"].map((item) => (
                    <span key={item} className="border border-line px-2 py-0.5 text-[12px] text-muted">{item}</span>
                  ))}
                </div>
              </div>
            </div>
            <div className="text-left sm:text-right">
              <div className="text-[12px] text-dim">Ingestion</div>
              <div className={cn("mt-1 text-[13px]", device?.connection_status === "manual_import" ? "text-muted" : "text-amber")}>
                {device?.connection_status === "manual_import" ? "Manual CSV import" : device ? "Simulated import" : "Not configured"}
              </div>
              <div className="mt-0.5 text-[12px] text-dim">No live OAuth connection</div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-px border-t border-line bg-line sm:grid-cols-4">
            {[
              { label: "Sleep", value: latest("sleep_duration"), unit: "h", digits: 1 },
              { label: "HRV", value: latest("hrv"), unit: "ms", digits: 1 },
              { label: "Resting HR", value: latest("resting_hr"), unit: "bpm", digits: 0 },
              { label: "Steps", value: latest("steps"), unit: "steps", digits: 0 },
            ].map(({ label, value, unit, digits }) => (
              <div key={label} className="bg-panel px-4 py-3.5">
                <div className="text-[12px] text-dim">{label}</div>
                <div className="mt-1.5 flex items-baseline gap-1.5">
                  {value && value.average !== null ? (
                    <>
                      <span className="number text-[20px] text-mist">{formatNumber(value.average, digits)}</span>
                      <span className="font-mono text-[11px] text-dim">{unit}</span>
                    </>
                  ) : (
                    <span className="text-[14px] text-dim">No data</span>
                  )}
                </div>
                <div className="mt-0.5 text-[12px] text-dim">14-day average</div>
              </div>
            ))}
          </div>

          <div className="border-t border-line px-4 py-2.5">
            <p className="text-[12px] text-dim">All values on this page are device estimates, not laboratory measurements.</p>
          </div>

          {overview.data.devices.length > 1 && (
            <div className="flex flex-wrap items-center gap-2 border-t border-line px-4 py-2.5">
              <span className="text-[12px] text-dim">Sources</span>
              {overview.data.devices.map((item) => (
                <span key={item.id} className="border border-line px-2 py-0.5 text-[12px] text-muted">
                  {deviceText(item.name)}, {item.is_synthetic ? "synthetic" : "imported"}
                </span>
              ))}
            </div>
          )}
        </Panel>

        <Callout tone="warning" title="What is operational in this MVP">
          <p>
            No third-party wearable OAuth flow is enabled. On the demonstration account the dataset is synthetic; you
            can additionally import a CSV export from any device. Imported values are user-supplied device estimates,
            not laboratory measurements, and do not imply a live provider connection.
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <span className="text-[12px] text-amber">Live connections: none</span>
            <Link href="/privacy" className="inline-flex min-h-11 items-center text-[13px] text-muted underline decoration-line underline-offset-4 hover:text-mist">
              Review permissions
            </Link>
          </div>
        </Callout>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,0.75fr)]">
        <Panel>
          <div className="border-b border-line px-4 pt-3.5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="text-[12px] text-dim">30-day trend</div>
                <div className="mt-1 text-[16px] text-mist">Device-estimated signal</div>
              </div>
              <Badge tone="violet">Device estimate</Badge>
            </div>
            <Tabs
              value={metric}
              onChange={setMetric}
              items={metricTabs.map((item) => ({ value: item.value, label: item.label }))}
              className="mt-3 border-b-0"
            />
          </div>
          <div className="px-2 pb-3 pt-4">
            {series.loading && !series.data ? (
              <Skeleton className="h-[300px] w-full" />
            ) : series.error && !series.data ? (
              <LoadError message={series.error} onRetry={series.refresh} />
            ) : series.data && series.data.points.length ? (
              <SeriesChart series={series.data} />
            ) : (
              <div className="py-16 text-center">
                <p className="text-[13px] text-muted">No series available for this metric.</p>
                <p className="mt-1 text-[12px] text-dim">Import a CSV with readings from the last 30 days.</p>
              </div>
            )}
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-4 py-3">
            <span className="text-[12px] text-dim">{series.data?.source ?? "No source recorded"}</span>
            <span className="text-[12px] text-dim">
              {series.data ? `${series.data.points.length} samples, ${series.data.unit}` : "No samples"}
            </span>
          </div>
          {series.data?.data_quality_note && (
            <p className="border-t border-line px-4 py-2.5 text-[12px] leading-relaxed text-dim">
              {series.data.data_quality_note}
            </p>
          )}
        </Panel>

        <div className="space-y-4">
          <Panel>
            <PanelHeader eyebrow="Recovery context" title="The last 14 days" />
            <div className="divide-y divide-line">
              {overview.data.metrics
                .filter((item) => ["sleep_duration", "deep_sleep", "hrv", "respiratory_rate", "skin_temp"].includes(item.metric))
                .map((item) => (
                  <div key={item.metric} className="px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-[13px] text-muted">{item.label}</span>
                      <span className="font-mono text-[13px] text-mist">
                        {item.average === null ? "No data" : `${formatNumber(item.average, 1)} ${item.unit}`}
                      </span>
                    </div>
                    <div className="mt-1 flex flex-wrap items-center justify-between gap-2 text-[12px] text-dim">
                      <span>{item.sample_count} sample{item.sample_count === 1 ? "" : "s"}</span>
                      <span>
                        {item.min_value === null || item.max_value === null
                          ? "No range"
                          : `Range ${formatNumber(item.min_value, 1)} to ${formatNumber(item.max_value, 1)} ${item.unit}`}
                      </span>
                    </div>
                  </div>
                ))}
              {!overview.data.metrics.some((item) => ["sleep_duration", "deep_sleep", "hrv", "respiratory_rate", "skin_temp"].includes(item.metric)) && (
                <div className="px-4 py-8 text-center">
                  <p className="text-[13px] text-dim">No recovery metrics recorded.</p>
                  <p className="mt-1 text-[12px] text-dim">Import a CSV to add device readings.</p>
                </div>
              )}
            </div>
            <div className="border-t border-line px-4 py-3">
              <p className="text-[12px] leading-relaxed text-dim">
                Averages are descriptive. They do not diagnose insomnia, autonomic dysfunction or any other condition.
              </p>
            </div>
          </Panel>

          <Panel>
            <PanelHeader eyebrow="Data quality" title="What device data can support" />
            <PanelBody className="space-y-2">
              {[
                "Patterns and temporal context, not diagnosis.",
                "Comparison with your own baseline, not population thresholds.",
                "A prompt for clinical discussion when symptoms persist.",
              ].map((text) => (
                <p key={text} className="border-l border-line pl-3 text-[13px] leading-relaxed text-muted">{text}</p>
              ))}
            </PanelBody>
          </Panel>
        </div>
      </div>

      <Panel className="mt-4">
        <PanelHeader
          eyebrow="Integration architecture"
          title="Provider readiness"
          description="Status describes implemented engineering, not marketing availability."
          action={<Badge tone="muted">No live credentials</Badge>}
        />
        <div className="grid gap-px bg-line sm:grid-cols-2 xl:grid-cols-3">
          {overview.data.integration_registry.map((integration) => {
            const status = integrationStatus[integration.status] ?? { label: integration.status.replaceAll("_", " "), tone: "muted" as const };
            return (
              <div key={integration.provider} className="bg-panel p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <PlugZap className="h-4 w-4 text-dim" aria-hidden="true" />
                    <span className="text-[14px] text-mist">{integration.name}</span>
                  </div>
                  <Badge tone={status.tone}>{status.label}</Badge>
                </div>
                <p className="mt-2 text-[13px] leading-relaxed text-muted">{integration.detail}</p>
                <div className="mt-3 text-[12px] text-dim">
                  {integration.status === "not_configured" ? "Credentials not configured" : "Live ingestion disabled"}
                </div>
              </div>
            );
          })}
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-4 py-3">
          <span className="text-[12px] text-dim">Unified metric model, provenance and quality flags</span>
          <Link href="/privacy" className="inline-flex min-h-11 items-center text-[13px] text-muted underline decoration-line underline-offset-4 hover:text-mist">
            Consent and permissions
          </Link>
        </div>
      </Panel>

      <ImportWearableSheet
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onImported={() => {
          overview.refresh();
          series.refresh();
        }}
      />

      <Callout tone="info" title="Device data are not laboratory data" className="mt-4">
        Resting heart rate, HRV, sleep duration, respiratory rate and skin temperature are produced by proprietary
        consumer algorithms. They can be affected by movement, fit, temperature and software changes. POLIS never silently
        mixes them with clinical measurements.
      </Callout>
    </div>
  );
}

function ImportWearableSheet({ open, onClose, onImported }: { open: boolean; onClose: () => void; onImported: () => void }) {
  const { push } = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<WearableImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const downloadTemplate = () => {
    const today = new Date().toISOString().slice(0, 10);
    const template = `metric,value,unit,date,source\nsleep_duration,7.4,h,${today},My device export\nhrv,52,ms,${today},My device export\nresting_hr,58,bpm,${today},My device export\nsteps,8400,steps,${today},My device export\n`;
    const url = URL.createObjectURL(new Blob([template], { type: "text/csv" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "polis-wearable-import-template.csv";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) return;
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const response = await uploadFile<WearableImportResult>("/wearables/import", file);
      setResult(response);
      push(`${response.imported} wearable value${response.imported === 1 ? "" : "s"} imported.`, "success");
      onImported();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setUploading(false);
    }
  };

  return (
    <Sheet open={open} onClose={onClose} title="Import wearable data" eyebrow="CSV device export" width="max-w-xl">
      <form onSubmit={submit} className="space-y-4">
        <Callout tone="info" title="No live provider connection is implied">
          This imports a file you already own. Values are marked as user-supplied device estimates, distinct from
          laboratory measurements and synthetic demonstration samples. Real provider OAuth is not enabled.
        </Callout>

        <div className="border border-line p-4">
          <div className="text-[13px] text-mist">Supported columns</div>
          <div className="mt-1 font-mono text-[12px] leading-relaxed text-muted">metric, value, unit, date, source (optional)</div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {["sleep_duration (h)", "deep_sleep (h)", "rem_sleep (h)", "resting_hr (bpm)", "hrv (ms)", "steps (steps)", "respiratory_rate (breaths/min)", "skin_temp (°C)", "spo2 (%)", "active_minutes (min)"].map((item) => (
              <span key={item} className="border border-line px-1.5 py-0.5 font-mono text-[11px] text-dim">{item}</span>
            ))}
          </div>
          <button type="button" onClick={downloadTemplate} className="btn btn-secondary mt-3">
            Download CSV template
          </button>
          <p className="mt-2 text-[12px] leading-relaxed text-dim">
            To enter readings by hand, fill the template with one row per measurement and import the saved file.
          </p>
        </div>

        <div>
          <label htmlFor="wearable-csv-file" className="mb-2 block text-[13px] text-mist">Wearable CSV file</label>
          <input
            id="wearable-csv-file"
            type="file"
            accept=".csv,text/csv"
            aria-describedby="wearable-csv-hint"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            className="block min-h-11 w-full cursor-pointer border border-line bg-ink px-3 py-2 text-[13px] text-muted file:mr-3 file:min-h-9 file:cursor-pointer file:rounded-[2px] file:border file:border-line file:bg-raised file:px-3 file:py-1.5 file:text-[13px] file:text-mist"
          />
          <p id="wearable-csv-hint" className="mt-1.5 text-[12px] text-dim">
            {file ? file.name : "UTF-8 CSV, maximum 5 MB and 5,000 rows."}
          </p>
        </div>

        {error && <Callout tone="danger" title="Import failed">{error}</Callout>}
        {result && (
          <div className="space-y-1.5 border border-mint/25 bg-mint/[0.04] px-3.5 py-3">
            <div className="text-[13px] font-medium text-mint">
              {result.imported} imported, {result.skipped} skipped
            </div>
            <p className="text-[12px] leading-relaxed text-muted">{result.notice}</p>
            {result.warnings.map((warning) => (
              <p key={warning} className="text-[12px] leading-relaxed text-amber">{warning}</p>
            ))}
            {result.errors.slice(0, 5).map((item) => (
              <p key={item} className="text-[12px] leading-relaxed text-dim">{item}</p>
            ))}
          </div>
        )}

        <div className="flex justify-end gap-2 border-t border-line pt-4">
          <Button type="button" variant="ghost" onClick={onClose}>Close</Button>
          <Button type="submit" variant="primary" loading={uploading} disabled={!file}>Import CSV</Button>
        </div>
      </form>
    </Sheet>
  );
}

function SeriesChart({ series }: { series: WearableSeries }) {
  const data = series.points.map((point) => ({
    date: formatDate(point.date, { day: "2-digit", month: "short", year: undefined }),
    value: point.value,
  }));
  const values = data.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const padding = (max - min || 1) * 0.18;
  return (
    <div className="h-[300px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 10, right: 28, left: 0, bottom: 2 }}>
          <CartesianGrid stroke="#2a312b" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: "#8d968a", fontSize: 12, fontFamily: "IBM Plex Mono, monospace" }}
            tickLine={false}
            axisLine={{ stroke: "#2a312b" }}
            minTickGap={30}
          />
          <YAxis
            domain={[min - padding, max + padding]}
            tick={{ fill: "#8d968a", fontSize: 12, fontFamily: "IBM Plex Mono, monospace" }}
            tickLine={false}
            axisLine={false}
            width={48}
            tickFormatter={(value: number) => formatNumber(value, series.unit === "steps" ? 0 : 1)}
          />
          <Tooltip
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null;
              return (
                <div className="border border-line bg-panel px-3 py-2">
                  <div className="text-[12px] text-dim">{label}</div>
                  <div className="mt-1 number text-[14px] text-mist">
                    {formatNumber(payload[0]?.value as number, 1)} <span className="font-mono text-[11px] text-dim">{series.unit}</span>
                  </div>
                </div>
              );
            }}
            cursor={{ stroke: "#3b453c", strokeDasharray: "2 3" }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="#7dded6"
            strokeWidth={1.6}
            dot={false}
            activeDot={{ r: 3, fill: "#eef1ea", stroke: "#7dded6", strokeWidth: 2 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
      <div className="mt-1 flex flex-wrap items-center justify-between gap-1 px-2">
        <span className="text-[12px] text-dim">{series.label}</span>
        <span className="font-mono text-[12px] text-dim">{series.points.length} samples, {series.unit}</span>
      </div>
    </div>
  );
}

function WearableSkeleton() {
  return (
    <div>
      <Skeleton className="mb-3 h-3 w-56" />
      <Skeleton className="mb-8 h-10 w-[300px]" />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <Skeleton className="h-[220px]" />
        <Skeleton className="h-[220px]" />
      </div>
      <Skeleton className="mt-4 h-[420px]" />
    </div>
  );
}
