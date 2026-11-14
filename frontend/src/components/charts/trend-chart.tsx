"use client";

import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Trend } from "@/lib/types";
import { formatDate, formatNumber } from "@/lib/format";

const axisTick = { fill: "#8d968a", fontSize: 12, fontFamily: "IBM Plex Mono, monospace" };

function TrendTooltip({
  active,
  payload,
  label,
  unit,
}: {
  active?: boolean;
  payload?: { value?: number | string; name?: string }[];
  label?: string;
  unit: string;
}) {
  if (!active || !payload?.length) return null;
  const value = payload.find((item) => item.name === "value")?.value ?? payload[0]?.value;
  return (
    <div className="rounded-[2px] border border-line bg-panel px-3 py-2">
      <div className="font-mono text-[11px] text-dim">{label}</div>
      <div className="mt-1.5 number text-[15px] text-mist">
        {typeof value === "number" ? formatNumber(value) : value} <span className="font-mono text-[11px] text-dim">{unit}</span>
      </div>
    </div>
  );
}

export function TrendChart({ trend, height = 230 }: { trend: Trend; height?: number }) {
  const data = trend.points.map((point) => ({
    date: formatDate(point.date, { day: "2-digit", month: "short" }),
    fullDate: formatDate(point.date),
    value: point.value,
    ref_low: point.ref_low,
    ref_high: point.ref_high,
  }));
  const latest = trend.points[trend.points.length - 1];
  const hasBand = latest?.ref_low !== null && latest?.ref_high !== null;
  const hasHigh = latest?.ref_high !== null;
  const hasLow = latest?.ref_low !== null;
  const values = data.map((point) => point.value);
  const bounds = [...values, latest?.ref_low ?? values[0], latest?.ref_high ?? values[0]].filter(
    (value): value is number => typeof value === "number" && !Number.isNaN(value),
  );
  const min = Math.min(...bounds);
  const max = Math.max(...bounds);
  const padding = (max - min || 1) * 0.22;

  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="#2a312b" vertical={false} />
          <XAxis
            dataKey="date"
            tick={axisTick}
            axisLine={{ stroke: "#2a312b" }}
            tickLine={false}
            minTickGap={24}
          />
          <YAxis
            domain={[min - padding, max + padding]}
            tick={axisTick}
            axisLine={false}
            tickLine={false}
            width={52}
            tickFormatter={(value: number) => formatNumber(value, Math.abs(value) < 10 ? 1 : 0)}
          />
          <Tooltip content={<TrendTooltip unit={trend.unit} />} cursor={{ stroke: "#3b453c", strokeDasharray: "2 3" }} />
          {hasBand && (
            <ReferenceArea
              y1={latest.ref_low ?? undefined}
              y2={latest.ref_high ?? undefined}
              fill="rgba(154,219,174,0.07)"
              stroke="rgba(154,219,174,0.28)"
              strokeDasharray="3 4"
            />
          )}
          {!hasBand && hasHigh && (
            <ReferenceLine y={latest.ref_high ?? undefined} stroke="rgba(232,185,121,0.4)" strokeDasharray="3 4" />
          )}
          {!hasBand && hasLow && (
            <ReferenceLine y={latest.ref_low ?? undefined} stroke="rgba(232,185,121,0.4)" strokeDasharray="3 4" />
          )}
          <Line
            type="monotone"
            dataKey="value"
            stroke="#7dded6"
            strokeWidth={1.8}
            dot={{ r: 2.2, fill: "#7dded6", strokeWidth: 0 }}
            activeDot={{ r: 3.6, fill: "#eef1ea", stroke: "rgba(125,222,214,0.35)", strokeWidth: 4 }}
            name="value"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
