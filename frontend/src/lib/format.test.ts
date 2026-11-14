import { describe, expect, it } from "vitest";
import { categoryLabel, clamp, formatNumber, formatRange, percent, titleCase } from "@/lib/format";
import { validateEmail, validateLogin, validateRegister } from "@/lib/validation";
import { navItems } from "@/lib/nav";

describe("display formatting", () => {
  it("formats reference intervals without inventing bounds", () => {
    expect(formatRange(7, 35, "U/L")).toBe("7–35 U/L");
    expect(formatRange(null, 30, "mg/g")).toBe("≤ 30 mg/g");
    expect(formatRange(60, null, "mL/min")).toBe("≥ 60 mL/min");
    expect(formatRange(null, null)).toBe("No interval supplied");
  });

  it("formats numbers and categories", () => {
    expect(formatNumber(97.2983, 2)).toBe("97.3");
    expect(categoryLabel("liver")).toBe("Liver");
    expect(titleCase("sleep_duration")).toBe("Sleep Duration");
    expect(percent(1, 4)).toBe(25);
    expect(clamp(120, 0, 100)).toBe(100);
  });
});

describe("form validation", () => {
  it("rejects malformed emails", () => {
    expect(validateEmail("not-an-email")).toBeTruthy();
    expect(validateEmail("avery@example.com")).toBeNull();
  });

  it("requires a valid login", () => {
    expect(validateLogin({ email: "", password: "" })).toEqual({
      email: "Email is required.",
      password: "Password is required.",
    });
  });

  it("enforces password strength and explicit terms", () => {
    const errors = validateRegister({
      name: "A",
      email: "bad",
      password: "short",
      accept_terms: false,
    });
    expect(errors.name).toBeTruthy();
    expect(errors.email).toBeTruthy();
    expect(errors.password).toBeTruthy();
    expect(errors.accept_terms).toBeTruthy();
    expect(
      validateRegister({
        name: "Avery Chen",
        email: "avery@example.com",
        password: "StrongPass123",
        accept_terms: true,
      }),
    ).toEqual({});
  });
});

describe("navigation contract", () => {
  it("contains all twelve product modules in order", () => {
    expect(navItems.map((item) => item.label)).toEqual([
      "Overview",
      "My Biology",
      "Digital Twin",
      "What If?",
      "Genetics",
      "Biomarkers",
      "Medications",
      "Wearables",
      "Insights",
      "POLIS AI",
      "Privacy & Data",
      "Settings",
    ]);
    expect(navItems.every((item) => item.href.startsWith("/"))).toBe(true);
  });
});
