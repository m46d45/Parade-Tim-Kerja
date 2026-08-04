# Manual — Parade Tim Kerja

**Simulasi parade tim kerja pekerjaan pengecoran lantai beton**

Panduan lengkap untuk mahasiswa, dosen, dan peserta workshop Lean Construction / Project Production.

| | |
|---|---|
| Aplikasi | **Parade Tim Kerja** (Streamlit) |
| Model | Zone-flow (zona demi zona, batch handoff) |
| Default | Total zona **40** · Seed **12345** · Batch **4** · 5 tim (tetap) · Tarif **100**/periode |
| Bahasa UI | Indonesia (istilah teknis: batch, WIP, takt, CONWIP, dll. dipertahankan) |

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
14. [Unduh data (Excel/CSV)](#14-unduh-data-excelcsv)
15. [Skenario latihan kelas](#15-skenario-latihan-kelas)
16. [Batasan model](#16-batasan-model)
17. [Literatur](#17-literatur)

---

## 1. Tujuan pembelajaran

Setelah memakai aplikasi ini, peserta diharapkan mampu:

1. Menjelaskan **parade tim kerja** pada floor cycle beton (5 trade berurutan di zona).
2. Membedakan **kapasitas produksi** (zona/periode) dan **variability** (perubahan kapasitas per zona).
3. Memahami **batch handoff** vs **one-piece flow** dan dampaknya ke **durasi proyek**, WIP, utilisasi, dan **biaya**.
4. Membedakan **durasi proyek** (kalender) vs **periode aktif/idle** (volume kerja kru).
5. Menghitung **biaya aktif** dan **biaya idle** dari tarif per periode.
6. Membaca **Line of Balance (LOB)** yang mulai dari (0,0).
7. Menerapkan **Little's Law** (WIP = TH × CT) serta **W_min**, **W_opt**, **CONWIP**.
8. Memakai intuisi **Kingman / VUT** dan tradeoff **inventory vs fill rate**.
9. Menyusun **takt plan** dengan **Little's Takt Law**: TD = (TW + TZ − 1) × TT.

---

## 2. Model zone-flow & konsep dasar

### 2.1 Parade floor cycle (5 tim)

```text
T1 Bekisting → T2 Tulangan → T3 Cor → T4 Bongkar bekisting → T5 Finishing
         zona 1, 2, 3, … N
```

- Satu zona hanya dikerjakan **satu tim** pada satu waktu.
- Tim hilir baru boleh masuk setelah zona **dilepas** sesuai **ukuran batch handoff**.
- Handoff default: periode berikutnya (zone-flow, bukan instant).

### 2.2 Kapasitas produksi

| Pilihan | Arti (zona / periode) |
|---------|------------------------|
| Sangat rendah | 1/3 |
| Rendah | 0,5 (dua periode → satu zona) |
| **Normal** (default) | **1** (satu zona / satu periode) |
| Tinggi | 2 |
| Sangat tinggi | 3 |

### 2.3 Variability

| Level | Intuisi |
|-------|---------|
| Tanpa variability | Kapasitas tetap tiap zona |
| Rendah / Sedang / Tinggi / Sangat tinggi | Kapasitas diundi per zona (± semakin lebar) |

Tanpa var + Normal → LOB lurus. Variability → patahan, idle, durasi & biaya naik.

### 2.4 Batch handoff

| Batch | Arti |
|-------|------|
| **4** (default) | Kumpulkan 4 zona dulu baru dilepas hilir |
| 1 | One-piece flow (zona per zona) |
| 2, 3, 5 | Antara batch dan OPF |

Batch besar → train “lebih jarang” handoff, **durasi proyek** biasanya lebih panjang, WIP antar-tim berubah.

### 2.5 Durasi proyek vs periode aktif (penting)

| Istilah | Arti | Contoh (tanpa var, 40 zona, 5 tim, Normal) |
|---------|------|-----------------------------------------------|
| **Durasi proyek** | Kalender sampai **tim terakhir** selesai | Batch 1 → **44** p; batch 4 → **56** p |
| **Periode aktif (satu tim)** | Tim itu **bekerja** (produksi > 0) | ≈ **40** per tim |
| **Σ periode aktif** | Jumlah periode-kerja **semua** tim | ≈ **200** (= 5 × 40) |
| **Periode idle (satu tim)** | Sudah mulai, belum selesai kerja sendiri, **tidak** berproduksi | **0** jika aliran mulus tanpa var |
| **Waktu di lapangan (tim)** | aktif + idle = selesai − mulai + 1 | |

**Durasi proyek ≠ Σ periode aktif.**  
Durasi = panjang kalender. Σ aktif = volume kru; lima tim bisa kerja **tumpang-tindih**, jadi Σ aktif bisa **lebih besar** dari durasi.

### 2.6 Rumus ringkas (intuisi)

- Ideal OPF, TT = 1, TW = 5, TZ = 40 → **TD ≈ (TW + TZ − 1) × TT = 44** (lihat tab Takt plan).
- Little: **WIP = TH × CT**.
- Biaya: lihat [§5](#5-biaya-aktif--idle).

---

## 3. Navigasi sidebar

| Kontrol | Default | Fungsi |
|---------|---------|--------|
| Total zona | **40** | Lingkup unit kerja (TZ) |
| Kunci seed / Seed | **12345** | Reproduktibilitas undi variability |
| Ukuran batch handoff | **4** | Kebijakan serah-terima zona |
| **Biaya per periode T1…T5** | **100** masing-masing | Tarif kru per periode (aktif & idle) |

Jumlah tim **tetap 5** (parade floor cycle).

---

## 4. Tab Simulasi

### 4.1 Pengaturan

1. **Mode kapasitas**: seragam semua tim **atau** per tim berbeda.  
2. Pilih **kapasitas** + **variability**.  
3. Tekan **Jalankan**.

Tidak ada tombol demo terpisah; fokus pada pengaturan trade.

### 4.2 Keluaran utama

| Blok | Isi |
|------|-----|
| Metrik | Durasi proyek, TH, Σ periode aktif, Σ periode idle, biaya idle, total biaya |
| LOB | Line of Balance semua tim (mulai 0) |
| Buffer / WIP | Profil antrian antar-tim |
| Utilisasi | Produksi vs idle kapasitas |
| Metrik per tim | Mulai, selesai, waktu lapangan, periode aktif/idle, biaya |
| Biaya | Ringkasan aktif / idle / total + tabel |
| Analisis | Sub-tab: LOB, Buffer, Utilisasi, Little's Law, Kingman, Inventory/FR |
| Unduh | Excel / CSV |

### 4.3 Cara baca cepat

1. Lihat **durasi proyek** (kalender).  
2. Bandingkan **Σ periode aktif** vs durasi — jangan disamakan.  
3. Jika **Σ idle > 0** → ada menunggu zona (variability / batch).  
4. LOB: kemiringan = laju; jarak antar garis ≈ buffer.  
5. Biaya naik terutama jika **idle** atau **waktu lapangan** memanjang.

---

## 5. Biaya aktif & idle

### 5.1 Definisi (samakan persepsi)

Window **per tim**: dari **mulai kerja** sampai **selesai kerja sendiri** (bukan sampai akhir proyek).

| Konsep | Rumus / arti |
|--------|----------------|
| **Periode aktif** | Periode dengan produksi > 0 |
| **Periode idle** | Periode produksi = 0 di rentang mulai…selesai (menunggu zona/handoff) |
| **Biaya aktif** | periode_aktif × **tarif** |
| **Biaya idle** | periode_idle × **tarif** |
| **Biaya total tim** | (aktif + idle) × tarif = waktu_lapangan × tarif |
| **Biaya total proyek** | jumlah biaya 5 tim |

Tarif diisi di **sidebar** (default 100). Tarif aktif = idle (biaya kru tetap selama di lapangan); pemisahan menonjolkan **pemborosan idle**.

### 5.2 Contoh angka (tarif 100, zona 40, Normal)

| Skenario | Durasi proyek | Σ aktif | Σ idle | Total biaya |
|----------|---------------|---------|--------|-------------|
| Tanpa var, batch 1 | 44 | 200 | 0 | **20.000** |
| Tanpa var, batch 4 | 56 | 200 | 0 | **20.000** |
| Var sedang, batch 4 | 68 | 173 | 56 | **22.900** |

- Batch 1 vs 4 tanpa var: **durasi beda**, **biaya sama** — volume kerja kru sama, tidak ada idle.  
- Variability: idle muncul → **biaya idle & total naik**, meskipun “kerja murni” (aktif) bisa sedikit beda karena pola undi.

### 5.3 Grafik biaya (tab Perbandingan)

Sub-tab **Biaya**:

- Aktif vs idle (berdampingan)  
- Stacked aktif + idle (= total)  
- Total / idle per skenario  
- Per tim (total & idle)

---

## 6. Tab Perbandingan

### 6.1 Fungsi

Membandingkan **2–5 skenario** (variability, batch, kapasitas) secara head-to-head.

### 6.2 Tombol isi cepat

| Tombol | Isi |
|--------|-----|
| **5× variability** | 5 skenario: tanpa var → sangat tinggi (batch = sidebar) |
| **Tanpa var vs Sedang** | 2 skenario |
| **Batch 1 vs 4** | OPF vs batch 4, tanpa var |
| Hapus hasil | Bersihkan |

Lalu tekan **Jalankan perbandingan**.

### 6.3 Ringkasan tabel

Kolom penting:

- Durasi proyek  
- Σ periode aktif / idle  
- Biaya aktif / idle / total  
- Batch, variability, TH, WIP, T5 selesai  

### 6.4 Sub-tab grafik

| Sub-tab | Isi |
|---------|-----|
| Line of Balance | Overlay (default: tim terakhir) |
| Buffer / WIP | Profil multi-skenario |
| Utilisasi | Bar per tim × skenario |
| **Biaya** | Total, idle, stacked, per tim |
| Little's Law | TH, WIP, CT, W_min, W_opt |
| Kingman | CT vs utilisasi |
| Inventory / FR | Tradeoff inventory–fill rate |

### 6.5 Pesan pembelajaran

- Variability ↑ → durasi ↑, idle ↑, **biaya ↑**.  
- Batch 4 vs 1 (tanpa var) → durasi ↑, biaya kru sering **sama** (tidak ada idle).  
- Utilisasi turun di hilir saat antrian/starvation.

---

## 7. Tab Takt plan

### 7.1 Setting fix

| Item | Nilai |
|------|--------|
| Bay / zona | **3 × 3 m = 9 m²** |
| TZ per lantai | **40** (genap, habis ÷4) |
| Luas per lantai | 40 × 9 = **360 m²** (fix) |
| Kapasitas Normal | **4 bay / hari** per tim |
| tₑ | **0,25 hari/bay** |
| T₀ (1 tim, 1 lantai) | 40/4 = **10 hari** |

### 7.2 Yang bisa diubah

- **Jumlah lantai** (permintaan)
- **Waktu tersedia** (hari, default **12**)
- **TW** (jumlah tim / wagon)

### 7.3 Rumus

```text
TT = T_avail_hari / N_lantai
tₑ = 1/4 hari per bay          # Normal
TD_lantai = (TW + 40 − 1) × 0,25
TD_total  ≈ N_lantai × TD_lantai
```

Default T_avail = **12 hari**. TW=5: TD/lantai = 11 hari; 2 lantai → 22 hari (perlu longgarkan hari / kurangi lantai / cek kapasitas).

### 7.4 Literatur

[LEI — Takt Time](https://www.lean.org/lexicon-terms/takt-time/): available time ÷ customer demand (di sini demand = lantai).

## 8. Line of Balance (LOB)

- Sumbu X = periode, Y = zona kumulatif.  
- Setiap tim satu warna; **mulai dari (0,0)**.  
- Kemiringan ≈ kapasitas efektif.  
- Jarak horizontal antar kurva ≈ buffer / waiting.  
- Ideal (tanpa var) = garis lurus; variability = patahan.

---

## 9. Buffer / WIP

**WIP** antar dua tim = zona sudah dilepas hulu, belum dikerjakan hilir.

- WIP tinggi → CT naik (Little's Law), masalah aliran tersembunyi.  
- WIP terlalu rendah + var tinggi → starvation hilir, idle ↑, biaya idle ↑.

---

## 10. Utilisasi

\[
u \approx \frac{\text{produksi}}{\text{kapasitas efektif}}
\]

- Idle/starvation menurunkan utilisasi.  
- Utilisasi sangat tinggi + var tinggi → CT meledak (Kingman).

---

## 11. Little's Law & kurva WIP–TH–CT

### 11.1 Identitas

\[
WIP = TH \times CT
\]

| Metrik | Arti |
|--------|------|
| TH | Throughput (zona/periode), sering ≈ total_zona / durasi |
| WIP | Rata-rata work-in-process di pipeline |
| CT | Cycle time ≈ WIP / TH |

### 11.2 Batas Factory Physics

| Simbol | Arti |
|--------|------|
| TH_max | Kapasitas bottleneck |
| T0 | Process time ideal |
| W0 / **W_min** | WIP kritis (kasus terbaik, V≈0) |
| **W_opt** | WIP praktis (naik jika variability naik) |
| **CONWIP** | Target WIP kendali (slider) |

Bila V=0 → W_min ≈ W_opt (bukan bug).

### 11.3 Kurva

- Sumbu X = WIP  
- Kiri Y = TH; kanan Y = CT  
- Batas ideal (tanpa var / TH_max) vs aktual  
- Slider CONWIP + dampak ke TH & CT  

---

## 12. Kingman (VUT)

\[
CT \approx t_e + V \times \frac{u}{1-u} \times t_e
\]

- **V** = variability, **u** = utilisasi, **t_e** = waktu proses efektif.  
- Grafik CT vs u (gabungan tim).  
- u → 1 + V tinggi → CT meledak.

---

## 13. Inventory vs fill rate

- Sumbu X = fill rate; Y = inventory (base-stock intuition).  
- Fill rate tinggi biasanya butuh inventory lebih besar.  
- Di parade: buffer antar-tim menopang “ketersediaan” kerja hilir.

---

## 14. Unduh data (Excel/CSV)

Tersedia di:

- Tab **Simulasi** (hasil run + analisis)  
- Tab **Perbandingan** (multi-skenario)  
- Tab **Takt plan** (rencana / simulasi / bandingan)

Gunakan untuk presentasi dan arsip kelas.

---

## 15. Skenario latihan kelas

| # | Setup | Amati |
|---|--------|--------|
| 1 | Normal, tanpa var, batch 4 | Durasi 56; Σ aktif 200; idle 0; biaya 20.000 (tarif 100) |
| 2 | Sama, batch 1 | Durasi 44; biaya masih 20.000 — beda kalender, sama volume kru |
| 3 | Normal, var sedang, batch 4 | Durasi ↑, idle ↑, biaya ↑ |
| 4 | Perbandingan 5× variability | LOB, biaya stacked, utilisasi |
| 5 | Takt: TW=5, TZ=40, TT=1 | TD=44; wagon penuh 40 zona |
| 6 | Takt: ubah TZ 30/40/50 (TT tetap) | TD naik dengan TZ |
| 7 | Takt: lingkup tetap | TD sedikit turun saat TZ naik (diminishing returns) |
| 8 | Little: CONWIP | Geser slider, baca TH & CT |
| 9 | Tarif T1=200, lain 100 | Biaya tidak simetris antar tim |

---

## 16. Batasan model

1. **Satu** lantai / satu rantai 5 trade — bukan multi-tower.  
2. Kapasitas & var **diskrit per zona**; bukan continuous distribution di lapangan.  
3. Tidak ada shift, cuaca, rework eksplisit (bisa diwakilkan var tinggi).  
4. Biaya = model edukasi (tarif × periode); bukan estimasi kontrak penuh.  
5. Takt plan ideal vs simulasi aktual bisa beda jika ada variability.  
6. Deploy Streamlit Cloud mengikuti repo GitHub; butuh refresh setelah push.

---

## 17. Literatur

1. Tommelein, I. D., Riley, D., & Howell, G. (1999). Parade Game: Impact of Work Flow Variability… *J. Constr. Eng. Manage.*  
2. Hopp, W. J., & Spearman, M. L. *Factory Physics*.  
3. Little, J. D. C. Little's Law.  
4. Project Production Institute — [Little's Law in production systems…](https://projectproduction.org/journal/littles-law-in-production-systems-with-yield-loss/)  
5. Kingman, J. F. C. — VUT / approximation queueing.  
6. Frandson, A., Berghede, K., & Tommelein, I. — Takt time planning.  
7. Lean Built — [Is Takt Really Magic?](https://leanbuilt.us/is-takt-really-magic/) — TD = (TW+TZ−1)×TT.  
8. LCI / Lean Construction — Takt, continuous flow, handoff.  

---

*Manual ini mengikuti perilaku aplikasi terkini: zone-flow, biaya aktif/idle, Little's Takt Law, analisis Factory Physics, dan unduh Excel/CSV. Siap dipakai di kelas.*
