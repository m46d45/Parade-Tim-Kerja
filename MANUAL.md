# Manual — Parade Tim Kerja

**Simulasi parade tim kerja pekerjaan pengecoran lantai beton**

Panduan lengkap untuk mahasiswa, dosen, dan peserta workshop Lean Construction / Project Production.

| | |
|---|---|
| Aplikasi | **Parade Tim Kerja** (Streamlit) |
| Model | Zone-flow classroom (zona demi zona, batch handoff) |
| Default | Total zona **40** · Seed **12345** · Batch **4** · 5 tim (tetap) |
| Bahasa UI | Indonesia (istilah teknis: batch, WIP, takt, CONWIP, dll. dipertahankan) |

---

## Daftar isi

1. [Tujuan pembelajaran](#1-tujuan-pembelajaran)
2. [Model zone-flow & konsep dasar](#2-model-zone-flow--konsep-dasar)
3. [Navigasi aplikasi](#3-navigasi-aplikasi)
4. [Tab Simulasi](#4-tab-simulasi)
5. [Tab Perbandingan](#5-tab-perbandingan)
6. [Tab Takt plan](#6-tab-takt-plan)
7. [Line of Balance (LOB)](#7-line-of-balance-lob)
8. [Buffer / WIP](#8-buffer--wip)
9. [Utilisasi](#9-utilisasi)
10. [Little's Law & kurva WIP–TH–CT](#10-littles-law--kurva-wipthct)
11. [Kingman (VUT)](#11-kingman-vut)
12. [Inventory vs fill rate](#12-inventory-vs-fill-rate)
13. [Skenario latihan kelas](#13-skenario-latihan-kelas)
14. [Batasan model](#14-batasan-model)
15. [Literatur](#15-literatur)

---

## 1. Tujuan pembelajaran

Setelah memakai aplikasi ini, peserta diharapkan mampu:

1. Menjelaskan **parade tim kerja** pada floor cycle beton (5 trade berurutan di zona).
2. Membedakan **kapasitas produksi** (zona/periode) dan **variability** (perubahan kapasitas per zona).
3. Memahami **batch handoff** vs **one-piece flow** dan dampaknya ke durasi, WIP, serta utilisasi.
4. Membaca **Line of Balance (LOB)** yang mulai dari (0,0) dan bergeser antar tim.
5. Menerapkan **Little's Law** (WIP = TH × CT) serta membaca **W_min**, **W_opt**, dan **CONWIP**.
6. Memakai intuisi **Kingman / VUT**: variability dan utilisasi menaikkan cycle time.
7. Memahami tradeoff **inventory vs fill rate**.
8. Menyusun **takt plan** one-piece dan memahami dampak **jumlah zonasi** (kasar ↔ halus) pada parade.

---

## 2. Model zone-flow & konsep dasar

### 2.1 Parade floor cycle

```text
T1  Pemasangan Bekisting
 → T2  Pemasangan Tulangan
  → T3  Pengecoran Beton
   → T4  Pembongkaran Bekisting
    → T5  Finishing Lantai
```

Satu zona hanya dikerjakan satu tim pada satu waktu. Tim hilir baru boleh masuk setelah zona **dilepas** oleh tim hulu (sesuai kebijakan batch / buffer inventory).

### 2.2 Zona, periode, kumulatif

| Istilah | Arti |
|---------|------|
| **Zona** | Satuan lokasi kerja (pelat / bay / unit). |
| **Periode** | Satuan waktu simulasi (hari / shift). |
| **Kumulatif** | Jumlah zona yang sudah diselesaikan suatu tim — grafik mulai dari **0**. |

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

Variability mengubah **laju di zona**, bukan “undi 0 atau 3 zona sekaligus”.

### 2.5 Batch handoff (tab Simulasi / Perbandingan)

| Batch | Perilaku |
|-------|----------|
| **1** (one-piece) | Tiap zona selesai langsung dilepas (periode berikutnya). |
| **2–5** (dst.) | Zona dikumpulkan; dilepas setelah batch penuh. Default **4**. |
| Sisa di akhir | Sisa batch tetap dilepas agar proyek tidak macet. |

Handoff selalu **periode berikutnya** (ada jeda), sehingga LOB antar tim **bergeser**, tidak menumpuk.

### 2.6 Idle & utilisasi (ringkas)

| Istilah | Arti |
|---------|------|
| **Idle** | Kapasitas terbuang karena **tidak ada zona siap** (menunggu handoff / buffer kosong). |
| **Utilisasi** | Produksi ÷ kapasitas efektif. |
| **Buffer / WIP** | Zona sudah dilepas hulu, belum dikerjakan hilir. |

---

## 3. Navigasi aplikasi

### 3.1 Sidebar

| Kontrol | Fungsi |
|---------|--------|
| Logo & judul | Parade Tim Kerja |
| **Total zona** | Ukuran proyek (default 40) |
| **Kunci seed** + **Seed** | Reproduktibilitas undian (default 12345) |
| **Ukuran batch handoff** | Default 4 (Simulasi/Perbandingan) |

Jumlah tim **tetap 5**.

### 3.2 Empat tab utama

| Tab | Isi |
|-----|-----|
| **Simulasi** | Satu skenario + suite analisis lengkap |
| **Perbandingan** | 2–5 skenario berdampingan |
| **Takt plan** | One-piece flow · bandingkan jumlah zona (kasar / baseline / halus) |
| **Manual** | Dokumen ini (bisa diunduh) |

---

## 4. Tab Simulasi

### 4.1 Pengaturan

- **Seragam** — semua tim sama (kapasitas + variability).
- **Per tim** — tiap trade (Bekisting … Finishing) bisa berbeda.
- Tombol **Jalankan** / **Atur ulang** (simulasi tidak jalan otomatis).

### 4.2 Metrik ringkas (setelah run)

| Metrik | Arti |
|--------|------|
| Durasi | Periode sampai T5 selesai |
| vs Ideal | Selisih terhadap acuan bottleneck + pipeline |
| Throughput | Zona / periode (sistem) |
| Idle total | Jumlah idle semua tim |
| Puncak WIP | Maksimum total buffer serentak |
| Batch | Ukuran handoff run ini |

### 4.3 Sub-tab hasil

Setelah run, buka sub-tab:

1. **Line of Balance** — kemajuan kumulatif  
2. **Buffer / WIP** — antrian antar-tim  
3. **Utilisasi** — % kerja vs idle  
4. **Little's Law** — TH, WIP, CT + kurva + CONWIP  
5. **Kingman** — CT vs utilisasi (VUT)  
6. **Inventory / FR** — fill rate vs inventory  

Teori tiap grafik: bab 7–12.

### 4.4 Latihan cepat

1. Semua Normal, tanpa var, batch **4** → catat durasi & puncak WIP.  
2. Batch **1** → durasi lebih pendek, WIP lebih tipis.  
3. T1 **Rendah**, lain Normal → LOB T1 landai; idle/utilisasi hilir memburuk.  
4. Variability **Sedang** → garis patah-patah; WIP & CT naik.

---

## 5. Tab Perbandingan

### 5.1 Kontrol

- **Jumlah skenario** 2–5.
- Per skenario: kapasitas, variability, **batch sendiri**.
- Tombol cepat: **5× variability**, **Tanpa var vs Sedang**, **Batch 1 vs 4**.
- **Jalankan perbandingan** (tidak otomatis).

### 5.2 Hasil

- Tabel ringkasan (durasi, idle, TH, WIP, CT, W_min, W_opt, …).
- Sub-tab multi-skenario: LOB (tim terakhir), Buffer, Utilisasi, Little's Law, Kingman, Inventory/FR.

### 5.3 Latihan cepat

1. Batch 1 vs 4 → one-piece lebih cepat, WIP lebih rendah.  
2. 5× variability → durasi & CT memburuk seiring level var.  
3. Bandingkan W_opt vs WIP operasi antar skenario.

---

## 6. Tab Takt plan

### 6.1 Peran edukasi

Tab ini adalah **kelanjutan parade tim kerja** dengan kebijakan tetap:

| Tetap | Fokus |
|-------|--------|
| **One-piece flow** (batch = 1) | Dampak **jumlah zonasi** |
| 5 tim berurutan | Train lebih pendek (kasar) vs lebih panjang (halus) |
| Kapasitas + variability | Durasi, LOB, TH, WIP, reliability |

Tidak ada pengaturan buffer takt di aplikasi. Buffer/WIP di tab Simulasi adalah **antrian antar-tim** hasil aliran (bukan buffer desain takt).

### 6.2 Tiga skenario zona

| Skenario | Zona | Arti |
|----------|------|------|
| **A · Kasar** | Lebih sedikit (default ≈ baseline/2) | Unit lokasi lebih “besar”; train lebih pendek |
| **B · Baseline** | Acuan (default = Total zona sidebar) | Titik banding |
| **C · Halus** | Lebih banyak (default ≈ baseline×2) | Banyak unit kecil; train lebih panjang; handoff lebih sering |

### 6.3 Kontrol

| Kontrol | Fungsi |
|---------|--------|
| Zona baseline / kasar / halus | Ukuran zonasi tiap skenario |
| Kapasitas | Laju (zona/periode), seragam |
| Variability | Sama untuk ketiga skenario |
| **Jalankan** | Simulasi OPF ketiga skenario |

### 6.4 Output

1. **Kurva durasi rencana vs jumlah zona** (ideal OPF) — intuisi: zona ↑ → durasi ↑ (train memanjang).  
2. **Tabel ringkasan** — durasi aktual vs rencana, TH, WIP, CT, reliability, idle.  
3. **LOB tim terakhir** — overlay A/B/C.  
4. **LOB semua tim** — panel per skenario.  
5. **Takt plan (wagon)** — train T1→T5, zona di sumbu Y, periode mulai **0**.  
6. **Unduh** CSV/Excel perbandingan + paket takt baseline.

### 6.5 Pesan pembelajaran

- **Zona sedikit (kasar):** lebih sedikit handoff; progres per “langkah” lebih besar di LOB.  
- **Zona banyak (halus):** handoff sering; sensitif variability dan waiting di hilir.  
- **One-piece** menjaga aliran unit-per-unit; bedanya murni dari **berapa unit lokasi** yang Anda potong.  
- Bandingkan **durasi aktual vs rencana** saat variability naik — reliability menurun, terutama pada zonasi halus.

### 6.6 Contoh kelas

| # | Setup | Amati |
|---|--------|--------|
| 1 | Normal, tanpa var, 20 / 40 / 80 | Durasi naik seiring zona; LOB C lebih “panjang” |
| 2 | Sama + var sedang | Reliability & idle memburuk, sering lebih terasa di C |
| 3 | Baseline 40, kasar 10, halus 100 | Ekstrem: unit sangat besar vs sangat kecil |


## 7. Line of Balance (LOB)

### 7.1 Teori

**Line of Balance** memplot kemajuan kumulatif tiap trade terhadap waktu. Dalam pekerjaan berulang (floor cycle), LOB menunjukkan **aliran** dan **gesekan** antar trade.

| Sumbu | Arti |
|-------|------|
| **X** | Periode (mulai 0) |
| **Y** | Zona kumulatif (mulai 0) |
| **Kemiringan** | ≈ kapasitas (zona/periode) |
| **Geser antar garis** | Handoff + jeda periode |

### 7.2 Di app

- **Simulasi**: detail awal + seluruh proyek; satu garis per tim.  
- **Perbandingan**: biasanya **tim terakhir** per skenario.  
- **Takt plan**: rencana (putus-putus) vs aktual (tegas).

### 7.3 Cara baca

- Garis **landai** = kapasitas rendah atau variability menghambat.  
- Jarak horizontal antar trade ≈ waktu tunggu / kebijakan batch.  
- Garis yang **bergeser** (bukan menumpuk) = handoff next-period bekerja benar.

---

## 8. Buffer / WIP

### 8.1 Teori

**Work-In-Process (WIP)** di antara dua tim = zona yang sudah selesai hulu tetapi belum dikerjakan hilir (**buffer**). WIP berlebih menaikkan cycle time (Little's Law) dan menyembunyikan masalah aliran.

### 8.2 Di app

| Tampilan | Isi |
|----------|-----|
| Grafik garis | B1…B4 (T1→T2, …, T4→T5) vs periode |
| Stacked | Komposisi total WIP |
| Tabel puncak | Puncak per buffer |
| Perbandingan | Total WIP vs waktu, multi-skenario |

### 8.3 Pola tipikal

| Kondisi | Puncak WIP (kira-kira) |
|---------|-------------------------|
| Batch 4, seimbang, tanpa var | ≈ **4** per buffer |
| Batch 1 (one-piece) | ≈ **1** |
| Variability tinggi | WIP lebih liar, puncak naik |

---

## 9. Utilisasi

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

## 10. Little's Law & kurva WIP–TH–CT

### 10.1 Teori Little

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
| **X** | WIP (zona) |
| **Y kiri** | Throughput TH (zona/periode) |
| **Y kanan** | Cycle time CT (periode) |

Kurva yang ditampilkan:

| Kurva | Arti |
|-------|------|
| **TH / CT batas** | Kasus terbaik tanpa variasi, dibatasi bottleneck |
| **TH / CT aktual** | Dengan variability (Kingman + perpanjangan Little) |
| **Titik operasi** | Hasil run simulasi |

Sumbu X dibatasi hingga sekitar  
`max(W_min, W_opt, CONWIP, WIP operasi) + 5`  
agar landmark terbaca tanpa grafik terlalu panjang.

### 10.3 Batas ideal Factory Physics (tanpa variasi)

| Simbol | Arti |
|--------|------|
| **TH_max** | Kapasitas mean terendah (bottleneck) di 5 tim |
| **T0** | Jumlah waktu proses murni semua stasiun |
| **W0 = W_min** | Critical WIP = TH_max × T0 |

| Rezim | TH | CT |
|-------|----|----|
| **W ≤ W0** | W / T0 (naik) | **T0** (minimum, datar) |
| **W ≥ W0** | **TH_max** (datar) | W / TH_max (naik) |

Kurva aktual **tidak lebih baik** dari batas: TH lebih rendah dan/atau CT lebih tinggi.

Contoh Normal: TH_max = 1, T0 = 5, W_min = 5.

### 10.4 W_min, W_opt, dan CONWIP

| Konsep | Arti | Tampilan |
|--------|------|----------|
| **W_min (W0)** | WIP **minimal/kritis** = TH_max × T0 (best case) | Garis hijau |
| **W_opt** | WIP **optimal praktis** dengan variability | Garis oranye |
| **CONWIP** | *Constant Work-In-Process* — batas WIP konstan | Garis ungu + pita |

**Rumus W_opt (ajaran Factory Physics / VUT):**

\[
W_{\mathrm{opt}} =
\begin{cases}
W_{\min} & \text{jika } V \approx 0 \\[4pt]
\alpha \cdot W_{\min} \cdot \bigl(1 + V \cdot \tfrac{\alpha}{1-\alpha}\bigr) & \text{jika } V > 0
\end{cases}
\]

dengan α ≈ 0,9 (target fraksi kapasitas bottleneck) dan **V** = faktor variability gabungan \((c_a^2 + c_e^2)/2\).

| Kondisi | W_min vs W_opt |
|---------|----------------|
| Tanpa variability (V ≈ 0) | **Sama** — itu benar, bukan bug |
| Ada variability (V > 0) | **W_opt > W_min** — butuh lebih banyak WIP untuk jaga TH |

**CONWIP:** kebijakan membatasi WIP di tingkat konstan; kerja baru dirilis hanya jika WIP di bawah batas. Saran awal CONWIP = W_opt.

### 10.5 Slider CONWIP & prediksi dampak

Di tab **Little's Law** (Simulasi):

1. Geser **CONWIP — batas WIP konstan**.  
2. Di **bawah slider** muncul prediksi:

| Metrik | Arti |
|--------|------|
| **TH @ CONWIP** | Throughput prediksi di WIP = CONWIP (+ Δ vs operasi) |
| **CT @ CONWIP** | Cycle time prediksi (+ Δ vs operasi; naik = lebih lambat) |
| **Δ WIP** | CONWIP − WIP operasi |
| **TH batas @ WIP** | Throughput kasus terbaik di WIP yang sama |

Prediksi dihitung dari **kurva operasi** (interpolasi), bukan run ulang simulasi — cocok untuk what-if cepat.

**Intuisi:**

- CONWIP **terlalu rendah** (≪ W_opt) → CT cenderung turun, tetapi TH bisa jatuh (kelaparan).  
- CONWIP **terlalu tinggi** → CT membengkak; TH hampir tidak naik jika sudah jenuh.  
- CONWIP **≈ W_opt** → menahan inventory sambil menjaga throughput mendekati kapasitas.

### 10.6 Jejak WIP

Grafik pipeline WIP vs buffer WIP sepanjang periode — melihat “isi pipa” proyek dari waktu ke waktu.

### 10.7 Perbandingan — Little's Law

Tabel multi-skenario memuat TH, WIP, CT, **W_min**, **W_opt**, **CONWIP★**, dan **WIP vs W_opt**.  
Scatter titik operasi memakai garis referensi W_min / W_opt / CONWIP dari skenario pertama.

---

## 11. Kingman (VUT)

### 11.1 Teori

Pendekatan antrian **G/G/1** (Kingman / Factory Physics) untuk cycle time di satu stasiun:

\[
\mathrm{CT} \approx t_e + \frac{c_a^2 + c_e^2}{2} \cdot \frac{u}{1-u} \cdot t_e
\]

| Simbol | Nama | Di app |
|--------|------|--------|
| **t_e** | Mean process time | Waktu 1 zona di stasiun |
| **u** | Utilisasi | Dari simulasi |
| **c_e** | CV process time | Dari variability (tanpa var → 0) |
| **c_a** | CV kedatangan | T1 ≈ 0; hilir ≈ c_e hulu |
| **V** | \((c_a^2 + c_e^2)/2\) | Faktor variability |
| **U** | \(u/(1-u)\) | Meledak saat u → 1 |

**VUT:** naiknya **V**ariability, **U**tilisasi, atau **T** process time menaikkan CT.  
Tanpa variability → wait = 0 → **CT = t_e**.

### 11.2 Grafik di app

| Grafik | Isi |
|--------|-----|
| **CT vs u̅** | Kurva keluarga V; titik = utilisasi **gabungan** (rata-rata tim) |
| **CT Kingman vs CT amati** | Per stasiun T1…T5 |
| **Perbandingan** | Titik operasi skenario di bidang CT–u̅ |

### 11.3 Catatan

Kingman mengasumsikan antrian **stasioner**. Proyek berhingga + batch handoff bisa beda numerik dari prediksi; gunakan untuk **arah** (var/u naik → antrian mahal), bukan ramalan absolut.

---

## 12. Inventory vs fill rate

### 12.1 Teori

Tradeoff klasik **service–inventory** (inventory theory / Factory Physics):

| Sumbu | Arti |
|-------|------|
| **X — Fill rate** | % permintaan terpenuhi **langsung dari stok** (tanpa stockout) |
| **Y — Inventory** | Rata-rata WIP di buffer |

Semakin tinggi target fill rate (mendekati 100%), inventory yang dibutuhkan **naik tajam** (diminishing returns). Variability tinggi → butuh lebih banyak inventory untuk fill rate yang sama.

### 12.2 Definisi di app

- **Inventory** = rata-rata isi buffer B1…B4.  
- **Fill rate** (analog tipe-2) ≈ `produksi / (produksi + idle)` pada tim hilir.  
- Kurva teoritis base-stock (unit normal loss) sebagai backdrop.  
- Titik sistem + penanda per buffer B1…B4.

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
| 2 | Sama, batch 1 | Durasi↓, WIP↓ |
| 3 | T1 Rendah, lain Normal | Idle hilir; utilisasi T2–T5 turun |
| 4 | Variability sedang semua | LOB patah; **W_opt > W_min**; CT naik |
| 5 | Perbandingan 5× var | Durasi, CT, W_opt vs level var |
| 6 | Little's Law + slider CONWIP | Prediksi TH/CT berubah di bawah slider |
| 7 | Takt plan zona 20/40/80 | Durasi & LOB vs jumlah zona |

Diskusi kunci: *idle = menunggu zona, bukan malas*; *batch = kebijakan serah terima*; *takt = janji irama*; *CONWIP ≈ W_opt menahan inventory*.

---

## 14. Batasan model

- Satu jalur zona, 5 tim tetap; tanpa cuaca, absensi, multitasking eksplisit.  
- Variability = undi kapasitas per zona (bukan Monte-Carlo ratusan faktor).  
- Handoff selalu periode berikutnya (tidak instan).  
- Kingman, kurva FR, dan prediksi CONWIP = pendekatan **stasioner / teoritis** untuk intuisi.  
- Prediksi TH/CT @ CONWIP dari **interpolasi kurva**, bukan re-simulasi penuh dengan kebijakan CONWIP di engine.  
- Cocok untuk **pembelajaran sistem & kebijakan**, bukan penjadwalan proyek 1:1.

---

## 15. Literatur

### Parade of Trades & takt

1. **Tommelein, I. D., Riley, D. R., & Howell, G. A. (1999).** *Parade Game: Impact of Work Flow Variability on Trade Performance.* Journal of Construction Engineering and Management, ASCE.  
2. **Choo, H. J., & Tommelein, I. D. (1999).** *Parade Game.* Technical Report, P²SL, University of California, Berkeley.  
3. **Tommelein, I. D. (2020).** *Takting the Parade of Trades: Use of Capacity Buffers to Gain Work Flow Reliability.* Proc. 28th Annual Conference of the International Group for Lean Construction (IGLC28). https://doi.org/10.24928/2020/0076  

### Factory Physics, Little, Kingman, CONWIP, inventory

4. **Hopp, W. J., & Spearman, M. L.** *Factory Physics* (edisi relevan). — Little's Law, VUT/Kingman, operations curves, **CONWIP**, critical WIP (W0), inventory–service.  
5. **Kingman, J. F. C. (1961).** Pendekatan heavy-traffic untuk waktu tunggu G/G/1 (dasar bentuk VUT).  
6. **Little, J. D. C. (1961).** *A Proof for the Queuing Formula: L = λW.* Operations Research.  
7. **Project Production Institute.** *Little’s Law in Production Systems with Yield Loss.*  
   https://projectproduction.org/journal/littles-law-in-production-systems-with-yield-loss/  

### Takt planning di konstruksi

8. **Lean Construction Institute.** *Takt Time* / Takt planning, steering & control.  
   https://leanconstruction.org/lean-topics/takt-time/  
9. Materi terkait **Takt Production System**, Line of Balance, dan location-based scheduling (LCI & IGLC).

### Pemetaan topik app → acuan

| Topik app | Acuan utama |
|-----------|-------------|
| Variability & parade | Tommelein et al. (1999); Choo & Tommelein (1999) |
| Takt & zonasi | LCI Takt Time; Tommelein (2020) (latar teoritis) |
| WIP = TH × CT | Little (1961); Hopp & Spearman; PPI (konteks y=1) |
| W_min, W_opt, CONWIP | Hopp & Spearman (Factory Physics) |
| CT vs u, VUT | Kingman; Hopp & Spearman |
| Inventory–fill rate | Inventory theory / Factory Physics |
| LOB | Praktik penjadwalan berulang + literatur parade |

---

*Parade Tim Kerja — manual zone-flow untuk pembelajaran Lean Construction & Project Production.*  
*Diselaraskan dengan tab Simulasi, Perbandingan, Takt plan, dan suite analisis (LOB, Buffer/WIP, Utilisasi, Little's Law + CONWIP, Kingman, Inventory/FR).*
