# Landing page Vercel (static)

Simulasi interaktif: https://parade-tim-kerja.streamlit.app/  
Landing statis: folder `public/` (bukan Python).

## Pengaturan Vercel (penting)

| Setting | Nilai |
|---------|--------|
| Framework Preset | **Other** |
| Root Directory | `.` (repo root) |
| Install Command | *otomatis dari vercel.json* (skip) |
| Build Command | *skip* |
| Output Directory | **`public`** |

Jangan pilih preset **Python** — app Streamlit tidak di-host di Vercel.

## Redeploy

Push ke `main` memicu redeploy jika repo sudah di-import di Vercel.
