import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EvidenceBadge, Badge } from "@/components/ui/badge";
import { StatusPill } from "@/components/ui/status";

describe("evidence labels", () => {
  it("renders clinical evidence distinctly from model estimates", () => {
    const { rerender } = render(<EvidenceBadge value="established_clinical_evidence" />);
    expect(screen.getByText("Clinical evidence")).toBeInTheDocument();
    rerender(<EvidenceBadge value="model_estimate" />);
    expect(screen.getByText("Model estimate")).toBeInTheDocument();
    rerender(<EvidenceBadge value="unknown" />);
    expect(screen.getByText("Unknown")).toBeInTheDocument();
  });

  it("renders range status with a text label, not colour alone", () => {
    const { rerender } = render(<StatusPill status="high" />);
    expect(screen.getByText("Above interval")).toBeInTheDocument();
    rerender(<StatusPill status="normal" />);
    expect(screen.getByText("In interval")).toBeInTheDocument();
    rerender(<StatusPill status="indeterminate" />);
    expect(screen.getByText("Indeterminate")).toBeInTheDocument();
  });

  it("renders generic badges", () => {
    render(<Badge tone="violet">Synthetic</Badge>);
    expect(screen.getByText("Synthetic")).toBeInTheDocument();
  });
});
