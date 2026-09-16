import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import React from "react";
import DevicesPage from "@/app/devices/page";
import { StatusBadge } from "@/components/common/StatusBadge";
import { api } from "@/lib/api-client";
import { DeviceResponse } from "@/lib/types";

// Mock AuthContext
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    user: { id: "1", username: "admin", role: "ADMIN", is_active: true, created_at: "" },
    token: "mock-token",
    role: "ADMIN",
    logout: vi.fn(),
  }),
}));

// Mock API client
vi.mock("@/lib/api-client", () => ({
  api: {
    getElections: vi.fn(),
    getDevices: vi.fn(),
    registerDevice: vi.fn(),
    updateDeviceStatus: vi.fn(),
  },
}));

const mockDevices: DeviceResponse[] = [
  {
    id: "EVM-001",
    election_id: "EV-2026-001",
    name: "Precinct 1 Polling Station",
    status: "ACTIVE",
    device_hash: null,
    last_sequence_number: 42,
    total_votes_cast: 42,
    registered_at: "2026-09-16T10:00:00Z",
    activated_at: "2026-09-16T10:05:00Z",
    last_seen_at: "2026-09-16T10:30:00Z",
  },
  {
    id: "EVM-002",
    election_id: "EV-2026-001",
    name: "Precinct 2 Polling Station",
    status: "SUSPENDED",
    device_hash: null,
    last_sequence_number: 10,
    total_votes_cast: 10,
    registered_at: "2026-09-16T10:00:00Z",
    activated_at: "2026-09-16T10:05:00Z",
    last_seen_at: "2026-09-16T10:15:00Z",
  },
];

describe("Device Management & Status Badge Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.getElections as any).mockResolvedValue([
      { id: "EV-2026-001", title: "General Election 2026", state: "OPEN" },
    ]);
    (api.getDevices as any).mockResolvedValue(mockDevices);
  });

  it("renders status badges with appropriate styles", () => {
    const { rerender } = render(<StatusBadge status="ACTIVE" />);
    expect(screen.getByText("ACTIVE")).toBeInTheDocument();

    rerender(<StatusBadge status="SUSPENDED" />);
    expect(screen.getByText("SUSPENDED")).toBeInTheDocument();

    rerender(<StatusBadge status="REVOKED" />);
    expect(screen.getByText("REVOKED")).toBeInTheDocument();

    rerender(<StatusBadge status="OPEN" isDemo={true} />);
    expect(screen.getByText("OPEN")).toBeInTheDocument();
    expect(screen.getByTestId("demo-mode-badge")).toHaveTextContent("[DEMO-MODE]");
  });

  it("renders devices list with sequence counters and status actions", async () => {
    render(<DevicesPage />);

    await waitFor(() => {
      expect(screen.getByText("EVM-001")).toBeInTheDocument();
    });

    expect(screen.getByText("Precinct 1 Polling Station")).toBeInTheDocument();
    expect(screen.getByText("#42")).toBeInTheDocument();
    expect(screen.getByText("EVM-002")).toBeInTheDocument();
    expect(screen.getByText("#10")).toBeInTheDocument();

    // Check actions available to ADMIN
    expect(screen.getByText("Suspend")).toBeInTheDocument();
    expect(screen.getByText("Re-activate")).toBeInTheDocument();
  });
});
