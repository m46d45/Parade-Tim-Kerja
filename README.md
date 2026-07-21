# Parade of Trades

Simulasi **Lean Construction** interaktif untuk belajar dampak *variability* dan ketergantungan sekuensial antar trade terhadap durasi, throughput, WIP, dan waste.

Berdasarkan karya **Iris D. Tommelein** dkk. (UC Berkeley), dengan konteks **floor cycle beton Indonesia** (5 trade).

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/)
<!-- Setelah deploy: ganti URL badge di atas dengan link app Anda, contoh:
https://YOUR-APP-NAME.streamlit.app
-->

## Coba aplikasinya

> Setelah deploy ke Streamlit Community Cloud, taruh link publik di sini:
>
> **🌐 App:** *https://xxxx.streamlit.app*  
> **📖 Manual belajar:** buka tab **Manual** di dalam app

Mahasiswa **tidak perlu menginstal Python** — cukup buka link di browser.

## Untuk siapa

- Mahasiswa teknik sipil / manajemen konstruksi  
- Peserta workshop Lean Construction  
- Dosen yang butuh demo interaktif di kelas  

## Fitur

| Tab | Fungsi |
|-----|--------|
| Single run | Satu skenario, Run / Step, grafik LOB · WIP · utilization |
| Compare 2 | Bandingkan dua skenario berdampingan |
| Preset sweep | Semua tingkat variability sekaligus |
| Takt 2020 | Capacity buffer (Tommelein 2020) + multi-replikasi |
| Replications | Statistik mean / std / min–max |
| Manual | Panduan belajar mahasiswa (Bahasa Indonesia) |

## Trade default (floor cycle)

1. Pemasangan Bekisting  
2. Pemasangan Tulangan  
3. Pengecoran Beton  
4. Pembongkaran Bekisting  
5. Finishing Lantai  

Default: **100 zona**, mean capacity **5** unit/periode.

## Menjalankan di komputer sendiri (opsional, untuk pengembang)

```bash
git clone https://github.com/USERNAME/parade-of-trades.git
cd parade-of-trades
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
- Tommelein (2020). *Takting the Parade of Trades.* IGLC28.  
- [P2SL — Parade of Trades](https://p2sl.berkeley.edu/parade-of-trades-game-2/)

## Lisensi & kredit

Konsep game: Tommelein / Riley / Howell / Choo (UC Berkeley P2SL).  
Implementasi web ini: proyek edukasi independen.  
Untuk pembelajaran dan workshop non-komersial. Cantumkan sitasi paper di atas saat dipakai di tugas/publikasi.
