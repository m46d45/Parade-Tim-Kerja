# Manual Belajar — Parade Tim Kerja (Zone-Flow)

**Panduan untuk mahasiswa & peserta workshop**  
Simulasi Lean Construction interaktif: **kecepatan per zona**, **variability per zona**, **batch / one-piece flow**.

| | |
|---|---|
| Untuk siapa | Mahasiswa teknik sipil / manajemen konstruksi, pelatihan Lean |
| Cara pakai | Buka di browser — **tidak perlu coding** |
| Dasar ilmiah | Tommelein, Riley & Howell (1999); Choo & Tommelein (1999); Tommelein (2020) |
| Konteks lokal | Floor cycle beton Indonesia (5 trade berurutan) |
| Model app | **Zone-flow classroom** (bukan dadu bulk multi-zona) |

---

## 1. Tujuan pembelajaran

1. Menjelaskan **kecepatan** sebagai progress pada **satu zona**.
2. Membedakan **tanpa variability** (rate sama tiap zona) vs **dengan variability** (rate diundi **per zona**).
3. Memahami **batch handoff** vs **one-piece flow** dan dampaknya ke LOB.
4. Membaca Line of Balance yang **mulai dari 0** dan **bergeser** antar trade.
5. Membandingkan 2–5 skenario di **Perbandingan** (termasuk 5 level variability).

---

## 2. Model zone-flow (inti app ini)

### Parade floor cycle

```text
Bekisting → Tulangan → Cor → Bongkar bekisting → Finishing
```

### Aturan utama

| Konsep | Arti di simulasi |
|--------|------------------|
| **Kecepatan** | Progress pada **satu zona** per periode (mis. normal = 1 zona/periode) |
| **Tanpa variability** | Setiap zona trade itu memakai rate yang **sama** |
| **Dengan variability** | **Setiap zona** mengundi rate sendiri (mis. medium: ×0.5 atau ×1.5), dikunci sampai zona selesai |
| **Batch handoff** | Zona dikumpulkan dulu; setelah N zona, dilepas ke trade hilir di **periode berikutnya** |
| **One-piece (batch=1)** | Tiap zona langsung dilepas setelah selesai |
| **Default batch** | **4 zona** (standar di sidebar) |

### Kecepatan (profil tetap)

| Profil | Definisi |
|--------|----------|
| Sangat lambat | 1 zona butuh **3** periode |
| Lambat | 1 zona butuh **2** periode |
| Normal | **1** zona / 1 periode |
| Cepat | **2** zona / 1 periode |
| Sangat cepat | **3** zona / 1 periode |

### Variability (faktor × dasar, undi per zona)

| Level | Faktor |
|-------|--------|
| No | ×1.0 tetap |
| Low | ×0.75 atau ×1.25 |
| Medium | ×0.5 atau ×1.5 |
| High | ×0.25 atau ×1.75 |
| Very high | ×0.1 atau ×1.9 |

> **Bukan** model lama “undi 0 atau 3 zona sekaligus”. Variability = **kecepatan zona**, bukan jumlah zona massal.

---

## 3. Membaca Line of Balance (LOB)

- Sumbu X = **periode** (mulai 0)
- Sumbu Y = **zona kumulatif** (mulai 0)
- **Kemiringan** ≈ kecepatan
- Dengan batch/one-piece yang benar, garis T1…T5 **bergeser**, tidak menumpuk jadi satu
- Ideal (garis putus) = bottleneck mean

---

## 4. Cara memakai setiap tab

App fokus **tiga tab** di kelas:

### Simulasi
Atur kecepatan & variability → cek batch di sidebar → **Run**.  
Lihat LOB (mulai dari 0), buffer, utilization, start/finish trade.

### Perbandingan (2–5 skenario)
Pilih jumlah skenario 2–5. Tiap skenario: nama, kecepatan, variability.  
Tombol cepat: **Isi 5 level variability** atau **No vs Medium**.  
Bandingkan duration, idle, WIP, dan LOB trade terakhir.

### Manual
File ini + ringkasan model / build.

---

## 5. Latihan terarah

1. **Batch 4, semua Normal + No var** → T2 start setelah batch 4; LOB bergeser.
2. **Batch 1 (one-piece)** → T2 start periode 2; jarak antar trade = 1 zona.
3. **T1 Medium, lain No var** → T1 lonjak/landai per zona; T2+ tetap menunggu handoff batch.
4. **Perbandingan**: isi 5 level variability → lihat duration naik seiring var.
5. Comparison 2 skenario: No var vs Medium; coba batch 1 vs 4 di sidebar.

---

## 6. FAQ singkat

**Q: Kenapa T2 tidak mulai di periode 1?**  
A: Handoff ke periode berikutnya setelah batch penuh (default 4 zona).

**Q: Kenapa medium tidak lompat +3 zona?**  
A: Rate ×0.5/×1.5 pada **satu zona**, bukan undi 0/3 zona massal.

**Q: Kenapa hanya 3 tab?**  
A: Fokus kelas: eksperimen (Single), bandingkan (Compare), baca panduan (Manual).

---

## 7. Referensi

- Tommelein, Riley & Howell (1999). Parade Game… *J. Mgt. in Engineering*.
- Choo & Tommelein (1999). Space scheduling…
- Tommelein (2020). Takt planning / capacity buffer discussions (P2SL / UC Berkeley).

