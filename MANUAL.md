# Manual — Parade Tim Kerja

**Simulasi parade tim kerja pekerjaan pengecoran lantai beton**

Panduan untuk mahasiswa, dosen, dan workshop Lean Construction / Project Production.

| | |
|---|---|
| Aplikasi | **Parade Tim Kerja** (Streamlit) |
| Model | Zone-flow (zona demi zona, batch handoff) |
| Default sidebar | Total zona **10** · Seed **12345** · Batch **4** · 5 tim · Tarif **100**/periode |
| Bahasa UI | Indonesia (istilah teknis: batch, WIP, takt, bay, dll. dipertahankan) |

---

## Daftar isi

1. [Tujuan pembelajaran](#1-tujuan-pembelajaran)
2. [Model zone-flow & konsep dasar](#2-model-zone-flow--konsep-dasar)
3. [Navigasi sidebar](#3-navigasi-sidebar)
4. [Tab Simulasi](#4-tab-simulasi)
5. [Biaya aktif & idle](#5-biaya-aktif--idle)
6. [Tab Perbandingan](#6-tab-perbandingan)
7. [Tab Takt plan](#7-tab-takt-plan)
8. [Line of Balance (LOB)](#8-line-of-balance-lob)
9. [Buffer / WIP](#9-buffer--wip)
10. [Utilisasi](#10-utilisasi)
11. [Little's Law & kurva WIP–TH–CT](#11-littles-law--kurva-wipthct)
12. [Kingman (VUT)](#12-kingman-vut)
13. [Inventory vs fill rate](#13-inventory-vs-fill-rate)
14. [Unduh data](#14-unduh-data)
15. [Skenario latihan](#15-skenario-latihan)
16. [Batasan model](#16-batasan-model)
17. [Literatur](#17-literatur)

---

## 1. Tujuan pembelajaran

1. Menjelaskan **parade tim kerja** (5 trade berurutan di zona).
2. Membedakan **kapasitas produksi**, **variability**, dan **batch handoff**.
3. Membedakan **durasi proyek** vs **periode aktif/idle** dan menghitung **biaya**.
4. Membaca **LOB**, **WIP**, **utilisasi**.
5. Menerapkan **Little's Law**, **Kingman**, inventory–fill rate.
6. Menyusun **takt plan** dari kasus gedung: **bay ≠ zona**, TT pelanggan, TD train.

---

## 2. Model zone-flow & konsep dasar

### 2.1 Parade (5 tim)

```text
T1 Bekisting → T2 Tulangan → T3 Cor → T4 Bongkar → T5 Finishing
```

- Satu zona dikerjakan satu tim pada satu waktu.
- Hilir mulai setelah handoff sesuai **batch**.
- Handoff default: periode berikutnya.

### 2.2 Kapasitas & variability

Kapasitas = zona/periode (Normal = 1, dll.). Variability = undi kapasitas per zona (tanpa var … sangat tinggi).

### 2.3 Batch handoff

Default **4**; **1** = one-piece flow.

### 2.4 Durasi proyek vs periode aktif

| Istilah | Arti |
|---------|------|
| **Durasi proyek** | Kalender sampai tim terakhir selesai |
| **Σ periode aktif** | Jumlah periode-tim berproduksi (bisa > durasi) |
| **Σ periode idle** | Menunggu zona di rentang mulai…selesai kerja sendiri |

---

## 3. Navigasi sidebar

| Kontrol | Default |
|---------|---------|
| Total zona | **10** (selaras TZ default takt) |
| Seed | **12345** |
| Batch handoff | **4** |
| Biaya / periode T1…T5 | **100** |
| Jumlah tim | **5** (tetap) |

---

## 3.5 Tab Statistik

Menampilkan **kunjungan** (landing + aplikasi) dan **berapa kali simulasi dijalankan** (tab Simulasi + Perbandingan). Angka agregat, tanpa data pribadi.

- Unik landing = satu perangkat/browser (localStorage).
- Sesi aplikasi = setiap buka Streamlit.
- Simulasi dihitung saat tombol **Jalankan** berhasil.

## 4. Tab Simulasi

1. Mode kapasitas: seragam atau per tim.  
2. Kapasitas + variability.  
3. **Jalankan**.

Keluaran: metrik, LOB, buffer, utilisasi, biaya, analisis (Little, Kingman, FR), unduh.

---

## 5. Biaya aktif & idle

Window per tim: **mulai → selesai kerja sendiri**.

| | |
|--|--|
| Periode aktif | produksi > 0 |
| Periode idle | produksi = 0 di window itu |
| Biaya | periode × tarif (sidebar) |
| Total proyek | jumlah 5 tim |

**Durasi proyek ≠ Σ periode aktif.**

---

## 6. Tab Perbandingan

2–5 skenario (variability / batch / kapasitas). Tombol cepat: 5× var, tanpa var vs sedang, batch 1 vs 4.

Sub-tab: LOB, Buffer, Utilisasi, **Biaya**, Little, Kingman, Inventory/FR.

---

## 7. Tab Takt plan

### 7.1 Kasus fix

Proyek gedung bertingkat **n lantai**, setiap lantai **360 m²**, ukuran **bay 3×3 m** (= 9 m²) → **40 bay / lantai**.

**Bay ≠ zona.** Zona = keputusan membagi 40 bay. Train **5 tim** (fix).

### 7.2 Input (dapat diubah)

| Input | Default | Keterangan |
|-------|---------|------------|
| Jumlah lantai n | **1** | |
| **TZ** (diskret) | **10** | Hanya **1, 5, 10, 20, 40** (bay/zona bulat) |
| Waktu tersedia **per lantai** | **15 hari** | |
| Kapasitas | **4 bay/hari/tim** | Normal |

| TZ | Bay/zona | m²/zona |
|----|----------|---------|
| 1 | 40 | 360 |
| 5 | 8 | 72 |
| **10** | **4** | **36** |
| 20 | 2 | 18 |
| 40 | 1 | 9 |

### 7.3 Rumus

```text
bay_per_zona = 40 / TZ
zona/hari    = (bay/hari) / bay_per_zona
tₑ           = 1 / (zona/hari)
TD_lantai    = (TW + TZ − 1) × tₑ     # TW = 5
```

**Contoh default:** TZ=10, 4 bay/hari → 1 zona/hari → tₑ=1  
TD = (5+10−1)×1 = **14 hari** ≤ **15** hari/lantai.

### 7.4 Takt pelanggan (LEI)

**TT = waktu tersedia ÷ permintaan**  
([lean.org](https://www.lean.org/lexicon-terms/takt-time/))

Di sini permintaan = **lantai** (bukan jumlah zona). Waktu diisi **per lantai**.

### 7.5 Keluaran

- Mapping bay → zona  
- tₑ, T₀, TD/lantai, kelayakan vs waktu per lantai  
- **Wagon chart** satu lantai  

*(Tidak ada simulasi opsional di tab ini — gunakan tab Simulasi / Perbandingan dengan Total zona = TZ.)*

---

## 8. Line of Balance (LOB)

X = periode, Y = zona kumulatif; mulai (0,0); kemiringan ≈ laju.

---

## 9. Buffer / WIP

WIP antar-tim = zona dilepas hulu, belum dikerjakan hilir.

---

## 10. Utilisasi

Produksi / kapasitas efektif; idle menurunkan utilisasi.

---

## 11. Little's Law & kurva WIP–TH–CT

WIP = TH × CT. Batas W_min, W_opt, CONWIP.

---

## 12. Kingman (VUT)

CT naik tajam saat utilisasi tinggi + variability.

---

## 13. Inventory vs fill rate

Tradeoff inventory (Y) vs fill rate (X).

---

## 14. Unduh data

Excel/CSV di Simulasi, Perbandingan, dan (rencana) Takt.

---

## 15. Skenario latihan

| # | Setup | Amati |
|---|--------|--------|
| 1 | Simulasi: 10 zona, Normal, tanpa var, batch 4 | Durasi, biaya |
| 2 | Batch 1 vs 4 | Durasi beda, biaya sering sama tanpa idle |
| 3 | 5× variability | Idle & biaya naik |
| 4 | Takt: TZ=10, 4 bay/hari, 15 hari | TD=14 ≤ 15 |
| 5 | Takt: TZ=20 vs 10 | tₑ & TD berubah |

---

## 16. Batasan model

1. Satu rantai 5 trade.  
2. Takt: lantai berurutan (bukan paralel multi-tower).  
3. Biaya = model edukasi.  
4. Simulasi diskrit vs wagon kontinu bisa sedikit beda.

---

## 17. Literatur

1. Tommelein et al. — Parade Game.  
2. Hopp & Spearman — *Factory Physics*.  
3. Little's Law; [PPI](https://projectproduction.org/journal/littles-law-in-production-systems-with-yield-loss/).  
4. Kingman VUT.  
5. [LEI — Takt Time](https://www.lean.org/lexicon-terms/takt-time/).  
6. Lean Built — Little's Takt Law TD=(TW+TZ−1)×TT.  
7. LCI — Takt planning & handoff.

---

*Manual mengikuti aplikasi terkini: default 10 zona, takt bay≠zona, TZ diskret, tanpa simulasi di tab Takt.*
