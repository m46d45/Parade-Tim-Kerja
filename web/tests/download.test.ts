import { describe, expect, it } from "vitest";
import {
  classroomConfig,
  DEFAULT_TRADE_NAMES,
  runParade,
} from "../src/core";
import {
  compareSummaryRows,
  resultHistoryRows,
  resultSummaryRows,
  resultWorkbookCsv,
  rowsToCsv,
} from "../src/ui/download";
import { shortTradeName } from "../src/theme";

describe("short trade names", () => {
  it("uses Bekisting…Finishing as defaults", () => {
    expect([...DEFAULT_TRADE_NAMES]).toEqual([
      "Bekisting",
      "Tulangan",
      "Cor",
      "Bongkar",
      "Finishing",
    ]);
  });

  it("aliases legacy long names", () => {
    expect(shortTradeName("Pemasangan Bekisting")).toBe("Bekisting");
    expect(shortTradeName("Pengecoran Beton")).toBe("Cor");
    expect(shortTradeName("Pembongkaran Bekisting")).toBe("Bongkar");
  });
});

describe("download CSV helpers", () => {
  it("escapes CSV cells", () => {
    expect(rowsToCsv([["a", 'b,c', 'say "hi"']])).toBe(
      'a,"b,c","say ""hi"""',
    );
  });

  it("builds summary + history + workbook for a run", () => {
    const r = runParade(
      classroomConfig({
        totalUnits: 6,
        batchSize: 2,
        baseSpeed: 1,
        seed: 1,
        deterministic: true,
      }),
    );
    const summary = resultSummaryRows(r, [100, 100, 100, 100, 100]);
    expect(summary[0][1]).toBe("Nama");
    expect(summary[1][1]).toBe("Bekisting");
    expect(summary[5][1]).toBe("Finishing");

    const hist = resultHistoryRows(r);
    expect(hist[0][0]).toBe("Periode");
    expect(hist.length).toBeGreaterThan(1);

    const wb = resultWorkbookCsv(r, [100, 100, 100, 100, 100]);
    expect(wb).toContain("### RINGKASAN");
    expect(wb).toContain("### RIWAYAT");
    expect(wb).toContain("Bekisting");

    const cmp = compareSummaryRows(
      [
        { name: "A", result: r },
        { name: "B", result: r },
      ],
      [100, 100, 100, 100, 100],
      [
        { variability: "none", batch: 2 },
        { variability: "medium", batch: 4 },
      ],
    );
    expect(cmp).toHaveLength(3);
    expect(cmp[1][0]).toBe("A");
  });
});
