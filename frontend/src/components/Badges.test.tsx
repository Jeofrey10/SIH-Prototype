import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  StatusBadge,
  PriorityBadge,
  OverdueBadge,
  EscalationBadge,
  BureauChip,
  AccessLevelNotice,
} from "./Badges";

describe("Badges Components", () => {
  it("renders StatusBadge with formatted text", () => {
    render(<StatusBadge status="IN_INVESTIGATION" />);
    expect(screen.getByText(/IN INVESTIGATION/i)).toBeInTheDocument();
  });

  it("renders PriorityBadge with uppercase text", () => {
    render(<PriorityBadge priority="URGENT" />);
    expect(screen.getByText("URGENT")).toBeInTheDocument();
  });

  it("renders OverdueBadge only when overdue is true", () => {
    const { rerender } = render(<OverdueBadge isOverdue={false} />);
    expect(screen.queryByText(/Overdue/i)).not.toBeInTheDocument();

    rerender(<OverdueBadge isOverdue={true} />);
    expect(screen.getByText(/Overdue/i)).toBeInTheDocument();
  });

  it("renders EscalationBadge only when escalated is true", () => {
    const { rerender } = render(<EscalationBadge isEscalated={false} />);
    expect(screen.queryByText("ESCALATED")).not.toBeInTheDocument();

    rerender(<EscalationBadge isEscalated={true} />);
    expect(screen.getByText("ESCALATED")).toBeInTheDocument();
  });

  it("renders BureauChip with bureau code", () => {
    render(<BureauChip code="RB" />);
    expect(screen.getByText("RB")).toBeInTheDocument();
  });

  it("renders AccessLevelNotice for summary redacted view", () => {
    render(<AccessLevelNotice />);
    expect(
      screen.getByText(/Summary view - your bureau does not participate/i)
    ).toBeInTheDocument();
  });
});
