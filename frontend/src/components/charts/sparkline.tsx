"use client";

import { cn } from "@/lib/format";

export function Sparkline({
  values,
  className,
  tone = "signal",
  height = 38,
  showArea = true,
}: {
  values: number[];
  className?: string;
  tone?: "signal" | "violet" | "amber" | "mint";
  height?: number;
  showArea?: boolean;
}) {
  if (!values.length) {
    return (
      <div className={cn("flex items-center font-mono text-[11px] text-dim", className)} style={{ height }}>
        No series
      </div>
    );
  }
  const width = 120;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const points = values.map((value, index) => {
    const x = values.length === 1 ? width / 2 : (index / (values.length - 1)) * width;
    const y = height - 5 - ((value - min) / range) * (height - 10);
    return [x, y] as const;
  });
  const path = points.map(([x, y], index) => `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${path} L${width},${height} L0,${height} Z`;
  const colors = {
    signal: { stroke: "#7dded6", fill: "rgba(125,222,214,0.09)" },
    violet: { stroke: "#bba9e8", fill: "rgba(187,169,232,0.09)" },
    amber: { stroke: "#e8b979", fill: "rgba(232,185,121,0.09)" },
    mint: { stroke: "#9adbae", fill: "rgba(154,219,174,0.09)" },
  }[tone];

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className={cn("w-full", className)}
      style={{ height }}
      aria-hidden="true"
    >
      {showArea && <path d={area} fill={colors.fill} stroke="none" />}
      <path d={path} fill="none" stroke={colors.stroke} strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" />
      {points.length === 1 && <circle cx={points[0][0]} cy={points[0][1]} r="2" fill={colors.stroke} />}
    </svg>
  );
}
