# Manual Belajar — Parade of Trades

**Panduan untuk mahasiswa & peserta workshop**  
Simulasi Lean Construction interaktif berbasis situs web.

| | |
|---|---|
| Untuk siapa | Mahasiswa teknik sipil / manajemen konstruksi, peserta pelatihan Lean |
| Cara pakai | Buka situs simulasi di browser — **tidak perlu coding** |
| Dasar ilmiah | Tommelein, Riley & Howell (1999); Choo & Tommelein (1999); Tommelein (2020) |
| Konteks lokal | Floor cycle beton Indonesia (5 trade berurutan) |

---

## Daftar isi

1. [Tujuan pembelajaran](#1-tujuan-pembelajaran)
2. [Apa itu Parade of Trades?](#2-apa-itu-parade-of-trades)
3. [Cara membuka simulasi](#3-cara-membuka-simulasi)
4. [Mengenal tampilan situs](#4-mengenal-tampilan-situs)
5. [Aturan main (cara kerja model)](#5-aturan-main-cara-kerja-model)
6. [Pilihan capacity (dadu virtual)](#6-pilihan-capacity-dadu-virtual)
7. [Cara memakai setiap tab](#7-cara-memakai-setiap-tab)
8. [Cara membaca metrik & grafik](#8-cara-membaca-metrik--grafik)
9. [Latihan terarah (ikuti urutan ini)](#9-latihan-terarah-ikuti-urutan-ini)
10. [Takt planning & capacity buffer](#10-takt-planning--capacity-buffer)
11. [Replikasi: kenapa satu run tidak cukup?](#11-replikasi-kenapa-satu-run-tidak-cukup)
12. [Menyimpan & melaporkan hasil](#12-menyimpan--melaporkan-hasil)
13. [Pertanyaan diskusi & refleksi](#13-pertanyaan-diskusi--refleksi)
14. [FAQ mahasiswa](#14-faq-mahasiswa)
15. [Glosarium singkat](#15-glosarium-singkat)
16. [Referensi untuk dibaca lanjut](#16-referensi-untuk-dibaca-lanjut)

---

## 1. Tujuan pembelajaran

Setelah memakai simulasi ini, Anda diharapkan mampu:

1. **Menjelaskan** mengapa variability + ketergantungan sekuensial memperlambat proyek, meski rata-rata kapasitas tiap trade sama.
2. **Membedakan** production capacity (mampu) vs production rate aktual (tercapai).
3. **Menginterpretasi** Line of Balance, profil buffer/WIP, utilization, dan idle capacity.
4. **Membandingkan** skenario variability rendah vs tinggi secara terukur (duration, throughput, waste).
5. **Memahami** ide takt + *capacity buffer* (standby): reliability work flow, bukan sekadar “tambah orang”.
6. **Merefleksikan** implikasi ke perencanaan lapangan (hand-off, buffer, Last Planner® / takt plan).

> **Bukan tujuan manual ini:** mengajari pemrograman Python. Fokusnya **belajar konsep lewat eksperimen di situs**.

---

## 2. Apa itu Parade of Trades?

**Parade of Trades** (Parade Game / Dice Game) adalah alat edukasi Lean Construction yang terkenal dari riset **Iris D. Tommelein** dan rekan (UC Berkeley).

### Analogi sederhana

Bayangkan lima regu kerja berbaris seperti **parade**:

```text
Bekisting → Tulangan → Cor beton → Bongkar bekisting → Finishing
```

Regu di belakang **hanya bisa bekerja** jika regu di depannya sudah menyerahkan pekerjaan (hand-off).  
Kapasitas tiap regu **tidak selalu sama tiap minggu** — kadang “beruntung”, kadang “kurang” (seperti lemparan dadu).

Akibatnya:

- Proyek bisa **lebih lama** dari yang diharapkan dari rata-rata capacity saja  
- Muncul **antrian pekerjaan (WIP / buffer)** di antara trade  
- Ada **capacity terbuang** (idle) karena menunggu  

### Proses di simulasi ini (floor cycle Indonesia)

| Urutan | Trade |
|--------|--------|
| 1 | Pemasangan Bekisting |
| 2 | Pemasangan Tulangan |
| 3 | Pengecoran Beton |
| 4 | Pembongkaran Bekisting |
| 5 | Finishing Lantai |

Default: **100 zona** kerja. Mean capacity tiap trade: **5 unit per periode**.

### Pesan Lean yang ingin diuji sendiri

> Mengurangi *variability* work flow antar trade dapat **memperpendek proyek** dan **mengurangi waste**, tanpa harus menaikkan mean capacity.

---

## 3. Cara membuka simulasi

1. Buka **tautan situs** yang dibagikan dosen / repository GitHub (halaman Streamlit atau GitHub Pages yang diarahkan ke app).
2. Tunggu halaman dimuat (header ilustrasi + beberapa tab di bagian atas).
3. Mulai dari tab **🎮 Single run** atau ikuti [Latihan terarah](#9-latihan-terarah-ikuti-urutan-ini).

**Yang Anda butuhkan:** browser modern (Chrome, Edge, Firefox, Safari) dan koneksi internet.  
**Yang tidak diperlukan:** instal Python, terminal, atau skill coding.

> Jika situs di-host lewat Streamlit Community Cloud / layanan sejenis, cukup klik link — tidak ada langkah instalasi di komputer Anda.

---

## 4. Mengenal tampilan situs

### Sidebar kiri (pengaturan global)

| Kontrol | Arti untuk pembelajaran |
|---------|-------------------------|
| **Total work units (zona)** | Besar “proyek mini” (default 100 zona). Naikkan/turunkan untuk eksperimen. |
| **Fix random seed** | Jika aktif, hasil **bisa diulang** (cocok untuk tugas & bandingkan skenario “adil”). |
| **Seed** | Nomor penentu urutan “keberuntungan” dadu. Contoh: 42. |
| **Number of trades** | Jumlah tahap berurutan (default 5 = floor cycle penuh). |

**Tips tugas:** tulis seed yang Anda pakai di laporan agar dosen bisa mereproduksi hasil Anda.

### Tab di bagian atas

| Tab | Kapan dipakai |
|-----|----------------|
| 🎮 **Single run** | Eksperimen satu skenario; langkah demi langkah (Step) atau langsung Run |
| ⚖️ **Compare 2** | Bandingkan dua setting berdampingan (mis. 5/5 vs 1/9) |
| 📊 **Preset sweep** | Lihat tren semua tingkat variability sekaligus |
| ⏱️ **Takt 2020** | Belajar capacity buffer (paper Tommelein 2020) |
| 🔁 **Replications** | Banyak percobaan → rata-rata & sebaran (lebih “ilmiah”) |
| 📖 **Manual** | Panduan belajar ini |
| ℹ️ **About** | Ringkasan konsep & referensi |

---

## 5. Aturan main (cara kerja model)

Pahami ini agar grafik tidak “ajaib”.

### Setiap periode (misalnya “satu minggu”)

1. Trade diproses **dari hulu ke hilir** (Bekisting dulu, Finishing belakangan).
2. Trade yang belum selesai mendapat **capacity** dari “dadu virtual” 50/50: nilai *low* atau *high*.
3. Yang benar-benar dikerjakan:

```text
aktual = minimum dari (capacity, sediaan dari trade di depan, sisa pekerjaan)
```

4. Hasil trade hulu **langsung bisa** diambil trade hilir **di periode yang sama** (update buffer berurutan).
5. Proyek selesai ketika trade **terakhir** menyelesaikan semua zona.

### Istilah penting

| Istilah | Bahasa sederhana |
|---------|------------------|
| **Capacity** | Mampu berapa unit periode ini (hasil dadu) |
| **Production / aktual** | Berapa yang benar-benar selesai |
| **Buffer / WIP** | Pekerjaan menumpuk di antara dua trade |
| **Idle capacity** | Capacity yang tidak terpakai (sering karena menunggu) |
| **Utilization** | Persentase capacity yang benar-benar dipakai |

---

## 6. Pilihan capacity (dadu virtual)

Semua preset di bawah punya **rata-rata 5**. Yang beda hanya **seberapa liar** naik-turunnya.

| Nama di situs | Angka (low/high) | Makna belajar |
|---------------|------------------|---------------|
| No variability | 5/5 | Ideal — selalu 5 |
| Low | 4/6 | Sedikit goyah |
| Medium | 3/7 | Goyah sedang |
| High | 2/8 | Goyah kuat |
| Very high | 1/9 | Sangat tidak andal |
| Custom | bebas | Eksperimen Anda sendiri |

**Uniform** = semua trade pakai pair yang sama.  
**Per trade** = tiap trade bisa beda (misalnya hulu stabil, hilir berisiko).

---

## 7. Cara memakai setiap tab

### 7.1 Single run — laboratorium utama Anda

1. Pilih **Uniform** atau **Per trade**.
2. Pilih preset (mulai dari *No variability*, lalu *Medium*, lalu *Very high*).
3. (Opsional) aktifkan **takt planning** setelah Anda paham mode klasik.
4. Tombol:
   - **▶ Run** — simulasi sampai selesai  
   - **⏭ Step** — satu periode (bagus untuk memahami hand-off)  
   - **⏩ Finish** — lanjutkan dari Step sampai selesai  
   - **↺ Reset** — ulangi dari nol  
5. Amati: angka metrik → grafik Line of Balance → Buffer → Utilization → tabel trade.
6. Unduh hasil (CSV/Excel) jika diminta untuk laporan.

### 7.2 Compare 2 — “A versus B”

1. Scenario **A**: mis. No variability (5/5).  
2. Scenario **B**: mis. Very high (1/9).  
3. **Run comparison**.  
4. Baca baris **B − A** (selisih duration, idle, peak WIP).  
5. Bandingkan grafik overlay.

### 7.3 Preset sweep — gambaran besar

1. Biarkan semua preset terpilih (atau pilih sebagian).  
2. **Run sweep**.  
3. Lihat tabel: semakin ke *very high*, biasanya duration & idle naik.

### 7.4 Takt 2020 — level lanjut

Setelah paham classic game, buka tab ini untuk membandingkan:

| Skenario | Inti pelajaran |
|----------|----------------|
| **S1** Classic 4/6 | Variability tanpa penanganan khusus |
| **S2** Takt + standby | Commit hand-off minimal; cadangan capacity hanya saat kurang |
| **S3** Die 5/7 | “Tambah capacity” — beda filosofi dari standby |

### 7.5 Replications — level riset mini

Satu Run = **satu kisah acak**.  
Banyak replikasi = **distribusi** (rata-rata, sebaran, risiko terlambat).

Pakai tab ini untuk tugas yang minta “bukan cuma satu seed”.

---

## 8. Cara membaca metrik & grafik

### Kotak metrik di atas

| Metrik | Pertanyaan yang dijawab |
|--------|-------------------------|
| **Duration** | Berapa periode sampai proyek selesai? |
| **vs Ideal** | Seberapa jauh dari “dunia sempurna” (tanpa waste)? |
| **Throughput** | Seberapa cepat zona terselesaikan per periode? |
| **Total Idle** | Berapa banyak capacity terbuang di seluruh parade? |
| **Peak WIP** | Seberapa parah penumpukan antar trade? |
| **Standby used** | (Mode takt) seberapa sering cadangan capacity ikut turun tangan? |

### Line of Balance

- Sumbu X = waktu (periode), Y = kumulatif unit selesai.  
- Tiap garis = satu trade.  
- **Ideal** = garis putus-putus.  
- Jika garis hilir lebih landai / terlambat “nyusul”, variability hulu merambat ke belakang.

### Buffer / WIP

- Naik = hand-off tidak seimbang (hulu lebih “agresif” dari hilir, atau sebaliknya starve).  
- Ideal *No variability* sering hampir datar di nol (aliran mulus).

### Utilization

- 100% = capacity penuh terpakai.  
- Trade **hilir** sering lebih “menderita” saat variability tinggi — bukan karena malas, tapi karena **kelaparan input**.

---

## 9. Latihan terarah (ikuti urutan ini)

Gunakan **seed tetap** (contoh: **42**) dan **100 zona** agar hasil sekelas bisa dibanding.

### Latihan A — Dunia ideal (10 menit)

1. Sidebar: seed 42, units 100, trades 5.  
2. Single run → **No variability (5/5)** → **Run**.  
3. Catat: Duration, Idle, Peak WIP.  
4. **Jawaban yang diharapkan:** duration ≈ 20, idle ≈ 0, WIP ≈ 0.

**Refleksi:** Apa arti “ideal” di sini?

### Latihan B — Variability sedang (10 menit)

1. Ganti ke **Medium (3/7)** → Run (seed tetap 42).  
2. Bandingkan dengan Latihan A: duration? idle? utilization trade terakhir?  
3. Buka grafik Buffer: kapan WIP memuncak?

### Latihan C — Variability ekstrem (10 menit)

1. **Very high (1/9)** → Run.  
2. Amati Line of Balance: siapa yang paling tertinggal?  
3. Tulis 3 kalimat: *apa yang terjadi pada trade hilir?*

### Latihan D — Bandingkan dua dunia (10 menit)

1. Tab **Compare 2**: A = 5/5, B = 1/9.  
2. Run comparison.  
3. Isi tabel di buku catatan:

| | Duration | Idle | Peak WIP |
|--|----------|------|----------|
| A (5/5) | | | |
| B (1/9) | | | |
| Selisih B−A | | | |

### Latihan E — Sweep (5–10 menit)

1. Tab **Preset sweep** → Run.  
2. Apakah pola “makin tinggi variability → makin buruk” konsisten?

### Latihan F — Takt (lanjutan, 15–20 menit)

1. Tab **Takt 2020**, mis. 50 replications.  
2. Bandingkan S1, S2, S3: mana yang lebih **cepat**, mana yang lebih **stabil** (std duration kecil)?  
3. Diskusikan: apakah “lebih cepat rata-rata” selalu lebih baik daripada “lebih andal”?

### Latihan G — Laporan singkat (tugas rumah)

Buat laporan 1–2 halaman:

1. Tujuan & setting (seed, units, skenario).  
2. Tabel hasil (minimal 3 skenario).  
3. Satu grafik (screenshot LOB atau hasil export).  
4. Tiga insight + satu rekomendasi untuk proyek nyata (hand-off / buffer / reliability).

---

## 10. Takt planning & capacity buffer

### Masalah yang dipecahkan

Di game klasik, trade “berjanji” hanya secara rata-rata.  
Di **takt planning**, ada komitmen hand-off yang lebih tegas: misalnya **minimal 5 unit per periode** (jika pekerjaan tersedia).

### Capacity buffer (standby)

Jika “dadu” hanya 4 padahal komitmen 5, sistem memakai **1 unit standby** untuk menutup kekurangan.

Contoh di situs: die **4/6**, takt **5**, standby **1**.

| Roll | Effective | Arti |
|------|-----------|------|
| 4 | 5 | Standby ikut membantu |
| 6 | 6 | Boleh lebih dari takt |

### Bukan sama dengan “tambah capacity terus-menerus”

| Pendekatan | Intuisi |
|------------|---------|
| **Standby (S2)** | Cadangan siap pakai *saat dibutuhkan* → work flow lebih **reliable** |
| **Die lebih besar (S3, mis. 5/7)** | Capacity lebih besar tapi variability tetap lebar → bisa lebih cepat *kadang-kadang*, kurang prediktif |

Ini inti diskusi Tommelein (2020): **standby capacity ≠ asal menambah capacity**.

---

## 11. Replikasi: kenapa satu run tidak cukup?

- Satu seed = satu “nasib” proyek.  
- Proyek nyata penuh ketidakpastian; yang relevan sering **distribusi** (bukan satu angka).  

Di tab **Replications** Anda melihat:

- **mean** — kecenderungan  
- **std** — seberapa tidak stabil  
- **min / max** — skenario terbaik & terburuk dalam sampel  

**Untuk presentasi kelas:** 30–100 replications sudah cukup untuk melihat pola.

---

## 12. Menyimpan & melaporkan hasil

### Di situs

- Tab **Single run** / **Replications** / **Takt 2020**: tombol **unduh CSV atau Excel**.  
- Sidebar & tab Manual: unduh file manual ini.

### Yang perlu dicantumkan di laporan

1. URL / nama situs (atau “Parade of Trades – simulasi web”)  
2. Tanggal akses  
3. **Seed** dan **total zona**  
4. Setting capacity / preset tiap skenario  
5. Apakah takt aktif (takt rate, standby)  
6. Tabel metrik + 1–2 screenshot grafik  
7. Interpretasi (bukan hanya menempel angka)

### Etika akademik

- Boleh memakai simulasi ini untuk tugas & presentasi.  
- Cantumkan bahwa model diilhami **Tommelein et al.** (lihat referensi).  
- Jangan mengklaim ini software resmi UC Berkeley.

---

## 13. Pertanyaan diskusi & refleksi

1. Mengapa mean capacity sama (5) tetapi duration bisa jauh beda?  
2. Siapa yang lebih dirugikan variability: trade hulu atau hilir? Mengapa?  
3. Apakah utilization tinggi di satu trade selalu bagus bagi proyek?  
4. Buffer besar: “aman” atau “waste”? Kapan?  
5. Di lapangan, apa padanan “roll dadu” (cuaca, material, rework, multi-tasking, …)?  
6. Jika Anda manajer proyek, apa yang Anda ubah dulu: **tambah tenaga** atau **stabilkan work flow**?  
7. Bagaimana hubungan simulasi ini dengan *pull planning*, takt time, atau Last Planner®?  
8. Setelah melihat S2 vs S3: kapan Anda memilih reliability daripada kemungkinan selesai lebih awal?

---

## 14. FAQ mahasiswa

**Hasil saya beda dengan teman meski setting sama?**  
Periksa **seed**. Matikan “Fix random seed” juga membuat tiap Run berbeda.

**Tombol Step bilang already complete?**  
Tekan **Reset**, lalu Step lagi.

**Duration ideal 20 — dari mana?**  
100 zona ÷ 5 unit per periode = 20. Itu “dunia tanpa waste”.

**Saya harus install sesuatu?**  
Tidak, selama Anda memakai **situs yang sudah di-deploy**. Manual ini ditulis untuk pengguna situs.

**Boleh ganti jumlah trade / zona?**  
Boleh — itu bagian dari eksperimen. Jelaskan di laporan kenapa Anda mengubahnya.

**Grafik tidak muncul / halaman error?**  
Refresh browser. Jika tetap gagal, laporkan ke dosen/admin hosting (bukan masalah “salah hitung” di sisi Anda).

**Apakah ini game judi?**  
Bukan. Dadu hanya model **ketidakpastian kapasitas** untuk belajar sistem produksi.

---

## 15. Glosarium singkat

| Istilah | Arti singkat |
|---------|----------------|
| **Variability** | Ketidaktetapan output/capacity dari waktu ke waktu |
| **Sequential dependence** | Trade hilir bergantung hand-off trade hulu |
| **Throughput** | Laju penyelesaian unit per waktu |
| **WIP / Buffer** | Pekerjaan dalam proses antar tahap |
| **Idle capacity** | Capacity tersedia tapi tidak terpakai |
| **Starvation** | Tidak bisa kerja karena input kurang |
| **Line of Balance** | Grafik kumulatif progress multi-trade vs waktu |
| **Takt** | Irama/komitmen waktu-kuantitas hand-off |
| **Capacity buffer (standby)** | Cadangan capacity untuk menjaga komitmen takt |
| **Seed** | Angka agar urutan acak bisa diulang |

---

## 16. Referensi untuk dibaca lanjut

1. Tommelein, I.D., Riley, D., and Howell, G.A. (1999).  
   *Parade Game: Impact of Work Flow Variability on Trade Performance.*  
   ASCE Journal of Construction Engineering and Management, 125(5), 304–310.

2. Choo, H.J. and Tommelein, I.D. (1999).  
   *Parade of Trades: A Computer Game for Understanding Variability and Dependence.*  
   Technical Report 99-1, University of California, Berkeley.

3. Tommelein, I.D. (2020).  
   *Takting the Parade of Trades: Use of Capacity Buffers to Gain Work Flow Reliability.*  
   Proc. 28th Annual Conference of the International Group for Lean Construction (IGLC28).  
   https://doi.org/10.24928/2020/0076

4. Halaman P2SL (latar belakang game):  
   https://p2sl.berkeley.edu/parade-of-trades-game-2/

---

## Kredit

- **Konsep game:** Iris D. Tommelein, David Riley, Greg Howell; dokumentasi komputer awal oleh Hyun Jeong (James) Choo (UC Berkeley / P2SL).  
- **Situs simulasi ini:** implementasi edukasi untuk belajar floor cycle beton Indonesia + fitur perbandingan, takt, dan replikasi.  
- **Manual ini:** ditujukan untuk **pengguna situs** (mahasiswa & peserta belajar), bukan panduan pemrograman.

Selamat bereksperimen — biarkan grafik yang meyakinkan Anda, bukan hanya definisi di slide.

*File ini: `MANUAL.md` · juga tampil di tab **📖 Manual** pada situs simulasi.*
