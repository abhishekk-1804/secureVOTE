import { describe, it, expect } from "vitest";
import { ApiError, formatApiError } from "@/lib/format-error";

describe("formatApiError", () => {
  it("formats string detail correctly", () => {
    const err = new ApiError(400, "Bad Request", { detail: "Invalid candidate selection" });
    const formatted = formatApiError(err);
    expect(formatted).toBe("Invalid candidate selection");
    expect(formatted).not.toContain("[object Object]");
  });

  it("formats array of string details", () => {
    const err = new ApiError(422, "Unprocessable", { detail: ["Missing field A", "Invalid field B"] });
    const formatted = formatApiError(err);
    expect(formatted).toBe("Missing field A. Invalid field B");
    expect(formatted).not.toContain("[object Object]");
  });

  it("formats array of object validation details (FastAPI style)", () => {
    const err = new ApiError(422, "Validation Error", {
      detail: [
        { loc: ["body", "dob"], msg: "Date of birth required", type: "value_error" },
        { loc: ["body", "name"], msg: "Name too short", type: "value_error" },
      ],
    });
    const formatted = formatApiError(err);
    expect(formatted).toBe("Date of birth required. Name too short");
    expect(formatted).not.toContain("[object Object]");
  });

  it("formats dictionary detail with message field", () => {
    const err = new ApiError(403, "Forbidden", {
      detail: { message: "Access denied to polling unit" },
    });
    const formatted = formatApiError(err);
    expect(formatted).toBe("Access denied to polling unit");
    expect(formatted).not.toContain("[object Object]");
  });

  it("formats dictionary detail with msg field", () => {
    const err = new ApiError(400, "Bad Request", {
      detail: { msg: "Device already registered" },
    });
    const formatted = formatApiError(err);
    expect(formatted).toBe("Device already registered");
    expect(formatted).not.toContain("[object Object]");
  });

  it("safely serializes arbitrary dictionary detail without producing [object Object]", () => {
    const err = new ApiError(409, "Conflict", {
      detail: { code: "DEVICE_REVOKED", device_id: "EVM-001", active: false },
    });
    const formatted = formatApiError(err);
    expect(formatted).toContain("DEVICE_REVOKED");
    expect(formatted).toContain("EVM-001");
    expect(formatted).not.toContain("[object Object]");
  });

  it("formats fallback to error.data.message when detail is absent", () => {
    const err = new ApiError(500, "Internal Server Error", { message: "Database connection failed" });
    const formatted = formatApiError(err);
    expect(formatted).toBe("Database connection failed");
    expect(formatted).not.toContain("[object Object]");
  });

  it("formats standard JavaScript Error", () => {
    const err = new Error("Network timeout while contacting backend");
    const formatted = formatApiError(err);
    expect(formatted).toBe("Network timeout while contacting backend");
    expect(formatted).not.toContain("[object Object]");
  });

  it("formats plain string error", () => {
    const formatted = formatApiError("Custom string error occurred");
    expect(formatted).toBe("Custom string error occurred");
    expect(formatted).not.toContain("[object Object]");
  });

  it("formats plain object without producing [object Object]", () => {
    const formatted = formatApiError({ custom_code: 503, reason: "Service unavailable" });
    expect(formatted).toContain("Service unavailable");
    expect(formatted).not.toContain("[object Object]");
  });

  it("handles null and undefined gracefully", () => {
    expect(formatApiError(null)).toBe("An unexpected error occurred. Please try again.");
    expect(formatApiError(undefined)).toBe("An unexpected error occurred. Please try again.");
  });
});
