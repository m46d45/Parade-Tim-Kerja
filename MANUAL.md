# Manual — Parade Tim Kerja

**Simulasi parade tim kerja pekerjaan pengecoran lantai beton**  
Panduan untuk mahasiswa, dosen, dan peserta workshop Lean Construction.

| | |
|---|---|
| Aplikasi | **Parade Tim Kerja** (Streamlit) |
| Untuk siapa | Teknik sipil / manajemen konstruksi — **tanpa coding** |
| Konteks | Floor cycle beton: 5 tim berurutan di zona kerja |
| Dasar ilmiah | Tommelein, Riley & Howell (1999); Choo & Tommelein (1999); Tommelein (2020) |
| Default | Total zona **40** · Seed **12345** · Batch handoff **4** · 5 tim (tetap) |

---

## 1. Apa yang disimulasikan?

Proyek lantai beton dikerjakan **zona demi zona** oleh lima tim berurutan:

```text
T1 Pemasangan Bekisting
  → T2 Pemasangan Tulangan
    → T3 Pengecoran Beton
      → T4 Pembongkaran Bekisting
        → T5 Finishing Lantai
```

**Aturan lapangan (model zone-flow):**

1. Satu zona hanya bisa dikerjakan satu tim pada satu waktu.
2. Tim hilir hanya boleh masuk ke zona yang **sudah dilepas** oleh tim hulu.
3. Pelepasan zona mengikuti **ukuran batch handoff** (bukan “langsung kapan saja”).
4. Setelah batch penuh, handoff ke tim berikutnya terjadi di **periode berikutnya** (ada jeda satu periode) — seperti antrian lokasi kerja di lapangan.

Animasi banner di atas halaman mencontohkan handoff **one-piece** (batch = 1): T1 selesai di Zona 1 lalu pindah; T2 masuk Zona 1; dan seterusnya sampai T5. Zona yang sudah dilalui T5 menampilkan blok **✓ Selesai**.

---

## 2. Konsep penting

### 2.1 Zona dan periode

| Istilah | Arti |
|---------|------|
| **Zona** | Satuan lokasi kerja (mis. pelat / bay). Total zona diatur di sidebar (default 40). |
| **Periode** | Satuan waktu simulasi (bisa dibayangkan sebagai “hari” atau “shift”). |
| **Kumulatif** | Jumlah zona yang sudah diselesaikan suatu tim (mulai dari **0**). |

### 2.2 Kapasitas produksi (zona/periode)

Kapasitas = seberapa cepat **satu tim** menyelesaikan **satu zona**.

| Profil di app | Arti |
|---------------|------|
| Sangat rendah | 1 zona butuh **3** periode |
| Rendah | 1 zona butuh **2** periode |
| Normal | **1** zona per 1 periode |
| Tinggi | **2** zona per 1 periode |
| Sangat tinggi | **3** zona per 1 periode |

Tanpa variability, kapasitas itu **tetap** untuk setiap zona yang dikerjakan tim tersebut.

### 2.3 Variability (perubahan kapasitas per zona)

Variability = kapasitas **bisa berubah tiap kali tim mulai zona baru** (diundi sekali per zona, lalu dikunci sampai zona itu selesai).

| Level | Rentang (× kapasitas dasar) | Gambaran |
|-------|------------------------------|----------|
| Tanpa variability | ×1,0 tetap | Semua zona sama cepat |
| Rendah | ×0,75 atau ×1,25 (**±25%**) | Sedikit goyang |
| Sedang | ×0,5 atau ×1,5 (**±50%**) | Cukup terasa |
| Tinggi | ×0,25 atau ×1,75 (**±75%**) | Sangat goyang |
| Sangat tinggi | ×0,1 atau ×1,9 (**±90%**) | Ekstrem |

> Bukan model “undi 0 atau 3 zona sekaligus”. Variability mengubah **laju progress di zona**, bukan lompat massal.

### 2.4 Batch handoff vs one-piece flow

