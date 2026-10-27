import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MatchExplanationCard } from "./MatchExplanationCard";

describe("MatchExplanationCard", () => {
  it("renders match score and rule point breakdown", () => {
    const explanation = {
      rule_points: {
        category_match: 15,
        text_similarity: 25,
        shared_domain_terms: 20,
        incident_date_proximity: 10,
        incident_ref_exact_match: 0,
      },
      shared_domain_terms: ["hostel", "mess"],
      shared_keywords: ["refund", "deposit", "caution"],
    };

    render(<MatchExplanationCard score={70} explanation={explanation} />);

    expect(screen.getByText(/70\/100/)).toBeInTheDocument();
    expect(screen.getByText(/category match/i)).toBeInTheDocument();
    expect(screen.getByText(/text similarity/i)).toBeInTheDocument();
    expect(screen.getByText("hostel")).toBeInTheDocument();
    expect(screen.getByText("mess")).toBeInTheDocument();
    expect(screen.getByText("refund")).toBeInTheDocument();
  });
});
