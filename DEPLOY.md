# Panduan Deploy

Dokumen ini untuk **pemilik repo** (bukan mahasiswa).  
Mahasiswa cukup membuka URL live.

## Kanonis (Vercel — app JS)

1. Hubungkan repo GitHub ke [Vercel](https://vercel.com).  
2. Konfigurasi sudah di `vercel.json`:
   - `installCommand`: `cd web && npm ci`
   - `buildCommand`: `cd web && npm run build`
   - `outputDirectory`: `web/dist`
3. Domain produksi: **https://parade-tim-kerja.vercel.app/**
4. Path penting:
   - `/` — simulasi
   - `/kelas/` — animasi kelas

Setelah push ke `main`, Vercel build otomatis.

## Streamlit (redirect / jaring pengaman)

Cloud Streamlit (`parade-tim-kerja.streamlit.app`) mengarahkan ke Vercel.  
UI Streamlit lama: buka URL Streamlit dengan `?legacy=1`.

```bash
streamlit run app.py
```

## Pengembangan lokal (JS)

```bash
cd web
npm install
npm run dev
```

Lihat juga [docs/MIGRATION-JS.md](docs/MIGRATION-JS.md).
