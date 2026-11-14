"use client";

import Link from "next/link";
import {
  Activity,
  Dna,
  FlaskConical,
  HeartPulse,
  Moon,
  Pill,
} from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Panel, PanelHeader, LoadError, Skeleton } from "@/components/ui/panel";
import { Badge } from "@/components/ui/badge";
import { Callout } from "@/components/ui/callout";
import { ProgressBar } from "@/components/ui/misc";
import { useQuery } from "@/lib/use-query";
import type { Exposure, GeneticsOverview, LabResult, Profile, TwinOverview, WearableOverview } from "@/lib/types";
import { categoryLabel, cn, formatDate, relativeTime, titleCase } from "@/lib/format";

const labCategories = ["liver", "kidney", "metabolic", "inflammatory", "hematology", "hormonal", "nutritional", "electrolytes"];

function ageFrom(date: string | null) {
  if (!date) return null;
  const dob = new Date(date);
  if (Number.isNaN(dob.getTime())) return null;
  return Math.floor((Date.now() - dob.getTime()) / (365.25 * 24 * 60 * 60 * 1000));
}

export default function BiologyPage() {
  const profile = useQuery<Profile>("/profile");
  const twin = useQuery<TwinOverview>("/twin");
  const labs = useQuery<LabResult[]>("/labs?latest_only=true");
  const genetics = useQuery<GeneticsOverview>("/genetics");
  const meds = useQuery<Exposure[]>("/medications?active_only=true");
  const wearables = useQuery<WearableOverview>("/wearables");

  if (profile.loading && !profile.data) return <BiologySkeleton />;
  if (profile.error && !profile.data) return <LoadError message={profile.error} onRetry={profile.refresh} />;
  if (!profile.data) return null;

  const data = profile.data;
  const age = ageFrom(data.date_of_birth);
  const labCounts = new Map<string, number>();
  for (const lab of labs.data ?? []) labCounts.set(lab.category, (labCounts.get(lab.category) ?? 0) + 1);
  const activeMeds = meds.data?.length ?? 0;
  const phenotypeCount = genetics.data?.phenotypes.length ?? 0;
  const variantCount = genetics.data?.variants.length ?? 0;
  const wearableMetrics = wearables.data?.metrics ?? [];
  const sleepMetrics = wearableMetrics.filter((metric) => ["sleep_duration", "deep_sleep", "rem_sleep"].includes(metric.metric));
  const activityMetrics = wearableMetrics.filter((metric) => ["steps", "active_minutes"].includes(metric.metric));
  const hasWearables = wearableMetrics.length > 0;

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Personal biological profile"
        title="My biology"
        description="The structured context behind every interpretation: demographics, conditions, genetics, laboratory panels and the provenance attached to each record."
        actions={
          <>
            <Link href="/privacy" className="btn btn-secondary">
              Data controls
            </Link>
            <Link href="/settings" className="btn btn-primary">
              Edit profile
            </Link>
          </>
        }
      />

      {data.is_synthetic && (
        <Callout tone="warning" title="Synthetic demonstration profile" className="mb-4">
          Every health value in this account is synthetic. The profile exercises normal, out-of-range and missing-data
          states and must not be read as information about a real person.
        </Callout>
      )}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,0.72fr)_minmax(0,1.28fr)]">
        <div className="space-y-4">
          <Panel>
            <div className="border-b border-line p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span className="font-mono text-[12px] text-dim">Profile record</span>
                <Badge tone={data.is_synthetic ? "amber" : "neutral"}>
                  {data.is_synthetic ? "Synthetic" : "Personal record"}
                </Badge>
              </div>
              <h2 className="mt-3 font-display text-[26px] leading-tight text-mist">
                {age !== null ? `${age} years old` : "Age not recorded"}
              </h2>
              <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-[13px] text-muted">
                <span>{data.gender_identity ?? "Gender not recorded"}</span>
                <span>{data.blood_type ?? "Blood type not recorded"}</span>
              </div>
              <div className="mt-4 grid grid-cols-3 gap-px border border-line bg-line">
                {[
                  ["Height", data.height_cm ? `${data.height_cm} cm` : "No data"],
                  ["Weight", data.weight_kg ? `${data.weight_kg} kg` : "No data"],
                  ["BMI", data.height_cm && data.weight_kg ? (data.weight_kg / ((data.height_cm / 100) ** 2)).toFixed(1) : "No data"],
                ].map(([label, value]) => (
                  <div key={label} className="bg-panel px-3 py-2.5">
                    <div className="font-mono text-[12px] text-dim">{label}</div>
                    <div className="mt-1 font-mono text-[13px] text-mist">{value}</div>
                  </div>
                ))}
              </div>
            </div>
            <div className="space-y-2.5 p-5">
              <Row label="Date of birth" value={data.date_of_birth ? formatDate(data.date_of_birth) : "Not recorded"} />
              <Row label="Sex at birth" value={data.sex_at_birth ?? "Not recorded"} />
              <Row label="Smoking" value={data.smoking_status ?? "Not recorded"} />
              <Row label="Alcohol" value={data.alcohol_units_per_week !== null ? `${data.alcohol_units_per_week} units/week` : "Not recorded"} />
              <Row label="Activity" value={data.activity_level?.replaceAll("_", " ") ?? "Not recorded"} />
              <Row label="Pregnancy" value={data.pregnancy_status?.replaceAll("_", " ") ?? "Not recorded"} />
              <Row label="Ancestry context" value={data.ancestry_context ?? "Not recorded"} />
            </div>
            <div className="border-t border-line px-5 py-3 font-mono text-[11px] text-dim">
              Last updated {relativeTime(data.updated_at)}
            </div>
          </Panel>

          <Panel>
            <PanelHeader eyebrow="Clinical context" title="Conditions and allergies" />
            <div className="p-4">
              <div className="mb-2 font-mono text-[12px] text-dim">Reported conditions</div>
              <div className="space-y-1.5">
                {data.conditions.map((condition) => (
                  <div key={condition.name} className="flex items-start justify-between gap-3 border border-line bg-ink px-3 py-2.5">
                    <div className="min-w-0">
                      <div className="text-[13px] text-mist">{condition.name}</div>
                      <div className="mt-0.5 text-[11px] text-dim">
                        {condition.diagnosed_year ? `Since ${condition.diagnosed_year}` : "Onset unknown"}
                        {condition.status ? `, ${condition.status}` : ""}
                      </div>
                    </div>
                    <Badge tone="muted">Self-reported</Badge>
                  </div>
                ))}
                {!data.conditions.length && <p className="text-[12px] text-dim">None recorded.</p>}
              </div>

              <div className="mb-2 mt-5 font-mono text-[12px] text-dim">Allergies</div>
              <div className="space-y-1.5">
                {data.allergies.map((allergy) => (
                  <div key={allergy.substance} className="border border-amber/25 bg-amber/[0.03] px-3 py-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[13px] text-mist">{allergy.substance}</span>
                      <Badge tone="amber">{titleCase(allergy.severity ?? "unknown")}</Badge>
                    </div>
                    <div className="mt-0.5 text-[12px] text-muted">{allergy.reaction ?? "Reaction not recorded"}</div>
                    <div className="mt-1 font-mono text-[11px] text-dim">
                      {allergy.source?.replaceAll("_", " ") ?? "Patient-reported"}
                    </div>
                  </div>
                ))}
                {!data.allergies.length && <p className="text-[12px] text-dim">None recorded.</p>}
              </div>

              <div className="mb-2 mt-5 font-mono text-[12px] text-dim">Family history</div>
              <div className="divide-y divide-line">
                {data.family_history.map((item) => (
                  <div key={`${item.relation}-${item.condition}`} className="flex items-baseline justify-between gap-3 py-2">
                    <span className="text-[12px] text-muted">{item.relation}</span>
                    <span className="text-right text-[12px] text-dim">
                      {item.condition}
                      {item.age_at_onset ? `, onset age ${item.age_at_onset}` : ""}
                    </span>
                  </div>
                ))}
                {!data.family_history.length && <p className="py-2 text-[12px] text-dim">None recorded.</p>}
              </div>
            </div>
          </Panel>
        </div>

        <div className="space-y-4">
          <Panel>
            <PanelHeader
              eyebrow="Data domains"
              title="What the profile contains"
              description="Coverage, provenance and quality. Missing domains are shown, not hidden."
              action={<Badge tone="neutral">{twin.data?.overall_completeness ?? 0}% complete</Badge>}
            />
            <div className="grid gap-px bg-line sm:grid-cols-2">
              <DomainCard icon={FlaskConical} title="Laboratory panels" count={labs.data?.length ?? 0} status="available" detail={`${labCounts.size} categories represented`} />
              <DomainCard icon={Dna} title="Pharmacogenomics" count={phenotypeCount} status={phenotypeCount ? "available" : "missing"} detail={`${variantCount} annotated variants`} />
              <DomainCard icon={Pill} title="Medication exposures" count={activeMeds} status={activeMeds ? "available" : "missing"} detail="User-reported, synthetic" />
              <DomainCard icon={HeartPulse} title="Wearable time series" count={wearableMetrics.length} status={hasWearables ? "partial" : "missing"} detail="Distinct device metric series" />
              <DomainCard icon={Moon} title="Sleep and recovery" count={sleepMetrics.length} status={hasWearables ? "partial" : "missing"} detail="No polysomnography" />
              <DomainCard icon={Activity} title="Physical activity" count={activityMetrics.length} status={hasWearables ? "partial" : "missing"} detail="Step and active-minute estimates" />
            </div>
          </Panel>

          <Panel>
            <PanelHeader eyebrow="Laboratory coverage" title="Panel completeness" description="Latest available markers by category." />
            <div className="grid gap-x-6 gap-y-3 p-5 sm:grid-cols-2">
              {labCategories.map((category) => {
                const count = labCounts.get(category) ?? 0;
                const percent = Math.min(100, count * 12);
                return (
                  <div key={category}>
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="text-[13px] text-muted">{categoryLabel(category)}</span>
                      <span className="font-mono text-[11px] text-dim">
                        {count} {count === 1 ? "marker" : "markers"}
                      </span>
                    </div>
                    <ProgressBar value={percent} tone={count ? "signal" : "muted"} className="mt-1.5" />
                  </div>
                );
              })}
            </div>
          </Panel>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Panel>
              <PanelHeader eyebrow="Environmental and lifestyle" title="Exposure context" />
              <div className="space-y-2.5 p-4">
                <Row label="Seasonal context" value="Not recorded" muted />
                <Row label="Occupational exposure" value="Not recorded" muted />
                <Row label="Air quality / location" value="Not connected" muted />
                <Row label="Diet pattern" value="Not recorded" muted />
                <div className="border-t border-line pt-2.5">
                  <p className="text-[11px] leading-relaxed text-dim">
                    POLIS does not infer environmental exposures from location telemetry. These data require an explicit,
                    consented source.
                  </p>
                </div>
              </div>
            </Panel>

            <Panel>
              <PanelHeader eyebrow="Missing information" title="What would improve this profile" />
              <div className="p-4">
                <ul className="list-disc space-y-2 pl-4 marker:text-amber/60">
                  {[
                    !data.pregnancy_status && "Pregnancy status is not recorded.",
                    !data.alcohol_units_per_week && "Alcohol exposure is not quantified.",
                    "No home blood-pressure series is connected.",
                    "No spirometry or pulmonary function data are available.",
                    "No continuous glucose monitoring is available.",
                    "The medication list has not been confirmed by a pharmacy.",
                    "No environmental or occupational exposure data are recorded.",
                  ].filter(Boolean).slice(0, 6).map((item) => (
                    <li key={String(item)} className="text-[12px] leading-relaxed text-muted">
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </Panel>
          </div>

          <Panel>
            <PanelHeader eyebrow="Provenance" title="How records enter POLIS" />
            <div className="grid gap-px bg-line sm:grid-cols-3">
              {[
                { label: "Laboratory", text: "Manual, CSV, FHIR or text-PDF import. Unit conversions are explicit; PDFs are marked needs review." },
                { label: "Genetics", text: "Curated demonstration diplotypes or conservative VCF annotation. No clinical phenotype from raw VCF." },
                { label: "Wearables", text: "Synthetic sample in the unified time-series model. No live consumer OAuth ingestion is enabled." },
              ].map((item) => (
                <div key={item.label} className="bg-panel p-4">
                  <div className="text-[13px] text-mist">{item.label}</div>
                  <p className="mt-2 text-[12px] leading-relaxed text-dim">{item.text}</p>
                </div>
              ))}
            </div>
          </Panel>

          <div className="flex flex-wrap items-center justify-between gap-3 border border-line px-4 py-3">
            <span className="text-[12px] text-muted">Laboratory values are not merged across incompatible units or intervals.</span>
            <Link href="/biomarkers" className="link-underline inline-flex min-h-11 items-center text-[12px] text-muted hover:text-mist sm:min-h-0">
              Inspect results
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value, muted }: { label: string; value: string; muted?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <span className="font-mono text-[12px] text-dim">{label}</span>
      <span className={cn("max-w-[220px] text-right text-[13px]", muted ? "text-dim" : "text-muted")}>{value}</span>
    </div>
  );
}

function DomainCard({
  icon: Icon,
  title,
  count,
  status,
  detail,
}: {
  icon: typeof FlaskConical;
  title: string;
  count: number;
  status: string;
  detail: string;
}) {
  const statusLabel = status === "available" ? "Available" : status === "partial" ? "Partial" : "Missing";
  return (
    <div className="bg-panel p-4">
      <div className="flex items-start justify-between gap-2">
        <Icon className="h-4 w-4 text-dim" aria-hidden="true" />
        <Badge tone={status === "available" ? "mint" : status === "partial" ? "amber" : "muted"}>{statusLabel}</Badge>
      </div>
      <div className="mt-3 text-[13px] text-mist">{title}</div>
      <div className="mt-1 flex items-baseline gap-1.5">
        <span className="number text-[20px] text-mist">{count}</span>
        <span className="text-[11px] text-dim">{count === 1 ? "entry" : "entries"}</span>
      </div>
      <div className="mt-1 text-[11px] text-dim">{detail}</div>
    </div>
  );
}

function BiologySkeleton() {
  return (
    <div>
      <Skeleton className="mb-3 h-3 w-52" />
      <Skeleton className="mb-8 h-10 w-[280px]" />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[0.72fr_1.28fr]">
        <Skeleton className="h-[560px]" />
        <Skeleton className="h-[440px]" />
      </div>
    </div>
  );
}
