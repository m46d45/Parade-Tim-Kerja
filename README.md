# Parade Tim Kerja

Simulasi **Lean Construction** interaktif untuk belajar dampak *variability* dan ketergantungan sekuensial antar trade terhadap durasi, throughput, WIP, dan waste.

Berdasarkan karya **Iris D. Tommelein** dkk. (UC Berkeley), dengan konteks **floor cycle beton Indonesia** (5 trade).

[![GitHub](https://img.shields.io/badge/GitHub-Parade--Tim--Kerja-181717?logo=github)](https://github.com/m46d45/Parade-Tim-Kerja)
[![Vercel](https://img.shields.io/badge/Vercel-live-black?logo=vercel)](https://parade-tim-kerja.vercel.app/)

## Coba aplikasinya

> **🌐 Simulasi (browser):** https://parade-tim-kerja.vercel.app/  
> **🎬 Animasi kelas:** https://parade-tim-kerja.vercel.app/kelas/  
> **📖 Manual:** tab **Manual** di dalam simulasi  

Mahasiswa **tidak perlu menginstal apa pun** — cukup buka link di browser.

## Untuk siapa

- Mahasiswa teknik sipil / manajemen konstruksi  
- Peserta workshop Lean Construction  
- Dosen yang butuh demo interaktif di kelas  

## Fitur (zone-flow classroom)

| Mode | Fungsi |
|------|--------|
| **Simulasi** | Satu skenario zone-flow: kapasitas + variability, Location-based Schedule / WIP / utilization |
| **Perbandingan** | Bandingkan **2–5** skenario |
| **Takt plan** | Little's Takt Law + wagon chart |
| **Buffer** | Buffer waktu–inventory (Iris) |
| **Statistik** | Counter kunjungan / sesi |
| **Manual** | Panduan belajar |
| **/kelas** | Animasi manufaktur vs konstruksi (Produksi / WIP / Inventory / Waste) |

**Batch handoff** default **4 zona** (1 = one-piece flow).  
Default demo: **20 zona**, 5 trade floor cycle Indonesia.

## Menjalankan di komputer sendiri (pengembang)

### App JS (kanonis)

```bash
git clone https://github.com/m46d45/Parade-Tim-Kerja.git
cd Parade-Tim-Kerja/web
npm install
npm run dev
```

Buka http://localhost:5173

### Streamlit (legacy / jaring pengaman)

```bash
cd Parade-Tim-Kerja
python -m pip install -r requirements.txt
streamlit run app.py
```

Cloud Streamlit mengarahkan ke Vercel. UI lama: tambahkan `?legacy=1` pada URL Streamlit.

## Struktur repo

```text
Parade-Tim-Kerja/
├── web/                 # App JS (Vite + TypeScript) — kanonis di Vercel
├── public/kelas/        # Animasi kelas (disalin ke web/public)
├── app.py               # Streamlit redirect (+ ?legacy=1)
├── parade_of_trades_*.py
├── docs/MIGRATION-JS.md
└── vercel.json          # build web → web/dist
```

## Deploy (Vercel)

1. Hubungkan repo ke Vercel.  
2. `vercel.json` memakai `installCommand` / `buildCommand` di folder `web`, output `web/dist`.  
3. Domain: https://parade-tim-kerja.vercel.app/

Detail migrasi: [docs/MIGRATION-JS.md](docs/MIGRATION-JS.md).

## Referensi

- Tommelein, Riley & Howell (1999). *Parade Game…* ASCE J. Constr. Eng. Manage.  
- Choo & Tommelein (1999). Technical Report 99-1, UC Berkeley.  
- Tommelein (2020). *Takting the Parade Tim Kerja.* IGLC28.  
- [P2SL — Parade Tim Kerja](https://p2sl.berkeley.edu/parade-of-trades-game-2/)

## Lisensi & kredit

Lihat repo GitHub untuk lisensi dan kredit penuh.
