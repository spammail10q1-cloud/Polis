import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { BodyMap } from "@/components/body-map";
import type { TwinSystem } from "@/lib/types";

const systems: TwinSystem[] = [
  {
    id: "liver",
    name: "Liver",
    tagline: "Metabolic processing",
    accent: "amber",
    status: "review",
    status_reason: "ALT above interval",
    completeness: 95,
    measurements: 6,
    genes: ["CYP2D6"],
    pathways: [],
    last_updated: null,
    signals: [],
    limitations: [],
  },
  {
    id: "kidneys",
    name: "Kidneys",
    tagline: "Filtration",
    accent: "cyan",
    status: "available",
    status_reason: "Within interval",
    completeness: 95,
    measurements: 5,
    genes: [],
    pathways: [],
    last_updated: null,
    signals: [],
    limitations: [],
  },
];

describe("BodyMap", () => {
  it("exposes selectable organs to the keyboard and pointer", () => {
    const onSelect = vi.fn();
    render(<BodyMap systems={systems} selectedId="liver" onSelect={onSelect} compact />);
    expect(screen.getByRole("button", { name: "Liver" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Kidneys" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Kidneys" }));
    expect(onSelect).toHaveBeenCalledWith("kidneys");
    fireEvent.keyDown(screen.getByRole("button", { name: "Liver" }), { key: "Enter" });
    expect(onSelect).toHaveBeenCalledWith("liver");
  });
});
