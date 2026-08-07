# Parade Tim Kerja

Simulasi **Lean Construction** interaktif untuk belajar dampak *variability* dan ketergantungan sekuensial antar trade terhadap durasi, throughput, WIP, dan waste.

Berdasarkan karya **Iris D. Tommelein** dkk. (UC Berkeley), dengan konteks **floor cycle beton Indonesia** (5 trade).

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://parade-tim-kerja.streamlit.app/)
[![GitHub](https://img.shields.io/badge/GitHub-Parade--Tim--Kerja-181717?logo=github)](https://github.com/m46d45/Parade-Tim-Kerja)
<!-- Setelah deploy: ganti URL badge di atas dengan link app Anda, contoh:
https://YOUR-APP-NAME.streamlit.app
-->

## Coba aplikasinya

> Setelah deploy ke Streamlit Community Cloud, taruh link publik di sini:
>
> **🌐 Simulasi (Streamlit):** https://parade-tim-kerja.streamlit.app/  
> **🏠 Landing (Vercel):** hubungkan repo ini ke Vercel → menyajikan `index.html`  
> **📖 Manual:** tab **Manual** di dalam app

Mahasiswa **tidak perlu menginstal Python** — cukup buka link di browser.

## Untuk siapa

- Mahasiswa teknik sipil / manajemen konstruksi  
- Peserta workshop Lean Construction  
- Dosen yang butuh demo interaktif di kelas  

## Fitur (zone-flow classroom)

| Tab | Fungsi |
|-----|--------|
| **Simulasi** | Satu skenario zone-flow: kecepatan + variability **per zona**, LOB / WIP / utilization |
| **Perbandingan** | Bandingkan **2–5** skenario (mis. kelima level variability) |
| **Manual** | Panduan belajar + tentang model |

**Batch handoff** default **4 zona** (sidebar; 1 = one-piece flow).  
Default demo: **20 zona**, 5 trade floor cycle Indonesia.

## Menjalankan di komputer sendiri (opsional, untuk pengembang)

```bash
git clone https://github.com/m46d45/Parade-Tim-Kerja.git
cd Parade-Tim-Kerja
python -m pip install -r requirements.txt
streamlit run app.py
```

Buka http://localhost:8501

## Struktur repo

```text
parade-of-trades/
├── app.py                         # Streamlit UI (entry point cloud)
├── parade_of_trades_core.py       # Engine simulasi
├── parade_of_trades_plots.py      # Visualisasi
├── parade_of_trades_analysis.py   # Replikasi & export
├── MANUAL.md                      # Manual belajar mahasiswa
├── requirements.txt
├── assets/                        # Banner & logo
└── test_*.py                      # Unit tests
```

## Deploy (Streamlit Community Cloud)

1. Push repo ini ke GitHub (public disarankan untuk cloud gratis).  
2. Buka [https://share.streamlit.io](https://share.streamlit.io) → login dengan GitHub.  
3. **New app** → pilih repo → Main file: `app.py` → Deploy.  
4. Tunggu build selesai; salin URL `*.streamlit.app` ke bagian atas README ini.

Detail langkah: lihat file [DEPLOY.md](DEPLOY.md).

## Referensi

- Tommelein, Riley & Howell (1999). *Parade Game…* ASCE J. Constr. Eng. Manage.  
- Choo & Tommelein (1999). Technical Report 99-1, UC Berkeley.  
- Tommelein (2020). *Takting the Parade Tim Kerja.* IGLC28.  
- [P2SL — Parade Tim Kerja](https://p2sl.berkeley.edu/parade-of-trades-game-2/)

## Lisensi & kredit

Konsep game: Tommelein / Riley / Howell / Choo (UC Berkeley P2SL).  
Implementasi web ini: proyek edukasi independen.  
Untuk pembelajaran dan workshop non-komersial. Cantumkan sitasi paper di atas saat dipakai di tugas/publikasi.
