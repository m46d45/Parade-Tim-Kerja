/**
 * App visual tokens — match Streamlit Parade Tim Kerja.
 *
 * Shell: .streamlit/config.toml (light theme)
 * Team chips / UI accents: parade banner in app.py
 *   --t1:#3b82f6 --t2:#f59e0b --t3:#10b981 --t4:#ef4444 --t5:#8b5cf6
 *   --bg0:#0f2744 --bg1:#1a365d (banner strip only)
 */

/** Primary UI trade colors (Streamlit banner / classroom chips). */
export const TRADE_COLORS = [
  "#3b82f6", // T1
  "#f59e0b", // T2
  "#10b981", // T3
  "#ef4444", // T4
  "#8b5cf6", // T5
  "#8c564b",
  "#e377c2",
] as const;

/** Ideal baseline on light charts */
export const IDEAL_COLOR = "#64748b";

/** Streamlit theme (config.toml) */
export const APP = {
  primary: "#1a365d",
  background: "#ffffff",
  secondaryBackground: "#f0f4f8",
  text: "#1a202c",
  muted: "#64748b",
  border: "#d0d7e2",
  banner0: "#0f2744",
  banner1: "#1a365d",
  banner2: "#234e76",
} as const;

export function tradeColor(i: number): string {
  return TRADE_COLORS[i % TRADE_COLORS.length];
}

export function shortTradeName(name: string, maxLen = 16): string {
  if (name.length <= maxLen) return name;
  return `${name.slice(0, maxLen - 1)}…`;
}
