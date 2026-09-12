# RUNBOOK — buat Google Form paper KoNTekS20

Instruksi untuk Grok bot yang punya akses Google Forms + Google Drive.
Kerjakan persis. Jangan menambah pertanyaan. Jangan menggabung dua form.

## Tujuan

Dua Google Form anonim = aliran data kedua naskah *Parade Tim Kerja*
(KoNTekS20 §3.6 dan §4.5), sesi ICE Center 19 September 2026 08.00–09.30 WIB.

Bukan Form Data Diri, bukan Join WAG, bukan Presensi LMS ICE.

## Simpan di sini — wajib

Folder Drive yang sudah ada (jangan buat folder baru):

- Nama: `ICE-19-Sep-2026-Form-Paper`
- ID: `1rWCKfktvQsI9RqcuKDcNjBWflwbHAL69`
- URL: https://drive.google.com/drive/folders/1rWCKfktvQsI9RqcuKDcNjBWflwbHAL69
- Parent: `KERJAAN / KoNTekS / 2026 - KoNTekS 20`
  ID parent: `1xVJm12HsqtXGyqadMzIaI-X-fGGwDwgL`

Di folder itu taruh:
1. Google Form 1
2. Google Form 2
3. Spreadsheet respons Form 1
4. Spreadsheet respons Form 2
5. Satu file teks `TAUTAN-FORM.txt` berisi URL isi + URL edit kedua form

Pemilik form = akun Drive user (Muhamad Abduh), bukan akun bot jika bisa dihindari.

## Pengaturan yang sama untuk kedua form

- Collect email addresses: **OFF**
- Limit to 1 response: **OFF** (peserta daring bisa ganti perangkat)
- Restrict to users in organization: **OFF** (tanpa login Google)
- Show progress bar: OFF
- Shuffle questions: OFF
- Show link to submit another response: OFF
- See summary charts and text responses: OFF
- Presentation confirmation: singkat, tanpa angka hasil simulasi
- Bahasa: Indonesia
- Quiz mode: OFF
- Sharing responden: **Anyone with the link can respond**
- Sharing editor: hanya pemilik

Jangan tanya nama, email, instansi, peran, NIM, nomor peserta.

---

## FORM 1 — sebelum angka di layar

Judul persis:
`Parade Tim Kerja — Form 1 (sebelum simulasi)`

Deskripsi persis:
`Isian anonim untuk naskah KoNTekS20. Tidak perlu nama atau email. Isi sebelum simulasi dijalankan. Bukan presensi ICE.`

Konfirmasi setelah kirim:
`Terima kasih. Tunggu instruksi fasilitator. Jangan isi Form 2 sekarang.`

### F1.1 — pilihan ganda, wajib, satu jawaban
Jika finishing terlambat, siapa yang paling mungkin Anda salahkan dulu?

- Tim finishing (tim terakhir)
- Tim di hulu
- Manajer proyek / penjadwalan
- Aturan serah terima antar tim
- Belum bisa menunjuk

### F1.2 — pilihan ganda, wajib, satu jawaban
Jika proyek molor, apa yang pertama Anda lihat?

- Tanggal akhir / milestone / persentase selesai
- Siapa yang idle atau mengantri zona
- Utilisasi tiap tim
- Ukuran batch serah terima
- Belum bisa menunjuk

### F1.3 — pilihan ganda, wajib, satu jawaban
“Kalau semua tim kelihatan sibuk, proyek mestinya tidak molor.”

- Setuju
- Ragu
- Tidak setuju

### F1.4 — pilihan ganda, wajib, satu jawaban
“Kalau kapasitas rata-rata tiap tim sama, durasi proyek mestinya sama.”

- Setuju
- Ragu
- Tidak setuju

Spreadsheet respons: `Respons-Form-1-Parade-Tim-Kerja` di folder yang sama.

---

## FORM 2 — sesudah tangga skenario

Judul persis:
`Parade Tim Kerja — Form 2 (sesudah simulasi)`

Deskripsi persis:
`Isian anonim untuk naskah KoNTekS20. Tidak perlu nama atau email. Isi setelah tangga lima tingkat, batch 1 vs 4, dan lokasi sumber. Bukan presensi ICE. Satu kalimat di butir terakhir boleh dikutip secara anonim.`

Konfirmasi setelah kirim:
`Terima kasih. Isian ini anonim.`

### F2.1 — pilihan ganda, wajib, satu jawaban
Setelah lima tingkat variabilitas (kapasitas rata-rata sama): kapasitas rata-rata sama menghasilkan durasi sama?

- Tetap setuju
- Jadi ragu
- Tidak setuju

### F2.2 — pilihan ganda, wajib, satu jawaban
Batch 4 vs batch 1 tanpa variabilitas paling tepat dibaca sebagai:

- Kesalahan tim hilir
- Aturan melepas pekerjaan yang menahan tim berikutnya
- Variabilitas / dadu
- Tidak mengubah apa pun

### F2.3 — pilihan ganda, wajib, satu jawaban
Variabilitas ±90% hanya di T1 atau hanya di T5, dibanding di kelima tim:

- Satu tim bermasalah cukup meruntuhkan kalender
- Satu sumber lebih ringan; yang merusak adalah ketidakrataan di sepanjang rantai
- Yang harus diobati tetap finishing
- Belum jelas

### F2.4 — pilihan ganda, wajib, satu jawaban
Setelah sesi, jika finishing telat, siapa/apa yang Anda lihat dulu?

- Tim finishing
- Aliran / serah terima / ketidakrataan di hulu
- Tanggal akhir saja
- Belum berubah

### F2.5 — paragraf, tidak wajib
Satu kalimat yang boleh dikutip secara anonim di naskah. Boleh kosong.

Spreadsheet respons: `Respons-Form-2-Parade-Tim-Kerja` di folder yang sama.

---

## Yang tidak boleh ditambah

- Butir persetujuan terpisah / izin publikasi nama
- Demografi, peran, instansi, email
- Likert 5 titik
- Pertanyaan Little, Kingman, takt, buffer
- Satu form dengan dua section sebagai pengganti dua form
- Dummy URL

## Output yang harus dikembalikan ke user

1. URL isi Form 1 (responden)
2. URL edit Form 1
3. URL sheet Respons-Form-1
4. URL isi Form 2 (responden)
5. URL edit Form 2
6. URL sheet Respons-Form-2
7. Konfirmasi: collect email OFF, anyone-with-link can respond, file ada di folder `1rWCKfktvQsI9RqcuKDcNjBWflwbHAL69`

Jangan menyunting deck PPTX di langkah ini. Tautan slide 3 dan 20 menyusul setelah URL hidup ada.
