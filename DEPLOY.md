# Panduan Deploy — GitHub + Streamlit Community Cloud

Dokumen ini untuk **Anda sebagai pemilik repo** (bukan mahasiswa).  
Mahasiswa hanya membuka link app yang sudah live.

---

## Ringkasan alur

```text
1. Install Git (+ login GitHub)
2. Buat repo di GitHub, push kode
3. Hubungkan repo ke Streamlit Community Cloud
4. Bagikan URL *.streamlit.app ke kelas
```

---

## A. Persiapan akun

1. Akun **GitHub**: https://github.com/signup  
2. Akun **Streamlit Community Cloud**: https://share.streamlit.io  
   - Login dengan **akun GitHub yang sama**  
   - Izinkan akses ke repository saat diminta  

---

## B. Install Git di Windows (jika belum ada)

1. Unduh: https://git-scm.com/download/win  
2. Install dengan opsi default (centang “Git from the command line”).  
3. **Tutup dan buka ulang** PowerShell / Terminal.  
4. Cek:

```powershell
git --version
```

### (Opsional) GitHub CLI

https://cli.github.com/ — memudahkan `gh repo create`.

---

## C. Push proyek ke GitHub

### Opsi 1 — Dari folder proyek (PowerShell)

Ganti `USERNAME` dengan username GitHub Anda.

```powershell
cd C:\Users\m46d4\parade-of-trades

git init
git add .
git status
git commit -m "Initial release: Parade of Trades simulation app"

# Buat repo kosong di github.com → New repository → nama: parade-of-trades (public)
# Lalu:

git branch -M main
git remote add origin https://github.com/USERNAME/parade-of-trades.git
git push -u origin main
```

Browser akan meminta login GitHub (atau Personal Access Token jika password ditolak).

### Opsi 2 — GitHub website + upload

1. github.com → **New repository** → nama `parade-of-trades` → **Public** → Create.  
2. Upload file (atau gunakan GitHub Desktop).  
3. Pastikan file inti ada di root:
   - `app.py`
   - `requirements.txt`
   - `parade_of_trades_*.py`
   - `MANUAL.md`
   - `assets/`

### Opsi 3 — GitHub Desktop

1. Install https://desktop.github.com/  
2. File → Add Local Repository → pilih folder `parade-of-trades`  
3. Publish repository → centang **Public** (disarankan untuk Streamlit gratis)

---

## D. Deploy ke Streamlit Community Cloud

1. Buka https://share.streamlit.io dan login.  
2. Klik **Create app** / **New app**.  
3. Isi:

| Field | Isi |
|-------|-----|
| Repository | `USERNAME/parade-of-trades` |
| Branch | `main` |
| Main file path | `app.py` |
| App URL (opsional) | mis. `parade-of-trades` → `parade-of-trades.streamlit.app` |

4. **Advanced settings** (opsional):
   - Python version: **3.11** atau **3.12** (disarankan)  
5. Klik **Deploy**.  
6. Tunggu log build (install matplotlib, streamlit, openpyxl).  
7. Jika sukses, buka URL `https://….streamlit.app`.

### Jika build gagal

| Gejala | Perbaikan |
|--------|-----------|
| Module not found | Pastikan `requirements.txt` di root repo |
| App file not found | Main file path harus `app.py` (bukan subfolder) |
| Repo private | Streamlit gratis butuh public repo, atau hubungkan plan yang mendukung private |
| Timeout matplotlib | Deploy ulang; jarang, biasanya sukses di retry |

### Secrets

App ini **tidak butuh** API key. Jangan buat `secrets.toml` kecuali nanti Anda menambah fitur berbayar.

---

## E. Setelah live

1. Uji tab: Single run, Manual, Compare 2.  
2. Edit `README.md` — ganti placeholder link app.  
3. Commit & push; Streamlit Cloud **auto-redeploy** pada push ke branch yang sama.  
4. Bagikan ke mahasiswa:
   - Link app  
   - Instruksi: buka tab **Manual** untuk latihan  

### Update app di kemudian hari

```powershell
cd C:\Users\m46d4\parade-of-trades
# edit file...
git add .
git commit -m "Update: deskripsi singkat perubahan"
git push
```

Tunggu 1–3 menit, refresh app.

---

## F. Checklist file untuk cloud

Pastikan di GitHub ada:

- [x] `app.py`  
- [x] `requirements.txt`  
- [x] `parade_of_trades_core.py`  
- [x] `parade_of_trades_plots.py`  
- [x] `parade_of_trades_analysis.py`  
- [x] `MANUAL.md`  
- [x] `assets/header_banner.jpg`  
- [x] `assets/logo_icon.jpg`  
- [x] `.gitignore`  
- [x] `README.md`  

Tidak wajib di cloud: `test_*.py`, folder `output/`.

---

## G. Python requirements (yang dibaca Streamlit Cloud)

```text
matplotlib>=3.7
streamlit>=1.28
openpyxl>=3.1
```

File: `requirements.txt` di root.

---

## H. Troubleshooting cepat

**“Please wait” lama sekali**  
Cold start free tier — tunggu; buka lagi beberapa detik kemudian.

**App sleep / sleep after inactivity**  
Normal di free tier; request pertama membangunkan app.

**Gambar header tidak muncul**  
Pastikan folder `assets/` ikut ter-push (bukan di `.gitignore`).

**Manual kosong**  
Pastikan `MANUAL.md` ada di root (sejajar `app.py`).

---

## Bantuan resmi

- Streamlit Cloud docs: https://docs.streamlit.io/deploy/streamlit-community-cloud  
- GitHub Hello World: https://docs.github.com/en/get-started/quickstart  
