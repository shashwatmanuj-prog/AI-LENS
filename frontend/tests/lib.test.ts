import { describe, expect, it } from "vitest";
import { dateParts, daysUntil, nextDeadline, urgency } from "@/lib/dates";
import { MESSAGES, translate } from "@/lib/i18n";

describe("dates", () => {
  const today = new Date(2026, 9, 9); // 9 Oct 2026, local time

  it("counts whole calendar days", () => {
    expect(daysUntil("2026-10-15", today)).toBe(6);
    expect(daysUntil("2026-10-09", today)).toBe(0);
    expect(daysUntil("2026-10-01", today)).toBe(-8);
    expect(daysUntil("15-10-2026", today)).toBeNull();
  });

  it("classifies urgency", () => {
    expect(urgency(-1)).toBe("past");
    expect(urgency(0)).toBe("today");
    expect(urgency(3)).toBe("soon");
    expect(urgency(30)).toBe("later");
    expect(urgency(null)).toBe("later");
  });

  it("picks the next upcoming deadline", () => {
    const items = [{ date: "2026-10-01" }, { date: "2026-11-01" }, { date: "2026-10-20" }, { date: null }];
    expect(nextDeadline(items, today)?.date).toBe("2026-10-20");
    expect(nextDeadline([{ date: "2026-01-01" }, { date: "2026-02-01" }], today)?.date).toBe("2026-02-01");
  });

  it("formats parts", () => {
    expect(dateParts("2026-10-15", "en")).toMatchObject({ day: "15", year: "2026" });
  });
});

describe("i18n", () => {
  it("Hindi and Kannada define every English key", () => {
    const keys = Object.keys(MESSAGES.en).sort();
    expect(Object.keys(MESSAGES.hi).sort()).toEqual(keys);
    expect(Object.keys(MESSAGES.kn).sort()).toEqual(keys);
  });

  it("keeps placeholders in every language", () => {
    for (const [key, text] of Object.entries(MESSAGES.en)) {
      const vars = text.match(/\{\w+\}/g) ?? [];
      for (const lang of ["hi", "kn"] as const) {
        for (const v of vars) expect(MESSAGES[lang][key as keyof typeof MESSAGES.en], `${lang}.${key}`).toContain(v);
      }
    }
  });

  it("interpolates", () => {
    expect(translate("en", "days_left", { n: 3 })).toBe("3 days left");
    expect(translate("kn", "days_left", { n: 3 })).toBe("3 ದಿನ ಬಾಕಿ");
  });
});
