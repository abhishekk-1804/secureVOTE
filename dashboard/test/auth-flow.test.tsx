import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import React from "react";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { api, setUnauthorizedHandler } from "@/lib/api-client";

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  usePathname: () => "/command",
}));

// Test component to consume context
function TestConsumer() {
  const { user, token, role, logout } = useAuth();
  return (
    <div>
      <span data-testid="auth-user">{user?.username || "anonymous"}</span>
      <span data-testid="auth-role">{role || "no-role"}</span>
      <span data-testid="auth-token">{token || "no-token"}</span>
      <button onClick={logout}>Trigger Logout</button>
    </div>
  );
}

describe("Authentication & 401 Handling Flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("restores user session from localStorage if token is valid", async () => {
    localStorage.setItem("securevote_token", "existing-valid-jwt");

    vi.spyOn(api, "getMe").mockResolvedValue({
      id: "u-123",
      username: "admin",
      role: "ADMIN",
      is_active: true,
      created_at: "2026-09-16T10:00:00Z",
    });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("auth-user")).toHaveTextContent("admin");
      expect(screen.getByTestId("auth-role")).toHaveTextContent("ADMIN");
      expect(screen.getByTestId("auth-token")).toHaveTextContent("existing-valid-jwt");
    });
  });

  it("handles 401 Unauthorized by clearing session and redirecting to /login", async () => {
    localStorage.setItem("securevote_token", "expired-token");

    // getMe throws 401 error
    vi.spyOn(api, "getMe").mockRejectedValue(new Error("401 Unauthorized"));

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("auth-user")).toHaveTextContent("anonymous");
      expect(screen.getByTestId("auth-token")).toHaveTextContent("no-token");
    });

    // Verify localStorage cleared and redirected to /login
    expect(localStorage.getItem("securevote_token")).toBeNull();
    expect(mockPush).toHaveBeenCalledWith("/login");
  });
});
