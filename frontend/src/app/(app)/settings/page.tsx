"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  ChevronDown,
  LoaderCircle,
  LogOut,
  Plus,
  Save,
  Settings2,
  ShieldCheck,
  Trash2,
  UserRound,
} from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Panel, LoadError } from "@/components/ui/panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { useQuery } from "@/lib/use-query";
import { useAuth } from "@/components/auth-provider";
import { useToast } from "@/components/toast";
import { apiPatch, errorMessage } from "@/lib/api";
import type { Allergy, Condition, FamilyHistory, ModelRegistry, Profile } from "@/lib/types";
import { cn, formatDate } from "@/lib/format";

type FormState = {
  date_of_birth: string;
  sex_at_birth: string;
  gender_identity: string;
  height_cm: string;
  weight_kg: string;
  blood_type: string;
  ancestry_context: string;
  smoking_status: string;
  alcohol_units_per_week: string;
  activity_level: string;
  pregnancy_status: string;
  conditions: Condition[];
  allergies: Allergy[];
  family_history: FamilyHistory[];
  notes: string;
};

function toForm(profile: Profile): FormState {
  return {
    date_of_birth: profile.date_of_birth ?? "",
    sex_at_birth: profile.sex_at_birth ?? "",
    gender_identity: profile.gender_identity ?? "",
    height_cm: profile.height_cm?.toString() ?? "",
    weight_kg: profile.weight_kg?.toString() ?? "",
    blood_type: profile.blood_type ?? "",
    ancestry_context: profile.ancestry_context ?? "",
    smoking_status: profile.smoking_status ?? "",
    alcohol_units_per_week: profile.alcohol_units_per_week?.toString() ?? "",
    activity_level: profile.activity_level ?? "",
    pregnancy_status: profile.pregnancy_status ?? "",
    conditions: profile.conditions?.length ? profile.conditions : [],
    allergies: profile.allergies?.length ? profile.allergies : [],
    family_history: profile.family_history?.length ? profile.family_history : [],
    notes: profile.notes ?? "",
  };
}