| Batch | Perilaku |
|-------|----------|
| **1** (one-piece) | Tiap zona selesai langsung dilepas ke tim hilir (periode berikutnya). |
| **2, 3, 4, 5** | Zona dikumpulkan dulu; baru dilepas setelah batch penuh. Default **4**. |
| Sisa di akhir proyek | Sisa batch (mis. 40 zona, batch 4 → habis pas; jika tidak habis dibagi) **tetap dilepas** agar proyek tidak macet. |

**Dampak tipikal (semua Normal, tanpa var, 40 zona, seed 12345):**

| Batch | Durasi (periode) | Puncak WIP per buffer |
|-------|------------------|------------------------|
| 1 | 44 | 1 |
| 4 | 56 | 4 |

Batch lebih besar → handoff lebih jarang → tim hilir sering **menunggu** → proyek lebih lama, WIP di buffer lebih tinggi.

### 2.5 Idle dan utilisasi

| Istilah | Arti di app |
|---------|-------------|
| **Idle** | Kapasitas yang “terbuang” karena tim sudah mulai kerja tetapi **tidak ada zona** yang siap (menunggu handoff / kelaparan buffer). |
| **Utilisasi** | Produksi ÷ kapasitas efektif (0–100%). Tim yang terus bekerja tanpa menunggu ≈ 100%. Tim yang sering mengantri zona → utilisasi turun. |
| **Buffer / WIP** | Zona yang sudah dilepas tim hulu tetapi belum dikerjakan tim hilir (persediaan kerja di antara dua tim). |

---

## 3. Navigasi aplikasi

### 3.1 Sidebar (kiri)

| Kontrol | Fungsi |
|---------|--------|
| **Total zona** | Ukuran proyek (default 40). |
| **Kunci seed acak** + **Seed** | Reproduktibilitas undian variability (default 12345). |
| **Ukuran batch handoff** | 4 (standar), 5, 3, 2, atau 1 (one-piece). Berlaku di tab Simulasi; di Perbandingan tiap skenario bisa beda. |

Jumlah tim **tetap 5** (floor cycle).

### 3.2 Tiga tab utama

1. **Simulasi** — satu skenario, atur tim, lihat LOB / Buffer / Utilisasi  
2. **Perbandingan** — 2–5 skenario berdampingan  
3. **Manual** — dokumen ini (+ unduh `.md`)

---

## 4. Tab Simulasi

### 4.1 Pengaturan tim

- **Seragam (semua tim sama)** — satu set kapasitas + variability untuk T1…T5.  
- **Per tim (bisa berbeda)** — tiap tim (Bekisting … Finishing) punya kapasitas & variability sendiri.

Lalu tekan **Jalankan**. **Atur ulang** menghapus hasil di memori sesi.

### 4.2 Hasil: metrik

| Metrik | Arti singkat |
|--------|----------------|
| Durasi | Periode sampai T5 selesai semua zona |
| vs Ideal | Selisih terhadap durasi ideal (bottleneck + jeda pipeline) |
| Throughput | Zona / periode (sistem) |
| Idle total | Jumlah idle semua tim |
| Puncak WIP | Maksimum total buffer serentak |
| Batch | Ukuran handoff yang dipakai run ini |

Tabel **Metrik per tim**: produksi, idle, mulai, selesai, waktu di lapangan.

### 4.3 Sub-tab grafik

#### Line of Balance (LOB)

- Sumbu X = **periode** (mulai 0)  
- Sumbu Y = **zona kumulatif** (mulai 0)  
- Setiap warna = satu tim  
- **Kemiringan** ≈ kapasitas  
- Garis **bergeser** (tidak menumpuk) karena handoff + jeda periode  
- Ada plot detail awal + plot seluruh proyek  

#### Buffer / WIP

- Grafik **per buffer** B1…B4 (T1→T2, T2→T3, …)  
- Versi **stacked** = komposisi total WIP  
- Tabel **puncak WIP** per buffer  
- Batch 4 tanpa var → puncak sering **4**; batch 1 → puncak **1**

