/**
 * Usage counters — same Counter API namespace/keys as Streamlit + landing.
 * NS: parade-tim-kerja.app
 */

export const STATS_NS = "parade-tim-kerja.app";
export const API = "https://counterapi.com/api";

export const KEYS = {
  landingVisits: "landing_visits",
  landingUnique: "landing_unique",
  appVisits: "app_visits",
  appSessions: "app_sessions",
  simRuns: "sim_runs",
  compareRuns: "compare_runs",
} as const;

async function getCounter(key: string, readOnly: boolean): Promise<number | null> {
  const q = readOnly ? "?readOnly=true" : "";
  const url = `${API}/${STATS_NS}/view/${encodeURIComponent(key)}${q}`;
  try {
    const res = await fetch(url, {
      headers: { Accept: "application/json" },
    });
    if (!res.ok) return null;
    const data = (await res.json()) as { value?: number };
    return typeof data.value === "number" ? data.value : null;
  } catch {
    return null;
  }
}

export async function bump(key: string): Promise<number | null> {
  return getCounter(key, false);
}

export async function read(key: string): Promise<number | null> {
  return getCounter(key, true);
}

export async function recordAppSession(): Promise<void> {
  await bump(KEYS.appVisits);
  await bump(KEYS.appSessions);
}

export async function recordSimRun(): Promise<void> {
  await bump(KEYS.simRuns);
}

export async function recordCompareRun(): Promise<void> {
  await bump(KEYS.compareRuns);
}

export async function readDashboard(): Promise<Record<string, number>> {
  const entries = await Promise.all(
    Object.values(KEYS).map(async (k) => [k, (await read(k)) ?? 0] as const),
  );
  return Object.fromEntries(entries);
}