export default function SettingsPage() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const { push } = useToast();
  const profile = useQuery<Profile>("/profile");
  const models = useQuery<ModelRegistry>("/models");
  const [form, setForm] = useState<FormState | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (profile.data) setForm(toForm(profile.data));
  }, [profile.data]);

  if (profile.loading && !profile.data) return <SettingsLoading />;
  if (profile.error && !profile.data) return <LoadError message={profile.error} onRetry={profile.refresh} />;
  if (!form) return null;

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => setForm((current) => (current ? { ...current, [key]: value } : current));

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      await apiPatch("/profile", {
        date_of_birth: form.date_of_birth || null,
        sex_at_birth: form.sex_at_birth || null,
        gender_identity: form.gender_identity || null,
        height_cm: form.height_cm ? Number(form.height_cm) : null,
        weight_kg: form.weight_kg ? Number(form.weight_kg) : null,
        blood_type: form.blood_type || null,
        ancestry_context: form.ancestry_context || null,
        smoking_status: form.smoking_status || null,
        alcohol_units_per_week: form.alcohol_units_per_week ? Number(form.alcohol_units_per_week) : null,
        activity_level: form.activity_level || null,
        pregnancy_status: form.pregnancy_status || null,
        conditions: form.conditions.filter((item) => item.name.trim()),
        allergies: form.allergies.filter((item) => item.substance.trim()),
        family_history: form.family_history.filter((item) => item.relation.trim() && item.condition.trim()),
        notes: form.notes || null,
      });
      await profile.refresh();
      push("Profile updated. Changes are reflected in the digital twin.", "success");
    } catch (error) {
      push(errorMessage(error), "error");
    } finally {
      setSaving(false);
    }
  };

  const signOut = async () => {
    await logout();
    router.replace("/login");
  };

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Configuration"
        title="Settings"
        description="Maintain the demographic and clinical context that POLIS uses to interpret measurements. Missing data stays visible."
        actions={
          <Button variant="primary" onClick={save} loading={saving}>
            <Save className="h-3.5 w-3.5" /> Save profile
          </Button>
        }
      />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,0.65fr)]">
        <div className="space-y-4">
          <Panel>
            <SectionHeader
              title="Core profile"
              description="Demographics, body measurements and lifestyle context. Blank fields are treated as unknown."
              action={<UserRound className="h-4 w-4 text-dim" />}
            />
            <form onSubmit={save} className="space-y-5 p-5">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <label>
                  <span className="mb-1.5 block text-[12px] font-medium text-muted">Date of birth</span>
                  <input
                    type="date"
                    className="input"
                    value={form.date_of_birth}
                    max={new Date().toISOString().slice(0, 10)}
                    onChange={(event) => set("date_of_birth", event.target.value)}
                  />
                </label>
                <label>
                  <span className="mb-1.5 block text-[12px] font-medium text-muted">Sex at birth</span>
                  <select className="input" value={form.sex_at_birth} onChange={(event) => set("sex_at_birth", event.target.value)}>
                    <option value="">Not recorded</option>
                    <option value="female">Female</option>
                    <option value="male">Male</option>
                    <option value="intersex">Intersex</option>
                    <option value="prefer_not_to_say">Prefer not to say</option>
                  </select>
                </label>
                <label>
                  <span className="mb-1.5 block text-[12px] font-medium text-muted">Gender identity</span>
                  <input
                    className="input"
                    value={form.gender_identity}
                    onChange={(event) => set("gender_identity", event.target.value)}
                    placeholder="Optional"
                  />
                </label>
                <label>
                  <span className="mb-1.5 block text-[12px] font-medium text-muted">Blood type</span>
                  <select className="input" value={form.blood_type} onChange={(event) => set("blood_type", event.target.value)}>
                    <option value="">Not recorded</option>
                    {["O+", "O−", "A+", "A−", "B+", "B−", "AB+", "AB−", "unknown"].map((type) => <option key={type}>{type}</option>)}
                  </select>
                </label>
                <label>
                  <span className="mb-1.5 block text-[12px] font-medium text-muted">Height (cm)</span>
                  <input
                    type="number"
                    min={50}
                    max={260}
                    step="0.1"
                    className="input"
                    value={form.height_cm}
                    onChange={(event) => set("height_cm", event.target.value)}
                  />
                </label>
                <label>
                  <span className="mb-1.5 block text-[12px] font-medium text-muted">Weight (kg)</span>
                  <input
                    type="number"
                    min={20}
                    max={400}
                    step="0.1"
                    className="input"
                    value={form.weight_kg}
                    onChange={(event) => set("weight_kg", event.target.value)}
                  />
                </label>
                <label>
                  <span className="mb-1.5 block text-[12px] font-medium text-muted">Smoking status</span>
                  <select className="input" value={form.smoking_status} onChange={(event) => set("smoking_status", event.target.value)}>
                    <option value="">Not recorded</option>
                    <option value="never">Never</option>
                    <option value="former">Former</option>
                    <option value="current">Current</option>
                  </select>
                </label>
                <label>
                  <span className="mb-1.5 block text-[12px] font-medium text-muted">Alcohol (units per week)</span>
                  <input
                    type="number"
                    min={0}
                    max={200}
                    step="0.5"
                    className="input"
                    value={form.alcohol_units_per_week}
                    onChange={(event) => set("alcohol_units_per_week", event.target.value)}
                  />
                </label>
                <label>
                  <span className="mb-1.5 block text-[12px] font-medium text-muted">Activity level</span>
                  <select className="input" value={form.activity_level} onChange={(event) => set("activity_level", event.target.value)}>
                    <option value="">Not recorded</option>
                    <option value="sedentary">Sedentary</option>
                    <option value="lightly_active">Lightly active</option>
                    <option value="moderately_active">Moderately active</option>
                    <option value="very_active">Very active</option>
                  </select>
                </label>
                <label>
                  <span className="mb-1.5 block text-[12px] font-medium text-muted">Pregnancy status</span>
                  <select className="input" value={form.pregnancy_status} onChange={(event) => set("pregnancy_status", event.target.value)}>
                    <option value="">Not recorded</option>
                    <option value="not_pregnant">Not pregnant</option>
                    <option value="pregnant">Pregnant</option>
                    <option value="lactating">Lactating</option>
                    <option value="not_applicable">Not applicable</option>
                    <option value="prefer_not_to_say">Prefer not to say</option>
                  </select>
                </label>
                <label className="sm:col-span-2">
                  <span className="mb-1.5 block text-[12px] font-medium text-muted">Ancestry context</span>
                  <input
                    className="input"
                    value={form.ancestry_context}
                    onChange={(event) => set("ancestry_context", event.target.value)}
                    placeholder="Self-reported, optional. Ancestry is not a substitute for genotype."
                  />
                </label>
                <label className="sm:col-span-2">
                  <span className="mb-1.5 block text-[12px] font-medium text-muted">Notes</span>
                  <textarea
                    className="input min-h-20"
                    value={form.notes}
                    onChange={(event) => set("notes", event.target.value)}
                    placeholder="Context that does not fit elsewhere. Do not use this field for emergency information."
                  />
                </label>
              </div>
              <div className="flex justify-end border-t border-line pt-4">
                <Button type="submit" variant="primary" loading={saving}>
                  <Save className="h-3.5 w-3.5" /> Save changes
                </Button>
              </div>
            </form>
          </Panel>

          <Panel>
            <SectionHeader
              title="Conditions"
              description="Self-reported. Not a diagnosis by POLIS."
              action={<Badge tone="muted">{form.conditions.length}</Badge>}
            />
            <div className="space-y-2 p-5">
              {form.conditions.map((condition, index) => (
                <div key={index} className="grid grid-cols-[minmax(0,1fr)_88px_44px] gap-2">
                  <input
                    className="input"
                    placeholder="Condition"
                    aria-label={`Condition ${index + 1}`}
                    value={condition.name}
                    onChange={(event) => {
                      const next = [...form.conditions];
                      next[index] = { ...condition, name: event.target.value };
                      set("conditions", next);
                    }}
                  />
                  <input
                    className="input"
                    type="number"
                    placeholder="Year"
                    aria-label={`Year diagnosed for condition ${index + 1}`}
                    value={condition.diagnosed_year ?? ""}
                    onChange={(event) => {
                      const next = [...form.conditions];
                      next[index] = { ...condition, diagnosed_year: event.target.value ? Number(event.target.value) : null };
                      set("conditions", next);
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => set("conditions", form.conditions.filter((_, itemIndex) => itemIndex !== index))}
                    className="flex h-11 w-11 items-center justify-center text-dim hover:text-danger"
                    aria-label={`Remove condition ${index + 1}`}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={() => set("conditions", [...form.conditions, { name: "", diagnosed_year: null, status: "active" }])}
                className="btn btn-ghost -ml-2"
              >
                <Plus className="h-3.5 w-3.5" /> Add condition
              </button>
            </div>
          </Panel>

          <Panel>
            <SectionHeader
              title="Allergies"
              description="A reported allergy is not the same as a confirmed hypersensitivity."
              action={<Badge tone="amber">{form.allergies.length}</Badge>}
            />
            <div className="space-y-2 p-5">
              {form.allergies.map((allergy, index) => (
                <div key={index} className="grid grid-cols-[minmax(0,1fr)_minmax(0,0.8fr)_88px_44px] gap-2">
                  <input
                    className="input"
                    placeholder="Substance"
                    aria-label={`Allergy substance ${index + 1}`}
                    value={allergy.substance}
                    onChange={(event) => {
                      const next = [...form.allergies];
                      next[index] = { ...allergy, substance: event.target.value };
                      set("allergies", next);
                    }}
                  />
                  <input
                    className="input"
                    placeholder="Reaction"
                    aria-label={`Reaction for allergy ${index + 1}`}
                    value={allergy.reaction ?? ""}
                    onChange={(event) => {
                      const next = [...form.allergies];
                      next[index] = { ...allergy, reaction: event.target.value };
                      set("allergies", next);
                    }}
                  />
                  <select
                    className="input"
                    aria-label={`Severity for allergy ${index + 1}`}
                    value={allergy.severity ?? "unknown"}
                    onChange={(event) => {
                      const next = [...form.allergies];
                      next[index] = { ...allergy, severity: event.target.value as Allergy["severity"] };
                      set("allergies", next);
                    }}
                  >
                    {["unknown", "mild", "moderate", "severe"].map((severity) => (
                      <option key={severity} value={severity}>{severity.charAt(0).toUpperCase() + severity.slice(1)}</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => set("allergies", form.allergies.filter((_, itemIndex) => itemIndex !== index))}
                    className="flex h-11 w-11 items-center justify-center text-dim hover:text-danger"
                    aria-label={`Remove allergy ${index + 1}`}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={() => set("allergies", [...form.allergies, { substance: "", reaction: "", severity: "unknown", source: "Self-reported" }])}
                className="btn btn-ghost -ml-2"
              >
                <Plus className="h-3.5 w-3.5" /> Add allergy
              </button>
            </div>
          </Panel>
        </div>

        <div className="space-y-4">
          <Panel>
            <SectionHeader title="Account" />
            <div className="space-y-3 p-5">
              <div className="border border-line bg-ink p-4">
                <div className="text-[12px] text-dim">Name</div>
                <div className="mt-1 text-[14px] text-mist">{user?.name}</div>
                <div className="mt-3 text-[12px] text-dim">Email</div>
                <div className="mt-1 break-all text-[14px] text-mist">{user?.email}</div>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <Badge tone={user?.is_demo ? "amber" : "signal"}>{user?.is_demo ? "Demonstration account" : sentenceCase(user?.role ?? "Member")}</Badge>
                  {user?.created_at && <span className="font-mono text-[12px] text-dim">Created {formatDate(user.created_at)}</span>}
                </div>
              </div>
              <div className="flex items-center gap-2 text-[13px] text-dim">
                <ShieldCheck className="h-4 w-4 text-mint" />
                HttpOnly session, scrypt password hash
              </div>
              <Button variant="secondary" className="w-full" onClick={signOut}>
                <LogOut className="h-3.5 w-3.5" /> Sign out
              </Button>
            </div>
          </Panel>

          <Panel>
            <SectionHeader title="Data permissions" />
            <div className="space-y-3 p-5">
              <p className="text-[13px] leading-relaxed text-muted">
                AI processing, research participation and federated learning are independently controlled.
              </p>
              <Link href="/privacy" className="btn btn-secondary w-full">
                <ShieldCheck className="h-3.5 w-3.5" /> Manage privacy and data
              </Link>
            </div>
          </Panel>

          <Panel>
            <SectionHeader
              title="Deployment"
              action={<Settings2 className="h-4 w-4 text-dim" />}
            />
            <div className="divide-y divide-line">
              {[
                ["Version", "0.1.0"],
                ["Environment", "Development"],
                ["Simulation engine", "0.3.0-experimental"],
                ["Federated module", "Simulation only"],
                ["Regulatory status", "Not a medical device"],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center justify-between gap-3 px-5 py-3">
                  <span className="text-[13px] text-muted">{label}</span>
                  <span className={cn("text-[13px]", label === "Regulatory status" ? "text-amber" : "text-mist/85")}>{value}</span>
                </div>
              ))}
            </div>
          </Panel>

          <Panel>
            <SectionHeader
              title="Model status"
              action={<Badge tone="muted">Experimental</Badge>}
            />
            <div className="divide-y divide-line">
              {(models.data?.models ?? []).map((model) => (
                <details key={model.id} className="group px-5 py-3">
                  <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3">
                    <span className="min-w-0">
                      <span className="block truncate text-[14px] text-mist">{model.name}</span>
                      <span className="mt-0.5 block font-mono text-[12px] text-dim">{model.version}</span>
                    </span>
                    <span className="flex shrink-0 items-center gap-2">
                      <Badge tone={model.status.includes("experimental") ? "violet" : "amber"}>
                        {sentenceCase(model.status)}
                      </Badge>
                      <ChevronDown
                        className="h-4 w-4 text-dim transition-transform group-open:rotate-180"
                        aria-hidden="true"
                      />
                    </span>
                  </summary>
                  <div className="mt-2 space-y-1.5 border-t border-line pt-3">
                    <p className="text-[13px] leading-relaxed text-muted">{model.description}</p>
                    <p className="text-[12.5px] leading-relaxed text-amber">{model.limitations}</p>
                  </div>
                </details>
              ))}
              {!models.data?.models.length && <div className="px-5 py-4 text-[13px] text-dim">Model registry unavailable.</div>}
            </div>
            <div className="border-t border-line px-5 py-3">
              <p className="text-[12px] leading-relaxed text-dim">No listed model is clinically validated.</p>
            </div>
          </Panel>

          <Callout tone="warning" title="Model behavior">
            Experimental simulations, demonstration genetics and wearable estimates are not validated clinical data.
            Profile edits change what POLIS can display, not what is medically true.
          </Callout>

          <Link
            href="/privacy"
            className="flex min-h-11 items-center gap-2 border border-line px-5 py-3 text-[13px] text-muted transition-colors hover:border-[#3b453c] hover:text-mist"
          >
            <AlertTriangle className="h-4 w-4 shrink-0 text-amber" />
            Export or delete your data
          </Link>
        </div>
      </div>
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

function sentenceCase(value: string) {
  const text = value.replaceAll("_", " ").replaceAll("-", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function SettingsLoading() {
  return (
    <div className="flex min-h-[320px] items-center justify-center gap-3" role="status">
      <LoaderCircle className="h-5 w-5 animate-spin text-signal" aria-hidden="true" />
      <span className="text-[13px] text-muted">Loading settings</span>
    </div>
  );
}