#### Utilisasi

- Batang % utilisasi per tim  
- Tabel: produksi, kapasitas efektif, idle, utilisasi %  
- Coba: T1 **Rendah** (lambat), tim lain Normal → T2–T5 utilisasi turun (banyak menunggu)

### 4.4 Latihan cepat (Simulasi)

1. Semua **Normal**, **tanpa variability**, batch **4** → catat durasi & puncak WIP.  
2. Ubah batch ke **1** → durasi lebih pendek, WIP lebih tipis.  
3. Batch 4 lagi; T1 **Rendah**, lain Normal → LOB T1 lebih landai; idle/utilisasi hilir memburuk.  
4. Semua Normal, variability **Sedang** → garis patah-patah; idle & WIP naik vs tanpa var.

---

## 5. Tab Perbandingan

Bandingkan **2 sampai 5** skenario dengan zona & seed yang sama (dari sidebar).

### 5.1 Kontrol

| Kontrol | Fungsi |
|---------|--------|
| **Jumlah skenario** | 2–5 kolom pengaturan |
| Per skenario | Kapasitas, variability, **batch handoff sendiri** |
| **5× variability** | Isi 5 skenario: tanpa var → sangat tinggi (batch = sidebar) |
| **Tanpa var vs Sedang** | 2 skenario, batch sidebar |
| **Batch 1 vs 4** | One-piece vs batch 4 (tanpa variability) |
| **Hapus hasil** | Bersihkan hasil run |
| **Jalankan perbandingan** | Hitung semua skenario |

### 5.2 Hasil

- **Ringkasan** tabel (durasi, idle, puncak WIP, throughput, …) diurut durasi naik  
- Sub-tab:
  - **Line of Balance** — kurva **tim terakhir** (penyelesaian proyek) per skenario, mulai (0,0)  
  - **Buffer / WIP** — total WIP antar-tim vs periode, per skenario  
  - **Utilisasi** — % utilisasi T1…T5 dikelompokkan per skenario  
- **Detail tim satu skenario** — tabel metrik satu skenario terpilih  

### 5.3 Latihan cepat (Perbandingan)

1. **Batch 1 vs 4** → lihat LOB & WIP: one-piece lebih cepat, WIP lebih rendah.  
2. **5× variability** → lihat durasi dan utilisasi memburuk seiring level var.  
3. Campur: S1 Normal tanpa var batch 4; S2 Normal var tinggi batch 4; S3 Normal tanpa var batch 1.

---

## 6. Cara membaca hasil (ringkas)

```text
Kapasitas ↑  →  kemiringan LOB curam, durasi ↓ (jika tidak dihambat handoff)
Variability ↑  →  LOB patah-patah, idle ↑, WIP ↑, durasi biasanya ↑
Batch ↑  →  handoff jarang, WIP puncak ↑, tim hilir sering idle, durasi ↑
Batch = 1  →  aliran zona paling mulus (one-piece), WIP tipis
```

**Ideal (garis putus di LOB)** = acuan “semua mulus tanpa antrian berlebih”. Semakin jauh hasil dari ideal, semakin mahal “biaya” variabilitas + kebijakan batch.

---

## 7. Tips kelas / workshop

1. Mulai **tanpa variability**, batch 4, Normal — pahami LOB bergeser.  
2. Ubah **hanya batch** (1 vs 4) — isolasi efek one-piece.  
3. Baru masukkan **variability** — isolasi efek ketidakpastian.  
4. Kunci **seed** agar undian bisa diulang di layar yang sama.  
5. Minta peserta menuliskan: *apa yang membuat idle?* (menunggu zona, bukan “malas”).  
6. Diskusi lapangan: batch di app ≈ “serah terima area tiap N zona / N unit”.

---

## 8. Batasan model (agar tidak overclaim)

- Satu jalur zona, 5 tim tetap, tanpa cuaca/absensi/multitasking eksplisit.  
- Variability = undi kapasitas per zona (bukan full Monte-Carlo ratusan faktor).  
- Handoff selalu **periode berikutnya** setelah batch lepas (tidak ada handoff instan).  
- Cocok untuk **pemahaman sistem & diskusi kebijakan**, bukan penjadwalan proyek nyata 1:1.

