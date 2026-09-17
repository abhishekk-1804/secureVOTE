import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import EligibilityCheckerPage from "@/app/(public)/voter/eligibility/page";
import { api } from "@/lib/api-client";
import { ApiError } from "@/lib/format-error";

vi.mock("@/lib/api-client", () => ({
  api: {
    checkEligibility: vi.fn(),
  },
}));

describe("EligibilityCheckerPage Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the eligibility form with inputs and simulation notice", () => {
    render(<EligibilityCheckerPage />);

    expect(screen.getByText("Eligibility Checker")).toBeInTheDocument();
    expect(screen.getByText("SIMULATED ELIGIBILITY CHECK")).toBeInTheDocument();
    expect(screen.getByLabelText("Full Name")).toBeInTheDocument();
    expect(screen.getByLabelText("Date of Birth")).toBeInTheDocument();
    expect(screen.getByLabelText("Constituency")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Check Eligibility/i })).toBeInTheDocument();
  });

  it("submits the form and renders eligible result", async () => {
    vi.mocked(api.checkEligibility).mockResolvedValueOnce({
      status: "ELIGIBLE",
      reasons: ["All checks passed. Age >= 18 and registration verified."],
      voter: {
        id: "VTR-123456",
        name: "Aarav Sharma",
        constituency: "North District",
        registration_status: "VERIFIED",
      },
      notice: "SIMULATED STATUS",
    });

    render(<EligibilityCheckerPage />);

    fireEvent.change(screen.getByLabelText("Full Name"), { target: { value: "Aarav Sharma" } });
    fireEvent.change(screen.getByLabelText("Date of Birth"), { target: { value: "1995-05-15" } });
    fireEvent.change(screen.getByLabelText("Constituency"), { target: { value: "North District" } });

    fireEvent.click(screen.getByRole("button", { name: /Check Eligibility/i }));

    await waitFor(() => {
      expect(screen.getByText("Eligibility Status")).toBeInTheDocument();
    });
    expect(screen.getByText("ELIGIBLE")).toBeInTheDocument();
    expect(screen.getByText(/All checks passed/i)).toBeInTheDocument();
  });

  it("handles structured API error safely without [object Object]", async () => {
    vi.mocked(api.checkEligibility).mockRejectedValueOnce(
      new ApiError(400, "Bad Request", { detail: { message: "Constituency is not part of active election zone" } })
    );

    render(<EligibilityCheckerPage />);

    fireEvent.change(screen.getByLabelText("Full Name"), { target: { value: "Invalid User" } });
    fireEvent.change(screen.getByLabelText("Date of Birth"), { target: { value: "1990-01-01" } });
    fireEvent.change(screen.getByLabelText("Constituency"), { target: { value: "North District" } });

    fireEvent.click(screen.getByRole("button", { name: /Check Eligibility/i }));

    await waitFor(() => {
      expect(screen.getByText("Check Failed")).toBeInTheDocument();
    });

    const errorMsg = screen.getByText("Constituency is not part of active election zone");
    expect(errorMsg).toBeInTheDocument();
    expect(errorMsg.textContent).not.toContain("[object Object]");
  });
});
