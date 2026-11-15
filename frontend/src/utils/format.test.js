import { describe, expect, it } from "vitest";
import { formatDate, formatFileSize, formatMoney, formatStatus } from "./format.js";
import { buildQuery } from "../api/client.js";

describe("formatMoney", () => {
  it("formats API money strings as US dollars", () => {
    expect(formatMoney("150.00")).toBe("$150.00");
    expect(formatMoney("1234.5")).toBe("$1,234.50");
  });

  it("shows a dash for missing values", () => {
    expect(formatMoney(null)).toBe("—");
    expect(formatMoney("")).toBe("—");
    expect(formatMoney("abc")).toBe("—");
  });
});

describe("formatDate", () => {
  it("keeps the calendar day regardless of timezone", () => {
    expect(formatDate("2026-01-15")).toBe("Jan 15, 2026");
    expect(formatDate("2026-03-01")).toBe("Mar 1, 2026");
  });

  it("shows a dash for missing values", () => {
    expect(formatDate(null)).toBe("—");
  });
});

describe("formatStatus", () => {
  it("turns API status codes into labels", () => {
    expect(formatStatus("in_review")).toBe("In review");
    expect(formatStatus("paid")).toBe("Paid");
  });
});

describe("formatFileSize", () => {
  it("picks a sensible unit", () => {
    expect(formatFileSize(512)).toBe("512 B");
    expect(formatFileSize(2048)).toBe("2.0 KB");
    expect(formatFileSize(3 * 1024 * 1024)).toBe("3.0 MB");
  });
});

describe("buildQuery", () => {
  it("skips empty values and encodes the rest", () => {
    expect(buildQuery({ q: "o'brien & co", status: "", page: 2, plan: null })).toBe(
      "?q=o%27brien+%26+co&page=2"
    );
    expect(buildQuery({})).toBe("");
  });
});
