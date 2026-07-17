import { describe, expect, it } from "vitest";
import { formatMonthLabel, shiftMonth } from "@/lib/month";

describe("shiftMonth", () => {
  it("moves forward within the same year", () => {
    expect(shiftMonth("2026-07", 1)).toBe("2026-08");
  });

  it("moves backward within the same year", () => {
    expect(shiftMonth("2026-07", -1)).toBe("2026-06");
  });

  it("rolls over into the next year", () => {
    expect(shiftMonth("2026-12", 1)).toBe("2027-01");
  });

  it("rolls back into the previous year", () => {
    expect(shiftMonth("2026-01", -1)).toBe("2025-12");
  });

  it("round-trips forward then backward", () => {
    const start = "2026-07";
    expect(shiftMonth(shiftMonth(start, 1), -1)).toBe(start);
  });
});

describe("formatMonthLabel", () => {
  it("formats a month as a readable label", () => {
    expect(formatMonthLabel("2026-07")).toBe("July 2026");
  });

  it("formats January correctly", () => {
    expect(formatMonthLabel("2027-01")).toBe("January 2027");
  });
});
