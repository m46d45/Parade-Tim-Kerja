# Manual — Parade Tim Kerja

**Simulasi parade tim kerja pekerjaan pengecoran lantai beton**  
Panduan lengkap untuk mahasiswa, dosen, dan peserta workshop Lean Construction.

| | |
|---|---|
| Aplikasi | **Parade Tim Kerja** (Streamlit) |
| Model | Zone-flow classroom (zona demi zona, batch handoff) |
| Default | Total zona **40** · Seed **12345** · Batch **4** · 5 tim (tetap) |
| Tanpa coding | Semua di browser |

---

## Daftar isi

1. [Tujuan pembelajaran](#1-tujuan-pembelajaran)
2. [Model zone-flow & konsep dasar](#2-model-zone-flow--konsep-dasar)
3. [Navigasi aplikasi](#3-navigasi-aplikasi)
4. [Tab Simulasi](#4-tab-simulasi)
5. [Tab Perbandingan](#5-tab-perbandingan)
6. [Tab Takt plan](#6-tab-takt-plan)
7. [Hasil analisis: Line of Balance](#7-hasil-analisis-line-of-balance)
8. [Hasil analisis: Buffer / WIP](#8-hasil-analisis-buffer--wip)
9. [Hasil analisis: Utilisasi](#9-hasil-analisis-utilisasi)
10. [Hasil analisis: Little's Law](#10-hasil-analisis-littles-law)
11. [Hasil analisis: Kingman (VUT)](#11-hasil-analisis-kingman-vut)
12. [Hasil analisis: Inventory vs fill rate](#12-hasil-analisis-inventory-vs-fill-rate)
13. [Skenario latihan kelas](#13-skenario-latihan-kelas)
14. [Batasan model](#14-batasan-model)
15. [Literatur](#15-literatur)
16. [Pemecahan masalah](#16-pemecahan-masalah)

---

## 1. Tujuan pembelajaran

Setelah memakai aplikasi ini, peserta diharapkan mampu:

1. Menjelaskan **parade tim kerja** pada floor cycle beton (5 trade berurutan di zona).
2. Membedakan **kapasitas produksi** (zona/periode) dan **variability** (perubahan kapasitas per zona).
3. Memahami **batch handoff** vs **one-piece flow** dan dampaknya ke durasi, WIP, serta utilisasi.
4. Membaca **Line of Balance (LOB)** yang mulai dari (0,0) dan bergeser antar tim.
5. Menerapkan **Little's Law** (WIP = TH × CT) dan membaca kurva batas ideal (TH_max, T0, W0).
6. Memakai intuisi **Kingman / VUT**: variability dan utilisasi menaikkan cycle time.
7. Memahami tradeoff **inventory vs fill rate**.
8. Menyusun dan menilai **takt plan** (rencana irama) vs aktual (reliability).

---

## 2. Model zone-flow & konsep dasar

### 2.1 Parade floor cycle

```text
T1 Pemasangan Bekisting
 → T2 Pemasangan Tulangan
  → T3 Pengecoran Beton
   → T4 Pembongkaran Bekisting
    → T5 Finishing Lantai
```

Satu zona hanya dikerjakan satu tim pada satu waktu. Tim hilir baru boleh masuk setelah zona **dilepas** oleh tim hulu (sesuai batch handoff).

### 2.2 Zona, periode, kumulatif

| Istilah | Arti |
|---------|------|
| **Zona** | Satuan lokasi kerja (pelat / bay / unit). |
| **Periode** | Satuan waktu simulasi (hari / shift). |
| **Kumulatif** | Jumlah zona yang sudah diselesaikan suatu tim (mulai **0**). |

### 2.3 Kapasitas produksi (zona/periode)

Kapasitas = laju progress pada **satu zona**.

| Profil | Definisi |
|--------|----------|
| Sangat rendah | 1 zona butuh **3** periode |
| Rendah | 1 zona butuh **2** periode |
| Normal | **1** zona / 1 periode |
| Tinggi | **2** zona / 1 periode |
| Sangat tinggi | **3** zona / 1 periode |

Tanpa variability, kapasitas **tetap** di setiap zona.

### 2.4 Variability (perubahan kapasitas per zona)

Setiap kali tim **memulai zona baru**, kapasitas diundi sekali (lalu dikunci sampai zona selesai).

| Level | Rentang (× kapasitas dasar) |
|-------|------------------------------|
| Tanpa variability | ×1,0 tetap |
| Rendah | ×0,75 atau ×1,25 (**±25%**) |
| Sedang | ×0,5 atau ×1,5 (**±50%**) |
| Tinggi | ×0,25 atau ×1,75 (**±75%**) |
| Sangat tinggi | ×0,1 atau ×1,9 (**±90%**) |

> Bukan model “undi 0 atau 3 zona sekaligus”. Variability mengubah **laju di zona**, bukan lompat massal.

### 2.5 Batch handoff

| Batch | Perilaku |
|-------|----------|
| **1** (one-piece) | Tiap zona selesai langsung dilepas (periode berikutnya). |
| **2–5** | Zona dikumpulkan; dilepas setelah batch penuh. Default **4**. |
| Sisa di akhir | Sisa batch tetap dilepas agar proyek tidak macet. |

Handoff selalu **periode berikutnya** (ada jeda), sehingga LOB antar tim **bergeser**, tidak menumpuk.

### 2.6 Idle & utilisasi (teori singkat)

| Istilah | Arti |
|---------|------|
| **Idle** | Kapasitas terbuang karena **tidak ada zona siap** (kelaparan buffer / menunggu handoff). |
| **Utilisasi** | Produksi ÷ kapasitas efektif. Tim yang terus bekerja tanpa menunggu ≈ 100%. |
| **Buffer / WIP** | Zona sudah dilepas hulu, belum dikerjakan hilir. |

---

## 3. Navigasi aplikasi

### 3.1 Sidebar

| Kontrol | Fungsi |
|---------|--------|
| Logo & judul | Parade Tim Kerja |
| **Total zona** | Ukuran proyek (default 40) |
| **Kunci seed** + **Seed** | Reproduktibilitas undian (default 12345) |
| **Ukuran batch handoff** | Default 4; opsi 5, 3, 2, 1 |

Jumlah tim **tetap 5**.

### 3.2 Empat tab utama

| Tab | Isi |
|-----|-----|
| **Simulasi** | Satu skenario + grafik analisis lengkap |
| **Perbandingan** | 2–5 skenario berdampingan |
| **Takt plan** | Rencana irama + reliability vs aktual |
| **Manual** | Dokumen ini (bisa diunduh) |

---

## 4. Tab Simulasi

### 4.1 Pengaturan

- **Seragam** — semua tim sama (kapasitas + variability).
- **Per tim** — tiap trade (Bekisting … Finishing) bisa beda.
- Tombol **Jalankan** / **Atur ulang**.

### 4.2 Metrik ringkas (setelah run)

| Metrik | Arti |
|--------|------|
| Durasi | Periode sampai T5 selesai |
| vs Ideal | Selisih terhadap acuan bottleneck + pipeline |
| Throughput | Zona / periode (sistem) |
| Idle total | Jumlah idle semua tim |
| Puncak WIP | Maksimum total buffer serentak |
| Batch | Ukuran handoff run ini |

### 4.3 Sub-tab hasil (lihat bab 7–12)

Line of Balance · Buffer / WIP · Utilisasi · Little's Law · Kingman · Inventory / FR

### 4.4 Latihan cepat

1. Semua Normal, tanpa var, batch **4** → catat durasi & puncak WIP.  
2. Batch **1** → durasi lebih pendek, WIP lebih tipis.  
3. T1 **Rendah**, lain Normal → LOB T1 landai; idle/utilisasi hilir memburuk.  
4. Variability **Sedang** → garis patah-patah; idle & WIP naik.

---

## 5. Tab Perbandingan

### 5.1 Kontrol

- **Jumlah skenario** 2–5.
- Per skenario: kapasitas, variability, **batch sendiri**.
- Tombol cepat: **5× variability**, **Tanpa var vs Sedang**, **Batch 1 vs 4**.
- **Jalankan perbandingan** (tidak otomatis).

### 5.2 Hasil

- Tabel ringkasan (durasi, idle, TH, WIP⌀, CT, …).
- Sub-tab sama seperti Simulasi, tetapi **multi-skenario**:
  - LOB (tim terakhir)
  - Buffer / WIP total
  - Utilisasi per tim
  - Little's Law (titik operasi)
  - Kingman (Σ CT / CT vs u̅)
  - Inventory / FR (titik skenario)

### 5.3 Latihan cepat

1. Batch 1 vs 4 → one-piece lebih cepat, WIP lebih rendah.  
2. 5× variability → durasi & CT memburuk seiring level var.  
3. Campur batch dan var dalam 3–5 skenario.

---

## 6. Tab Takt plan

### 6.1 Prinsip

Takt plan lean construction biasanya:

1. **One-piece flow** — serah terima zona per zona (bukan batch besar).  
2. **Jumlah zona** — variabel desain utama (menentukan panjang parade & durasi).  
3. **Sistem buffer** — tiga jenis agar irama tetap andal.

| Istilah | Arti |
|---------|------|
| **One-piece flow** | Batch handoff = 1 (tetap di tab ini) |
| **Jumlah zona** | Skala zonasi; what-if menampilkan durasi vs zona |
| **Takt time** | Waktu rencana per zona di satu stasiun |
| **Reliability** | % (tim, zona) selesai sesuai/sebelum rencana |

### 6.2 Tiga jenis buffer

| Buffer | Teori | Di app |
|--------|--------|--------|
| **Kapasitas** | Cadangan produktivitas (standby, lembur, kru ekstra) — Tommelein 2020 | +% pada kapasitas dasar → rate efektif naik |
| **Waktu** | Slack jadwal; takt time lebih longgar dari pure process time | +periode per zona pada takt time |
| **Inventory** | Stok zona antar-tim (decoupling stock) | 0–1 = OPF murni; ≥2 = lepas tiap N zona |

Tanpa buffer + tanpa variability → rencana = aktual (reliability 100%).  
Dengan variability, buffer menolong reliability dan/atau mendekati target periode.

### 6.3 Mode desain

1. **Hitung durasi** dari zona + kapasitas + buffer.  
2. **Target periode** — cek apakah rate efektif (+ buffer) mencukupi.

### 6.4 Alur di tab

1. Atur **jumlah zona** dan kapasitas dasar.  
2. Atur **3 buffer**.  
3. **Jalankan simulasi** (tombol di atas grafik).  
4. Baca reliability & overlay rencana vs aktual.  
5. Opsional: Tommelein 2020 (S1/S2/S3).

### 6.5 Grafik

| Grafik | Isi |
|--------|-----|
| LOB rencana / aktual | Putus-putus vs tegas |
| Wagon chart | Batang waktu per zona × tim |
| What-if zona | Durasi OPF vs jumlah zona (tanpa buffer) |

### 6.6 Contoh

- 40 zona, OPF, Normal, tanpa buffer → rencana **44** periode.  
- Tambah buffer kapasitas 20% → rate efektif naik → durasi rencana turun.  
- Buffer waktu +1 p/zona → takt time lebih longgar → durasi naik (jadwal lebih “aman”).  
- Buffer inventory 4 → mirip handoff tiap 4 zona (bukan OPF murni).


## 7. Hasil analisis: Line of Balance

### 7.1 Teori

**Line of Balance (LOB)** memplot kemajuan kumulatif tiap trade terhadap waktu. Dalam konstruksi berulang (floor cycle, unit berulang), LOB menunjukkan **aliran** dan **interferensi** antar trade.

| Sumbu | Arti |
|-------|------|
| **X** | Periode (mulai 0) |
| **Y** | Zona kumulatif (mulai 0) |
| **Kemiringan** | ≈ kapasitas (zona/periode) |
| **Geser antar garis** | Handoff + jeda periode |

### 7.2 Di app

- **Simulasi**: detail awal + seluruh proyek; satu garis per tim.  
- **Perbandingan**: biasanya **tim terakhir** (penyelesaian proyek) per skenario.  
- **Takt plan**: rencana (putus-putus) vs aktual (tegas).

### 7.3 Cara baca

- Garis **menumpuk** = handoff terlalu “instan” atau model salah (di app yang benar, garis bergeser).  
- Garis **landai** = kapasitas rendah atau variability menghambat.  
- Jarak horizontal antar trade ≈ waktu tunggu / buffer kebijakan batch.

---

## 8. Hasil analisis: Buffer / WIP

### 8.1 Teori

**Work-In-Process (WIP)** di antara dua tim = zona yang sudah selesai hulu tetapi belum dikerjakan hilir (**buffer**). WIP berlebih menaikkan cycle time (lihat Little's Law) dan menyembunyikan masalah aliran.

### 8.2 Di app

| Tampilan | Isi |
|----------|-----|
| Grafik garis | B1…B4 (T1→T2, …, T4→T5) vs periode |
| Stacked | Komposisi total WIP |
| Tabel puncak | Puncak per buffer |
| Perbandingan | Total WIP vs waktu, multi-skenario |

### 8.3 Pola tipikal

| Kondisi | Puncak WIP |
|---------|------------|
| Batch 4, seimbang, tanpa var | ≈ **4** per buffer |
| Batch 1 (one-piece) | ≈ **1** |
| Variability tinggi | WIP lebih liar, puncak naik |

---

## 9. Hasil analisis: Utilisasi

### 9.1 Teori

**Utilisasi** = proporsi kapasitas yang menjadi produksi. Dalam parade, utilisasi hilir sering jatuh bukan karena “malas”, melainkan **menunggu zona** (starvation).

\[
u = \frac{\text{produksi}}{\text{kapasitas efektif}}
\]

Idle dihitung saat tim sudah mulai di lapangan tetapi **tidak ada zona siap**.

### 9.2 Di app

- Batang % per tim + tabel (produksi, kapasitas, idle, utilisasi).  
- Perbandingan: utilisasi T1…T5 dikelompokkan per skenario.

### 9.3 Pola tipikal

| Kondisi | Utilisasi |
|---------|-----------|
| Semua Normal, seimbang, tanpa var | ≈ 100% |
| T1 lambat, lain normal | T2–T5 utilisasi turun (banyak idle) |
| Variability sedang/tinggi | Utilisasi rata-rata turun |

---

## 10. Hasil analisis: Little's Law

### 10.1 Teori

Bentuk klasik (tanpa yield loss):

\[
\text{WIP} = \text{TH} \times \text{CT}
\]

| Simbol | Nama | Di app |
|--------|------|--------|
| **TH** | Throughput | Total zona ÷ durasi |
| **WIP pipeline** | Work in process | Rata-rata (kumulatif T1 − T5) |
| **WIP buffer** | Antrian antar-tim | Rata-rata jumlah buffer |
| **CT** | Cycle time | WIP ÷ TH |

Artikel PPI membahas perluasan bila ada **yield loss**. Di app ini **y = 1** (tidak ada scrap), jadi bentuk klasik berlaku. Cek: **TH × CT ≈ WIP**.

### 10.2 Grafik WIP–TH–CT (ganda sumbu)

| Sumbu | Isi |
|-------|-----|
| **X** | WIP |
| **Y kiri** | Throughput (TH) |
| **Y kanan** | Cycle time (CT) |

### 10.3 WIP minimal, WIP optimal, dan CONWIP

| Konsep | Arti | Di grafik |
|--------|------|-----------|
| **W_min (W0)** | WIP **minimal/kritis** = TH_max × T0 (Factory Physics best case) | Garis hijau |
| **W_opt** | WIP **optimal praktis** dengan variability: α·W0·(1 + V·α/(1−α)), α≈0,9. Jika **V=0** maka **W_opt = W_min** (benar, bukan bug). | Garis oranye |
| **CONWIP** | *Constant WIP* — batas WIP konstan; saran awal = W_opt | Garis ungu + pita |

**Intuisi:**  
- V = 0 → cukup W_min untuk TH penuh → W_opt = W_min.  
- V > 0 → antrian → butuh WIP lebih besar → **W_opt > W_min**.  
- Terlalu sedikit WIP → TH rendah; terlalu banyak → CT membengkak.  
- **CONWIP ≈ W_opt** menahan inventory sambil menjaga throughput.

Slider CONWIP di tab Little's Law (Simulasi) memindahkan batas ungu di grafik.

### 10.4 Batas ideal Factory Physics (tanpa variasi)

| Simbol | Arti |
|--------|------|
| **TH_max** | Kapasitas mean terendah (bottleneck) di 5 tim |
| **T0** | Jumlah waktu proses murni semua stasiun |
| **W0** | Critical WIP = TH_max × T0 |

| Rezim | TH | CT |
|-------|----|----|
| **W ≤ W0** | W / T0 (naik) | **T0** (minimum, datar) |
| **W ≥ W0** | **TH_max** (datar) | W / TH_max (naik) |

Kurva aktual (dengan variability) **tidak lebih baik** dari batas: TH lebih rendah dan/atau CT lebih tinggi.

Contoh Normal: TH_max = 1, T0 = 5, W0 = 5.

### 10.5 Jejak WIP

Grafik pipeline WIP vs buffer WIP sepanjang periode — melihat “isi pipa” proyek.

---

## 11. Hasil analisis: Kingman (VUT)

### 11.1 Teori

Pendekatan antrian **G/G/1** (Kingman / Factory Physics) untuk cycle time di satu stasiun:

\[
\text{CT} \approx t_e + \frac{c_a^2 + c_e^2}{2} \cdot \frac{u}{1-u} \cdot t_e
\]

| Simbol | Nama | Di app |
|--------|------|--------|
| **t_e** | Mean process time | Waktu 1 zona di stasiun (T = 1/C) |
| **u** | Utilisasi | Dari simulasi |
| **c_e** | CV process time | Dari variability (tanpa var → 0) |
| **c_a** | CV kedatangan | T1 ≈ 0; hilir ≈ c_e hulu |
| **V** | (c_a² + c_e²)/2 | Faktor variability |
| **U** | u/(1−u) | Meledak saat u → 1 |

**VUT**: naiknya **V**ariability, **U**tilisasi, atau **T** process time menaikkan CT.

Tanpa variability (c_a = c_e = 0) → wait = 0 → **CT = t_e**.

### 11.2 Grafik di app

| Grafik | Isi |
|--------|-----|
| **CT vs u̅** | Kurva keluarga V; titik = utilisasi **gabungan** (rata-rata tim) |
| **CT Kingman vs CT amati** | Per stasiun T1…T5 |
| **Perbandingan** | Titik operasi skenario di bidang CT–u̅ |

### 11.3 Catatan

Kingman mengasumsikan antrian **stasioner**. Proyek berhingga + batch handoff bisa beda numerik dari prediksi; gunakan untuk **arah** (var/u naik → antrian mahal), bukan ramalan absolut.

---

## 12. Hasil analisis: Inventory vs fill rate

### 12.1 Teori

Tradeoff klasik **service–inventory** (inventory theory / Factory Physics):

| Sumbu | Arti |
|-------|------|
| **X — Fill rate** | % permintaan terpenuhi **langsung dari stok** (tanpa stockout) |
| **Y — Inventory** | Rata-rata WIP di buffer |

Semakin tinggi target fill rate (mendekati 100%), inventory yang dibutuhkan **naik tajam** (diminishing returns). Variability tinggi → butuh lebih banyak inventory untuk fill rate yang sama.

### 12.2 Definisi di app

- **Inventory** = rata-rata isi buffer B1…B4.  
- **Fill rate** (analog tipe-2) ≈ `produksi / (produksi + idle)` pada tim hilir (idle = kelaparan buffer).  
- Kurva teoritis base-stock (unit normal loss) sebagai backdrop.  
- Titik sistem + berlian per buffer B1…B4.

### 12.3 Pola

| Kondisi | Inventory | Fill rate |
|---------|-----------|-----------|
| Seimbang, tanpa var | Sedang (≈ batch) | Tinggi (~100%) |
| Var tinggi | Naik / lebih liar | Turun |
| One-piece | Tipis | Bergantung keandalan hulu |

---

## 13. Skenario latihan kelas

| # | Setup | Amati |
|---|--------|--------|
| 1 | Normal, tanpa var, batch 4 | LOB bergeser; WIP puncak ≈ 4; util ≈ 100% |
| 2 | Sama, batch 1 | Durasi↓, WIP↓, rencana takt lebih pendek |
| 3 | T1 Rendah, lain Normal | Idle hilir; utilisasi T2–T5 turun |
| 4 | Variability sedang semua | LOB patah; CT Little & Kingman naik |
| 5 | Perbandingan 5× var | Durasi & CT vs level var |
| 6 | Takt plan + var sedang | Reliability < 100%; selisih durasi |
| 7 | Tommelein S1/S2/S3 | Standby menekan idle vs classic |

Diskusi: *idle = menunggu zona, bukan malas*; *batch = kebijakan serah terima area*; *takt = janji irama*.

---

## 14. Batasan model

- Satu jalur zona, 5 tim tetap; tanpa cuaca, absensi, multitasking eksplisit.  
- Variability = undi kapasitas per zona (bukan Monte-Carlo ratusan faktor).  
- Handoff selalu periode berikutnya (tidak instan).  
- Kingman & kurva teoritis FR = pendekatan stasioner / base-stock untuk **intuisi**.  
- Cocok untuk **pembelajaran sistem & kebijakan**, bukan penjadwalan proyek 1:1.

---

## 15. Literatur

### Inti Parade of Trades & takt

1. **Tommelein, I. D., Riley, D. R., & Howell, G. A. (1999).** *Parade Game: Impact of Work Flow Variability on Trade Performance.* Journal of Construction Engineering and Management, ASCE.  
2. **Choo, H. J., & Tommelein, I. D. (1999).** *Parade Game.* Technical Report, P²SL, University of California, Berkeley.  
3. **Tommelein, I. D. (2020).** *Takting the Parade of Trades: Use of Capacity Buffers to Gain Work Flow Reliability.* Proc. 28th Annual Conference of the International Group for Lean Construction (IGLC28). https://doi.org/10.24928/2020/0076  

### Factory Physics, Little, Kingman, inventory

4. **Hopp, W. J., & Spearman, M. L.** *Factory Physics* (edisi relevan). McGraw-Hill / Waveland — Little's Law, VUT/Kingman, operations curves, inventory–service.  
5. **Kingman, J. F. C. (1961).** Pendekatan heavy-traffic untuk waktu tunggu G/G/1 (dasar bentuk VUT).  
6. **Little, J. D. C. (1961).** *A Proof for the Queuing Formula: L = λW.* Operations Research.  
7. **Project Production Institute.** *Little’s Law in Production Systems with Yield Loss.*  
   https://projectproduction.org/journal/littles-law-in-production-systems-with-yield-loss/  

### Takt planning di konstruksi

8. **Lean Construction Institute.** *Takt Time* / Takt planning, steering & control.  
   https://leanconstruction.org/lean-topics/takt-time/  
9. Materi terkait **Takt Production System**, Line of Balance, dan location-based scheduling (lihat rujukan LCI & IGLC).

### Catatan pemakaian literatur di app

| Topik app | Acuan utama |
|-----------|-------------|
| Variability & parade | Tommelein et al. (1999); Choo & Tommelein (1999) |
| Takt + capacity buffer | Tommelein (2020) |
| WIP = TH × CT | Little (1961); Hopp & Spearman; PPI yield-loss (konteks y=1) |
| CT vs u, VUT | Kingman; Hopp & Spearman |
| Inventory–fill rate | Inventory theory / Factory Physics (service–inventory tradeoff) |
| LOB | Praktik penjadwalan berulang + literatur parade |

---

## 16. Pemecahan masalah

| Gejala | Coba |
|--------|------|
| Hasil beda tiap buka | Nyalakan **Kunci seed acak** |
| UI / logo lama | Muat ulang paksa (Ctrl/Cmd+Shift+R) |
| Simulasi error max periode | Turunkan zona; hindari kapasitas sangat rendah + var ekstrem bersamaan |
| LOB menumpuk | Pastikan batch & zone-flow terbaru; handoff tidak instan |
| Utilisasi semua 100% | Normal jika seimbang tanpa var; coba T1 lebih lambat atau naikkan var |
| Takt reliability 100% | Tanpa var, aktual = rencana; naikkan variability untuk melihat selisih |
| Tab Takt tidak mensimulasi | Tekan **Jalankan simulasi** (tidak otomatis) |

---

*Parade Tim Kerja — manual zone-flow untuk pembelajaran Lean Construction.*  
*Diselaraskan dengan tab Simulasi, Perbandingan, Takt plan, dan suite analisis (LOB, Buffer/WIP, Utilisasi, Little's Law, Kingman, Inventory/FR).*
