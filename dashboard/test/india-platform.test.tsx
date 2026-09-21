import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
import {
  StatCard,
  SecurityStatusBadge,
  ElectionBreadcrumb,
  IndiaMap,
  TrusteeCard,
  CryptoPipeline,
  ConstituencyCard,
} from "@/components/common";
import CommandCenterPage from "@/app/page";
import { StateFeature } from "@/lib/types";

// Mock AuthContext
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    user: { id: "1", username: "commissioner", role: "ADMIN", is_active: true, created_at: "" },
    token: "mock-token",
    role: "ADMIN",
    logout: vi.fn(),
  }),
}));

// Mock API Client
vi.mock("@/lib/api-client", () => ({
  api: {
    getGeographyMapData: vi.fn().mockResolvedValue({
      viewbox: "0 0 600 650",
      title: "India Electoral Geography",
      features: [
        {
          code: "KA",
          name: "Karnataka",
          capital: "Bengaluru",
          region: "Southern",
          pc_count: 28,
          ac_count: 224,
          elector_count_est: 53800000,
          d: "M 180,380 L 260,380 L 250,500 L 190,480 Z",
          center: [15.3173, 75.7139],
          turnout_pct: 71.4,
          anomalies_detected: 0,
          verification_status: "VERIFIED",
        },
        {
          code: "MH",
          name: "Maharashtra",
          capital: "Mumbai",
          region: "Western",
          pc_count: 48,
          ac_count: 288,
          elector_count_est: 92400000,
          d: "M 140,280 L 260,280 L 250,380 L 140,360 Z",
          center: [19.7515, 75.7139],
          turnout_pct: 61.3,
          anomalies_detected: 0,
          verification_status: "VERIFIED",
        },
      ],
    }),
    getNationalSummary: vi.fn().mockResolvedValue({
      total_states: 12,
      total_pcs: 64,
      total_acs: 512,
      national_registered_electors_est: 450000000,
      simulated_ballots_cast: 142850,
      national_turnout_pct: 68.4,
      active_trustees: 3,
      trustee_threshold: "2-of-3",
      verification_integrity_pct: 100.0,
      disclaimer: "Research Prototype — Indian Electoral Simulation",
      states_summary: [],
    }),
    getGeographyStates: vi.fn().mockResolvedValue({
      states: [
        { code: "KA", name: "Karnataka", total_pcs: 28, total_acs: 224 },
        { code: "MH", name: "Maharashtra", total_pcs: 48, total_acs: 288 },
      ],
      total: 2,
    }),
    getGeographyState: vi.fn().mockResolvedValue({
      code: "KA",
      name: "Karnataka",
      capital: "Bengaluru",
      total_pcs: 28,
      total_acs: 224,
      parliamentary_constituencies: [
        {
          id: "KA-PC-24",
          pc_id: "KA-PC-24",
          name: "Bengaluru Central",
          pc_name: "Bengaluru Central",
          pc_number: 24,
          state_code: "KA",
          category: "GEN",
          assembly_constituencies: [{ name: "Sarvagnanagar" }],
          total_electors: 1950000,
        },
      ],
    }),
    getGeographyPC: vi.fn().mockResolvedValue({
      id: "KA-PC-24",
      name: "Bengaluru Central",
      state_code: "KA",
      total_electors: 1950000,
      live_polling_stations: [],
      candidates: [],
    }),
    getPCPollingStations: vi.fn().mockResolvedValue({
      pc_id: "KA-PC-24",
      polling_stations: [],
      total: 0,
    }),
    getPCCandidates: vi.fn().mockResolvedValue({
      pc_id: "KA-PC-24",
      candidates: [],
      total: 0,
    }),
  },
  isDemoMode: () => false,
}));

