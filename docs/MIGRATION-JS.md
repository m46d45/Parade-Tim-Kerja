# Migrasi Parade Tim Kerja → JavaScript (browser)

**Status:** Fase 0–1 dimulai (fondasi + engine zone-flow deterministik).  
**Repo:** tetap `Parade-Tim-Kerja` (satu repo).  
**Nama produk:** tetap **Parade Tim Kerja** (jangan diganti).

## Tujuan

1. Pengguna buka URL kanonis → **langsung simulasi** (bukan landing → Streamlit).
2. Simulasi berjalan **di browser** (tidak tergantung server Streamlit untuk compute).
3. Statistik Counter API (`parade-tim-kerja.app`) **tetap** — key yang sama.
4. Streamlit tetap hidup sementara sebagai jaring pengaman + redirect nanti.

## URL & hosting

| URL | Peran target |
|-----|----------------|
| Domain Vercel (sekarang landing `public/`) | App JS penuh (cutover) |
| `parade-tim-kerja.streamlit.app` | Redirect / pengumuman setelah cutover |
| Counter NS `parade-tim-kerja.app` | Jangan diubah |

## Statistik (jangan putus)

Key yang sudah dipakai landing + Streamlit:

- `landing_visits`, `landing_unique`
- `app_visits`, `app_sessions`
- `sim_runs`, `compare_runs`

App JS memakai key yang sama (`src/stats.ts`).

## Fase

| Fase | Isi | Status |
|------|-----|--------|
| **0** | Dokumen, folder `web/`, tooling Vite/TS/Vitest | ✅ |
| **1** | Port engine zone-flow + ideal baseline; golden parity vs Python | ✅ mulai (deterministik) |
| **2** | UI shell di Vercel = langsung simulasi (LoB/WIP minimal) | 🚧 LoB detail + warna Streamlit |
| **3** | Parity tab: Perbandingan, biaya, Little/Kingman, Takt, Buffer | 🔜 |
| **4** | Cutover Vercel + redirect Streamlit | 🔜 |
| **5** | PWA/offline (opsional) | 🔜 |

## Layout repo

```text
web/                 # App JS (Vite + TypeScript)
  src/core/          # Engine (port dari parade_of_trades_core.py)
  src/stats.ts       # Counter API (NS sama)
  src/ui/            # UI browser
  fixtures/          # Golden JSON dari Python
  tests/             # Vitest parity
scripts/
  export_golden_fixtures.py
docs/MIGRATION-JS.md # Dokumen ini
app.py               # Streamlit (tetap sampai cutover)
public/              # Landing statis (tetap sampai Fase 2/4)
```

## Pengembangan lokal

```bash
cd web
npm install
npm test          # parity vs fixtures
npm run dev       # UI shell
```

Regenerate golden (Python oracle):

```bash
python3 scripts/export_golden_fixtures.py
```

## Palet (sumber kebenaran)

Ikuti **Streamlit app**, bukan landing gelap:

| Token | Nilai | Sumber |
|-------|-------|--------|
| Background | `#ffffff` / `#f0f4f8` | `.streamlit/config.toml` |
| Primary / teks | `#1a365d` / `#1a202c` | config.toml |
| Header navy | `#0f2744` → `#1a365d` → `#234e76` | banner `app.py` |
| Tim T1–T5 | `#3b82f6` `#f59e0b` `#10b981` `#ef4444` `#8b5cf6` | banner `app.py` |

Lihat `web/src/theme.ts`.

- Python = sumber kebenaran selama migrasi.
- Fase 1 fokus **zone_flow + deterministic** (tanpa ketergantungan RNG Python).
- Variability ber-seed: belakangan (RNG portabel bersama) atau bandingkan distribusi, bukan bit-exact dulu.

## Cutover Vercel (nanti)

1. `web` build → output ke folder yang di-serve Vercel.
2. Update `vercel.json` `outputDirectory` / build command.
3. Hapus CTA “Buka simulasi Streamlit” dari jalur utama.
4. Streamlit: halaman redirect ke domain Vercel.
