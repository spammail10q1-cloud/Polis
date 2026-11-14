import {
  Atom,
  Brain,
  Dna,
  FlaskConical,
  Gauge,
  GitBranch,
  HeartPulse,
  LayoutDashboard,
  Pill,
  ScanLine,
  Settings,
  ShieldCheck,
} from "lucide-react";

export type NavItem = {
  href: string;
  label: string;
  icon: typeof LayoutDashboard;
  group: "primary" | "secondary";
  hint?: string;
};

export const navItems: NavItem[] = [
  { href: "/overview", label: "Overview", icon: LayoutDashboard, group: "primary" },
  { href: "/biology", label: "My Biology", icon: Brain, group: "primary" },
  { href: "/twin", label: "Digital Twin", icon: ScanLine, group: "primary" },
  { href: "/what-if", label: "What If?", icon: GitBranch, group: "primary", hint: "Simulation" },
  { href: "/genetics", label: "Genetics", icon: Dna, group: "primary" },
  { href: "/biomarkers", label: "Biomarkers", icon: FlaskConical, group: "primary" },
  { href: "/medications", label: "Medications", icon: Pill, group: "primary" },
  { href: "/wearables", label: "Wearables", icon: HeartPulse, group: "primary" },
  { href: "/insights", label: "Insights", icon: Gauge, group: "primary" },
  { href: "/assistant", label: "POLIS AI", icon: Atom, group: "primary" },
  { href: "/privacy", label: "Privacy & Data", icon: ShieldCheck, group: "secondary" },
  { href: "/settings", label: "Settings", icon: Settings, group: "secondary" },
];

export const pageMeta: Record<string, { title: string }> = {
  "/overview": { title: "Overview" },
  "/biology": { title: "My Biology" },
  "/twin": { title: "Digital Twin" },
  "/what-if": { title: "What If?" },
  "/genetics": { title: "Genetics" },
  "/biomarkers": { title: "Biomarkers" },
  "/medications": { title: "Medications" },
  "/wearables": { title: "Wearables" },
  "/insights": { title: "Insights" },
  "/assistant": { title: "POLIS AI" },
  "/privacy": { title: "Privacy & Data" },
  "/settings": { title: "Settings" },
};
