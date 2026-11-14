"use client";

import { useState } from "react";
import { cn } from "@/lib/format";
import type { TwinSystem } from "@/lib/types";

const IMAGE = { x: 24, y: 0, width: 372, height: 620 };

type NodeConfig = {
  sx: number;
  sy: number;
  side: "left" | "right";
  rx: number;
  ry: number;
};

/**
 * Approximate navigation anchors over the licensed anatomical illustration.
 * These are interface coordinates, not measurements of a person's organs.
 */
const NODES: Record<string, NodeConfig> = {
  brain: { sx: 300, sy: 55, side: "right", rx: 22, ry: 25 },
  endocrine: { sx: 300, sy: 150, side: "right", rx: 15, ry: 16 },
  lungs: { sx: 245, sy: 248, side: "right", rx: 42, ry: 38 },
  heart: { sx: 348, sy: 260, side: "right", rx: 20, ry: 18 },
  liver: { sx: 278, sy: 315, side: "left", rx: 44, ry: 28 },
  immune: { sx: 364, sy: 332, side: "right", rx: 24, ry: 24 },
  kidneys: { sx: 350, sy: 370, side: "right", rx: 22, ry: 25 },
  digestive: { sx: 290, sy: 405, side: "left", rx: 46, ry: 38 },
  metabolic: { sx: 316, sy: 390, side: "right", rx: 48, ry: 34 },
  musculoskeletal: { sx: 300, sy: 565, side: "left", rx: 40, ry: 62 },
};

const COLORS: Record<string, { base: string; tint: string }> = {
  available: { base: "#9adbae", tint: "rgba(154,219,174,.14)" },
  review: { base: "#e8b979", tint: "rgba(232,185,121,.14)" },
  partial: { base: "#7dded6", tint: "rgba(125,222,214,.12)" },
  missing: { base: "#8d968a", tint: "rgba(141,150,138,.07)" },
  experimental: { base: "#bba9e8", tint: "rgba(187,169,232,.14)" },
};

const LEGEND = [
  { key: "available", label: "Available", dot: "bg-mint" },
  { key: "review", label: "Review", dot: "bg-amber" },
  { key: "partial", label: "Partial", dot: "bg-signal" },
  { key: "missing", label: "Missing", dot: "bg-dim" },
];

function statusLabel(status: string): string {
  return (
    {
      available: "data available",
      review: "review indicated",
      partial: "partial data",
      missing: "data missing",
      experimental: "experimental",
    }[status] ?? status
  );
}