describe("Indian Electoral Platform Components", () => {
  it("renders StatCard with value, subtitle and badge", () => {
    render(
      <StatCard
        title="Reference States & UTs"
        value={12}
        subtitle="Constitutional Jurisdictions"
        badge="12 JURISDICTIONS"
      />
    );
    expect(screen.getByText("Reference States & UTs")).toBeDefined();
    expect(screen.getByText("12")).toBeDefined();
    expect(screen.getByText("Constitutional Jurisdictions")).toBeDefined();
    expect(screen.getByText("12 JURISDICTIONS")).toBeDefined();
  });

  it("renders SecurityStatusBadge with accessible text and not color only", () => {
    const { container } = render(<SecurityStatusBadge status="VERIFIED" />);
    const badge = container.querySelector('[aria-label="VERIFIED: Cryptographically Verified"]');
    expect(badge).toBeDefined();
    expect(screen.getByText("VERIFIED")).toBeDefined();
  });

  it("renders ElectionBreadcrumb across electoral hierarchy", () => {
    render(
      <ElectionBreadcrumb
        stateName="Karnataka"
        stateCode="KA"
        pcName="Bengaluru Central"
        pcId="KA-PC-24"
        stationCode="KA-24-PS-042"
        deviceName="CU-KA24-042"
      />
    );
    expect(screen.getByText("India (National)")).toBeDefined();
    expect(screen.getByText("Karnataka")).toBeDefined();
    expect(screen.getByText("Bengaluru Central")).toBeDefined();
    expect(screen.getByText("KA-24-PS-042")).toBeDefined();
    expect(screen.getByText("CU-KA24-042")).toBeDefined();
  });

  it("renders IndiaMap with SVG paths, hover tooltips and selection triggers", () => {
    const mockSelect = vi.fn();
    const mockFeatures: StateFeature[] = [
      {
        code: "KA",
        name: "Karnataka",
        capital: "Bengaluru",
        region: "Southern",
        pc_count: 28,
        ac_count: 224,
        elector_count_est: 53800000,
        d: "M 180,380 L 260,380 L 250,500 L 190,480 Z",
        center: [15.3173, 75.7139],
        turnout_pct: 71.4,
        anomalies_detected: 0,
        verification_status: "VERIFIED",
      },
    ];

    render(
      <IndiaMap
        features={mockFeatures}
        selectedStateCode="KA"
        onSelectState={mockSelect}
      />
    );

    const kaGroup = screen.getByRole("button", { name: /Karnataka \(KA\)/i });
    expect(kaGroup).toBeDefined();
    fireEvent.click(kaGroup);
    expect(mockSelect).toHaveBeenCalledWith("KA");
  });

  it("renders TrusteeCard with 2-of-3 threshold metadata and zero-secret isolation notice", () => {
    render(
      <TrusteeCard
        index={1}
        name="ECI Chief Election Commissioner"
        role="Constitutional Authority"
        verificationKeyFingerprint="04:b8:9f:...:12"
        commitmentHash="a8f9c...082"
        isQual={true}
        hasSubmittedShare={true}
        status="ONLINE"
      />
    );

    expect(screen.getByText("ECI Chief Election Commissioner")).toBeDefined();
    expect(screen.getByText("QUAL")).toBeDefined();
    expect(screen.getByText("04:b8:9f:...:12")).toBeDefined();
    expect(screen.getByText("Decryption Share Verified")).toBeDefined();
    expect(screen.getByText("x_1 strictly isolated")).toBeDefined();
  });

  it("renders CryptoPipeline with 8 stages and toggles stage details", () => {
    render(<CryptoPipeline />);
    expect(screen.getByText("End-to-End Cryptographic Verification Pipeline")).toBeDefined();
    expect(screen.getByText("ALL 8 STAGES ACTIVE")).toBeDefined();

    // Stage 1 default
    expect(screen.getByText("Stage 01:")).toBeDefined();

    // Click Stage 6 (2-of-3 GJKR DKG)
    const stage6Btn = screen.getByRole("button", { name: /06.*2-of-3 GJKR DKG/i });
    fireEvent.click(stage6Btn);
    expect(screen.getByText("Stage 06:")).toBeDefined();
  });

  it("renders ConstituencyCard with assembly segments and electors", () => {
    const pc = {
      pc_id: "KA-PC-24",
      pc_name: "Bengaluru Central",
      state_code: "KA",
      category: "GEN",
      assembly_constituencies: [{ name: "Sarvagnanagar" }, { name: "Shanti Nagar" }],
      estimated_electors: 1950000,
      simulated_turnout_pct: 72.1,
    };

    render(<ConstituencyCard pc={pc} isSelected={true} />);
    expect(screen.getByText("Bengaluru Central")).toBeDefined();
    expect(screen.getByText("1.95M")).toBeDefined();
    expect(screen.getByText("72.1%")).toBeDefined();
    expect(screen.getByText("Sarvagnanagar")).toBeDefined();
  });

  it("renders CommandCenterPage with all 8 main cards, disclaimer banner, and trustee network", async () => {
    render(<CommandCenterPage />);

    // Header & Disclaimer
    expect(screen.getByText("SECUREVOTE")).toBeDefined();
    expect(screen.getByText("v3.3 Research")).toBeDefined();
    expect(screen.getByText(/RESEARCH PROTOTYPE & INDIAN ELECTORAL SIMULATION/i)).toBeDefined();

    // Metrics
    await waitFor(() => {
      expect(screen.getByText("Active Pilot Election")).toBeDefined();
      expect(screen.getByText("Reference States & UTs")).toBeDefined();
      expect(screen.getByText("Simulated Polling Stations")).toBeDefined();
      expect(screen.getByText("Cryptographic Ballots")).toBeDefined();
      expect(screen.getByText("Trustee Network Threshold")).toBeDefined();
      expect(screen.getByText("Detected Anomalies")).toBeDefined();
    });

    // Trustee Section
    expect(screen.getByText("ECI Chief Election Commissioner")).toBeDefined();
    expect(screen.getByText("IIT Madras Cryptography Lab")).toBeDefined();
    expect(screen.getByText("Supreme Court Appointed Observer")).toBeDefined();
  });
});
