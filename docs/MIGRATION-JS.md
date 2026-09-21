# Migrasi Parade Tim Kerja → JavaScript (browser)

**Status:** Cutover Vercel **selesai** — URL kanonis = app JS.  
**Repo:** tetap `Parade-Tim-Kerja` (satu repo).  
**Nama produk:** tetap **Parade Tim Kerja** (jangan diganti).

## Tujuan

1. Pengguna buka URL kanonis → **langsung simulasi** (bukan landing → Streamlit). ✅  
2. Simulasi berjalan **di browser** (tidak tergantung server Streamlit untuk compute). ✅  
3. Statistik Counter API (`parade-tim-kerja.app`) **tetap** — key yang sama. ✅  
4. Streamlit tetap hidup sementara sebagai redirect + jaring (`?legacy=1`). ✅  

## URL & hosting

| URL | Peran |
|-----|--------|
| https://parade-tim-kerja.vercel.app/ | **Kanonis** — app JS (`web/dist`) |
| https://parade-tim-kerja.vercel.app/kelas/ | Animasi kelas |
| https://parade-tim-kerja.vercel.app/landing/ | Halaman tentang (ex-landing) |
| `parade-tim-kerja.streamlit.app` | Redirect → Vercel (`?legacy=1` = UI Streamlit lama) |
| Counter NS `parade-tim-kerja.app` | Jangan diubah |

## Statistik (jangan putus)

Key yang sudah dipakai landing + Streamlit + app JS:

- `landing_visits`, `landing_unique`
- `app_visits`, `app_sessions`
- `sim_runs`, `compare_runs`

App JS memakai key yang sama (`web/src/stats.ts`).

## Fase

| Fase | Isi | Status |
|------|-----|--------|
| **0** | Dokumen, folder `web/`, tooling Vite/TS/Vitest | ✅ |
| **1** | Port engine zone-flow + ideal baseline; golden parity vs Python | ✅ |
| **2** | UI shell: LoB detail, Buffer/WIP, seed + variability | ✅ |
| **3** | Parity tab Simulasi + **Perbandingan** multi-skenario | ✅ |
| **4** | Takt / Buffer waktu–inventory / Statistik / Manual | ✅ |
| **4b** | Cutover Vercel + redirect Streamlit | ✅ |
| **5** | PWA/offline (opsional) | 🔜 |

Mode top-level JS:

1. **Simulasi** — LoB, Buffer WIP, Utilisasi, Biaya, Little, Kingman, Inventory/FR  
2. **Perbandingan** — multi-skenario overlay  
3. **Takt plan** — Little's Takt Law + wagon chart (bay≠zona)  
4. **Buffer** — waktu–inventory Iris  
5. **Statistik** — Counter API  
6. **Manual** — `MANUAL.md` di browser  

## Layout repo

```text
web/                 # App JS (Vite + TypeScript) — output Vercel
  src/core/          # Engine
  src/stats.ts       # Counter API (NS sama)
  src/ui/            # UI browser
  public/kelas →     # symlink ke ../../public/kelas
  public/landing/    # halaman tentang
app.py               # Streamlit redirect (+ ?legacy=1)
vercel.json          # build web → web/dist
docs/MIGRATION-JS.md
```

## Pengembangan lokal

```bash
cd web
npm install
npm test
npm run dev
```

## Cutover Vercel (sudah)

1. ✅ `vercel.json`: `installCommand` / `buildCommand` di `web`, `outputDirectory` `web/dist`  
2. ✅ CTA utama → `/` (app JS), bukan Streamlit  
3. ✅ Streamlit: redirect ke Vercel; `?legacy=1` untuk UI lama  
