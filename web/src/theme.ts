/**
 * Visual tokens aligned with parade_of_trades_plots.py (Streamlit charts).
 */

/** Matplotlib trade palette used in Streamlit LoB. */
export const TRADE_COLORS = [
  "#1f77b4", // T1 blue
  "#ff7f0e", // T2 orange
  "#2ca02c", // T3 green
  "#d62728", // T4 red
  "#9467bd", // T5 purple
  "#8c564b",
  "#e377c2",
] as const;

export const IDEAL_COLOR = "#555555";

export const MARKERS = ["o", "s", "^", "D", "v"] as const;

export function tradeColor(i: number): string {
  return TRADE_COLORS[i % TRADE_COLORS.length];
}

export function shortTradeName(name: string, maxLen = 16): string {
  if (name.length <= maxLen) return name;
  return `${name.slice(0, maxLen - 1)}…`;
}