export function BodyMap({
  systems,
  selectedId,
  onSelect,
  className,
  compact = false,
}: {
  systems: TwinSystem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  className?: string;
  compact?: boolean;
}) {
  const [hovered, setHovered] = useState<string | null>(null);
  const map = new Map(systems.map((system) => [system.id, system]));
  const activeId = hovered ?? selectedId;
  const colorFor = (id: string) => COLORS[map.get(id)?.status ?? "missing"] ?? COLORS.missing;

  return (
    <div className={cn("relative flex h-full min-h-0 flex-col", className)}>
      <div className="relative min-h-0 flex-1">
        <svg
          viewBox="0 0 420 620"
          className="absolute inset-0 h-full w-full"
          fill="none"
          aria-label="Interactive anterior anatomical navigation illustration"
        >
          {/* Restrained orientation plane: one crosshair and small ticks, no grid. */}
          <g stroke="rgba(238,241,234,.07)" strokeWidth="0.7">
            <line x1="210" y1="18" x2="210" y2="602" />
            <line x1="44" y1="300" x2="376" y2="300" />
            {Array.from({ length: 9 }).map((_, index) => (
              <line key={`tick-y-${index}`} x1="205" y1={80 + index * 60} x2="215" y2={80 + index * 60} />
            ))}
            {Array.from({ length: 5 }).map((_, index) => (
              <line key={`tick-x-${index}`} x1={90 + index * 60} y1="296" x2={90 + index * 60} y2="304" />
            ))}
          </g>

          <image
            href="/anatomy/body-organs.svg"
            x={IMAGE.x}
            y={IMAGE.y}
            width={IMAGE.width}
            height={IMAGE.height}
            preserveAspectRatio="xMidYMid meet"
            style={{
              filter: "grayscale(0.85) sepia(0.1) brightness(0.72) contrast(1.2)",
              opacity: 0.85,
            }}
          />

          {systems.map((system) => {
            const config = NODES[system.id];
            if (!config) return null;
            const x = IMAGE.x + config.sx * 0.62;
            const y = config.sy * 0.62;
            const active = activeId === system.id;
            const colors = colorFor(system.id);
            const labelX = config.side === "left" ? x - 14 : x + 14;
            const anchor = config.side === "left" ? "end" : "start";
            return (
              <g
                key={system.id}
                role="button"
                tabIndex={0}
                aria-label={system.name}
                aria-pressed={selectedId === system.id}
                onClick={() => onSelect(system.id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelect(system.id);
                  }
                }}
                onMouseEnter={() => setHovered(system.id)}
                onMouseLeave={() => setHovered(null)}
                onFocus={() => setHovered(system.id)}
                onBlur={() => setHovered(null)}
                className="cursor-pointer outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal"
              >
                <title>{`${system.name}: ${statusLabel(system.status)}`}</title>
                <circle cx={x} cy={y} r="22" fill="transparent" />

                {active && (
                  <ellipse
                    cx={x}
                    cy={y}
                    rx={config.rx * 0.56}
                    ry={config.ry * 0.56}
                    fill={colors.tint}
                    stroke={colors.base}
                    strokeOpacity="0.32"
                    strokeWidth="0.8"
                  />
                )}
                <circle cx={x} cy={y} r={active ? 5 : 4} fill={colors.base} fillOpacity={active ? 1 : 0.8} />
                <circle
                  cx={x}
                  cy={y}
                  r={active ? 10 : 7}
                  stroke={colors.base}
                  strokeOpacity={active ? 0.8 : 0.35}
                  strokeWidth="0.9"
                />

                {active && (
                  <>
                    <text
                      x={labelX}
                      y={y - 2}
                      textAnchor={anchor}
                      fill="#eef1ea"
                      fontSize="12"
                      fontFamily="IBM Plex Sans, sans-serif"
                      stroke="#111512"
                      strokeWidth="3"
                      paintOrder="stroke"
                    >
                      {system.name}
                    </text>
                    <text
                      x={labelX}
                      y={y + 12}
                      textAnchor={anchor}
                      fill={colors.base}
                      fontSize="11"
                      fontFamily="IBM Plex Sans, sans-serif"
                      stroke="#111512"
                      strokeWidth="3"
                      paintOrder="stroke"
                    >
                      {statusLabel(system.status)}
                    </text>
                  </>
                )}
              </g>
            );
          })}
        </svg>

        <div className="pointer-events-none absolute inset-x-3 top-3 flex items-start justify-between gap-3 text-[11px] text-dim">
          <span>Navigation model, not a scan</span>
          <span>Anterior view</span>
        </div>
      </div>

      <div className="relative flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-t border-line px-3 py-2">
        <ul className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[11px] text-dim">
          {LEGEND.map((item) => (
            <li key={item.key} className="flex items-center gap-1.5">
              <span className={cn("h-1.5 w-1.5 rounded-full", item.dot)} aria-hidden="true" />
              {item.label}
            </li>
          ))}
        </ul>
        <a
          href="https://commons.wikimedia.org/wiki/File:202403_human_anatomy_organs.svg"
          target="_blank"
          rel="noreferrer noopener"
          className="inline-flex min-h-11 items-center text-[11px] text-dim underline decoration-line underline-offset-2 hover:text-muted lg:min-h-0"
        >
          Anatomy: DBCLS, CC BY 4.0
        </a>
      </div>
    </div>
  );
}
