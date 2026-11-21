import { describe, it, expect } from "vitest";
import { money, relativeTime, statusBadgeTone } from "./format";

describe("money", () => {
  it("formats USD by default", () => {
    expect(money(1234.5)).toContain("1,234");
  });
  it("formats EUR amounts", () => {
    const s = money(100, "EUR");
    expect(s).toContain("100");
  });
  it("handles nullish values", () => {
    expect(money(null)).toBeDefined();
    expect(money(undefined)).toBeDefined();
  });
});

describe("statusBadgeTone", () => {
  it("maps done to success", () => expect(statusBadgeTone("done")).toBe("success"));
  it("maps todo to warning", () => expect(statusBadgeTone("todo")).toBe("warning"));
  it("maps overdue to danger", () => expect(statusBadgeTone("overdue")).toBe("danger"));
  it("maps archived to neutral", () => expect(statusBadgeTone("archived")).toBe("neutral"));
});

describe("relativeTime", () => {
  it("returns 'just now' for fresh timestamps", () => {
    expect(relativeTime(new Date().toISOString())).toBe("just now");
  });
  it("handles null", () => {
    expect(relativeTime(null)).toBe("—");
  });
});
