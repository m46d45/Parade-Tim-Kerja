# Landing page Vercel

Halaman statis di root (`index.html`) untuk deploy ke **Vercel**.  
Simulasi interaktif tetap di **Streamlit Cloud**: https://parade-tim-kerja.streamlit.app/

## Deploy (dashboard — disarankan)

1. Buka https://vercel.com/new  
2. Import repo **m46d45/Parade-Tim-Kerja**  
3. Framework Preset: **Other**  
4. Build Command: *(kosong)*  
5. Output Directory: *(kosong / `.`)*  
6. Root Directory: `.`  
7. Deploy  

Vercel akan menyajikan `index.html` + folder `assets/`.

## Catatan

- File `app.py` / Python **tidak** dijalankan di Vercel.  
- Streamlit Cloud tetap memakai `app.py` seperti biasa (abaikan `index.html`).  