---

## 9. Referensi

1. Tommelein, I. D., Riley, D. R., & Howell, G. A. (1999). *Parade Game: Impact of Work Flow Variability on Trade Performance.* Journal of Construction Engineering and Management.  
2. Choo, H. J., & Tommelein, I. D. (1999). *Parade Game.* Technical Report, University of California, Berkeley.  
3. Tommelein, I. D. (2020). *Takting the Parade of Trades.* Proc. 28th Annual Conference of the International Group for Lean Construction (IGLC).  

---



---

## 11. Little's Law (analisis tambahan)

Dasar: hubungan klasik produksi

```text
WIP  =  TH  ×  CT
```

| Simbol | Nama | Arti di Parade Tim Kerja |
|--------|------|-------------------------|
| **TH** | Throughput | Zona selesai proyek per periode = *total zona ÷ durasi* |
| **WIP** | Work-In-Process | (1) **Pipeline**: zona sudah dikerjakan T1 tetapi belum selesai di T5; (2) **Buffer**: jumlah antrian antar-tim |
| **CT** | Cycle time | Waktu tinggal rata-rata ≈ **WIP ÷ TH** (periode) |

### Bentuk klasik vs yield loss

Artikel [Little’s Law in Production Systems with Yield Loss](https://projectproduction.org/journal/littles-law-in-production-systems-with-yield-loss/) (Project Production Institute) membahas perluasan bila ada **kehilangan hasil (yield loss)** di tiap tahap.

| | Model app ini | Jika ada yield loss |
|--|---------------|---------------------|
| Yield per tahap yᵢ | **yᵢ = 1** (tidak ada scrap) | 0 < yᵢ ≤ 1 |
| Bentuk Little | **WIP = TH × CT** klasik | Perlu TH / CT “yielded” vs “observed” |
| TH akhir | = TH sistem (semua zona selesai finishing) | TH_end = TH₀ × Y, Y = ∏ yᵢ |

Di app ini **tidak ada yield loss**, jadi bentuk klasik langsung dipakai. Cek numerik: **TH × CT ≈ WIP rata-rata**.

### Di mana di app?

- Tab **Simulasi** → sub-tab **Little's Law** (setelah Jalankan)  
- Tab **Perbandingan** → kolom TH / WIP⌀ / CT + sub-tab **Little's Law**

### Cara baca di kelas

1. Naikkan **batch** → biasanya WIP↑ dan CT↑ (meski TH turun karena durasi lebih panjang).  
2. Naikkan **variability** → WIP dan CT cenderung naik (antrian lebih liar).  
3. **One-piece (batch=1)** → WIP lebih tipis, CT lebih pendek, TH lebih tinggi (proyek lebih cepat).

> Intuisi Factory Physics: *untuk throughput yang sama, CT proporsional terhadap WIP* — kurangi WIP (aliran lebih ramping) untuk mempercepat cycle time.


## 10. Pemecahan masalah singkat

| Gejala | Coba |
|--------|------|
| Hasil beda tiap buka | Nyalakan **Kunci seed acak** |
| Logo / UI lama | Muat ulang paksa (Ctrl/Cmd+Shift+R) |
| Simulasi lama / error max periode | Turunkan total zona, atau hindari kapasitas sangat rendah + var sangat tinggi bersamaan |
| Garis LOB menumpuk | Pastikan batch & model zone-flow terbaru; handoff tidak instan |
| Utilisasi semua 100% | Normal jika seimbang tanpa var; coba T1 lebih lambat atau naikkan variability |

---

*Parade Tim Kerja — manual zone-flow untuk pembelajaran Lean Construction.*  
*Isi diselaraskan dengan perilaku aplikasi terbaru (kapasitas, variability per zona, batch handoff, LOB, Buffer/WIP, Utilisasi).*
