# Smash Angin — Badminton Manager (smashangin.cloud)

Repo kolaborasi untuk situs **smashangin.cloud** — badminton manager komunitas Smash Angin.

## Struktur file

- `index.html` — halaman yang tayang di smashangin.cloud (build terbaru).
- `v01.html` … `v19.html` — arsip versi pengembangan. Tanda `(stable)` = versi yang pernah dipakai stabil di live. Versi terakhir: **v19.html**.
- `logo-*.png` / `logo-*.jpg` — aset logo.
- `.htaccess`, `.user.ini`, `php.ini` — konfigurasi hosting cPanel (jangan diubah kecuali paham; `.htaccess` memuat redirect HTTPS + aturan DirectoryIndex).

## Cara ikut mengembangkan

1. Clone: `git clone https://github.com/benxt13/smash-angin.git`
2. Buka versi terakhir (`v19.html`) di browser untuk melihat kondisi sekarang.
3. Kerja di file versi BARU — mis. salin `v19.html` → `v20.html` — jangan edit `index.html` langsung; `index.html` adalah file yang tayang ke publik.
4. Setelah selesai & sudah dites di browser: commit dan push. Kalau bukan kolaborator, buat branch + Pull Request.
5. Naik-tayang (deploy) ke hosting dilakukan oleh Benny: file versi baru disalin menjadi `index.html` di hosting.

## Aturan simpel buat tim

- Satu perubahan = satu cerita; pesan commit jelas, mis. `v20: perbaiki skor ganda`, bukan `update`.
- Jangan commit data pribadi member (nomor HP, alamat, dsb) — pakai data dummy saat tes.
- File versi lama jangan dihapus; nama file = arsip riwayat.


## Firebase

Aplikasi memakai Firebase untuk login (Anonymous) dan penyimpanan data.

- Versi terbaru (`index.html`, `v07.html` ke atas) menyimpan konfigurasi Firebase dalam bentuk base64 di variabel `encConfig`. Ambil nilainya dengan:
  ```bash
  python3 tools/get-firebase-config.py            # default index.html
  python3 tools/get-firebase-config.py v19.html
  ```
- Versi lama `v03`-`v06` memuat konfigurasi mentah — di repo ini `apiKey`-nya sudah diganti placeholder `MASUKAN_API_KEY_ANDA_DISINI` (isi sendiri kalau perlu menjalankan versi itu).
- ⚠️ Proyek `smash-angin` adalah **produksi** (data member asli). Untuk eksperimen, buat project Firebase sendiri — caranya ada di [`FIREBASE-SETUP.md`](FIREBASE-SETUP.md).

## Kontak

Pemilik & maintainer: **Benny (benxt13)**.

_Dibuat 23 Sep 2026 — sinkronisasi penuh dari file live smashangin.cloud._

## Deploy otomatis

Situs ini tayang otomatis dari repo ini:

- Setiap perubahan yang masuk ke `main` dikirim ke hosting dalam ~2 menit (pemantau
  di server Benny, lewat FTPS).
- Manual dari repo: `python3 tools/smashangin_deploy.py` (laporan saja, default) atau
  `python3 tools/smashangin_deploy.py --go` (benar-benar unggah).
- Kredensial FTP tidak pernah disimpan di repo: diambil dari env `FTP_HOST`/`FTP_USER`/
  `FTP_PASS` atau berkas yang diberikan lewat `--creds`.
- Berkas yang tidak ikut tayang otomatis ada di `.deployignore`, misalnya salinan
  `v03`-`v06` di repo (kunci Firebase-nya sengaja dikosongkan) supaya tidak menimpa
  versi server yang masih jalan.
- Pengaman: halaman yang memakai login Email/Password ditahan otomatis kalau provider
  Email/Password di Firebase Authentication masih mati - kalau dipaksa tayang, panel
  admin jadi tidak bisa dibuka.
- Berkas baru harus ditaruh di akar repo (bukan subfolder) agar ikut ter-deploy.
