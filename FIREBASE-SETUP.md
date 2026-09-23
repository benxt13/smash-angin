# Firebase Setup — Smash Angin

Panduan untuk teman/senior yang ikut develop `smashangin.cloud`.

## 1. Konfigurasi proyek `smash-angin`

Aplikasi ini memakai Firebase untuk **login (Anonymous Auth)** dan penyimpanan data.
Konfigurasi web-nya sudah ada di dalam `index.html` — disimpan dalam bentuk base64 pada variabel `encConfig`.
Ambil dengan skrip yang sudah disediakan:

```bash
python3 tools/get-firebase-config.py            # default: index.html
python3 tools/get-firebase-config.py v19.html   # versi arsip tertentu
```

Contoh nilai yang bukan rahasia (semua ini memang publik di aplikasi web):

| Field | Nilai | Guna |
|---|---|---|
| `authDomain` | `smash-angin.firebaseapp.com` | domain login Firebase |
| `projectId` | `smash-angin` | nama proyek di Firebase Console |
| `storageBucket` | `smash-angin.firebasestorage.app` | penyimpanan berkas |
| `messagingSenderId` | `562614873594` | ID pengirim aplikasi web |
| `appId` | `1:562614873594:web:433f01f857e66cfc62c843` | identitas aplikasi web |
| `apiKey` | (lihat skrip di atas) | identitas publik aplikasi web — **bukan** kata sandi akun |

> Catatan: `apiKey` Firebase untuk aplikasi web bukan rahasia; keamanan dijaga oleh
> **Firestore Security Rules** + pembatasan kunci (HTTP referrer) di Google Cloud Console,
> bukan oleh kerahasiaan berkas. Yang benar-benar rahasia adalah *service account / admin key* —
> jangan pernah disebar.

## 2. Tempat konfigurasi di kode

`index.html` (versi aktif) dan `v07.html` ke atas menyimpan konfigurasi seperti ini:

```js
const encConfig = "eyJhcG...";                     // base64 dari JSON konfigurasi
const fbConfig  = JSON.parse(atob(encConfig));      // dikembalikan jadi objek
firebase.initializeApp(fbConfig);
```

Kalau perlu meng-encode konfigurasi lain (mis. project dev sendiri):

```bash
python3 -c "import base64,json;print(base64.b64encode(json.dumps(dict(apiKey='ISI',authDomain='ISI',projectId='ISI',storageBucket='ISI',messagingSenderId='ISI',appId='ISI')).encode()).decode())"
```

Hasilnya tempel sebagai nilai `encConfig`.

Versi lama `v03`–`v06` di repo ini konfigurasinya **dikosongkan** (placeholder `MASUKAN_API_KEY_ANDA_DISINI`),
karena berkas itu mengirim kunci mentah. Isi sendiri kalau memang perlu menjalankan versi tersebut.

## 3. Jalur data di Firestore

Semua data aplikasi ada di bawah satu jalur:

```
artifacts/smash-angin-prod/public/data/
├── players/            daftar pemain
├── matches/            hasil pertandingan
├── sparing_teams/      tim sparing
├── sparing_matches/    hasil sparing
├── reguler_history/    riwayat sesi reguler
├── config/reguler_meta
└── sparing_config/info
```

`appId` di kode bukan `appId` Firebase, tapi string tetap `smash-angin-prod`
(`atob("c21hc2gtYW5naW4tcHJvZA==")` di `index.html`).

## 4. ⚠️ Sebelum ngoprek / pull request

- Proyek `smash-angin` adalah **PRODUKSI** — data member, jadwal, dan skor asli ada di sana.
  **Jangan** uji tulis/hapus data di project ini.
- **Aturan keamanan data** ada di `firestore.rules` (usulan). Uji dulu di project dev, lalu
  pasang di produksi lewat *Firebase Console → Firestore Database → Rules → Publish*.
  Lihat juga komentar `ADMIN_EMAIL` di `index.html` — nilainya harus sama dengan aturan tersebut.
- Untuk development, sebaiknya pakai **project Firebase sendiri** (gratis):
  1. https://console.firebase.google.com → *Add project* (contoh: `smash-angin-dev-namamu`)
  2. *Authentication* → *Sign-in method* → aktifkan **Anonymous**
  3. *Firestore Database* → *Create database* (mode test, khusus dev)
  4. *Project settings* → *Your apps* → tambahkan **Web app** → salin config
  5. Ganti `encConfig` di berkas yang kamu kerjakan dengan config project dev tersebut
  6. Jangan commit config project pribadimu kalau tidak perlu
- Jangan pakai kunci ini untuk aplikasi/keperluan lain, dan jangan kirim kunci ke grup publik.

## 5. Alur kontribusi (pull request)

```bash
git clone https://github.com/benxt13/smash-angin.git
cd smash-angin
git checkout -b fitur/nama-fiturmu
# ... kerjakan ...
git add -A
git commit -m "Fitur: ..."
git push origin fitur/nama-fiturmu
```

Lalu buka **Pull Request** ke branch `main` di GitHub. Mohon jangan push langsung ke `main`
supaya bisa direview dulu.

## 6. Struktur berkas

| Berkas | Isi |
|---|---|
| `index.html` | versi aktif yang dilayani situs smashangin.cloud |
| `v01.html` – `v19.html` | arsip versi sebelumnya (`v19` paling baru; beberapa bernama `vNN (stable).html`) |
| `.htaccess`, `.user.ini`, `php.ini` | pengaturan hosting (redirect HTTPS, index, batas PHP) |
| `tools/get-firebase-config.py` | pengambil konfigurasi Firebase dari berkas HTML |
| `firestore.rules` | usulan aturan keamanan Firestore (baca/tulis data) |
| `README.md`, `FIREBASE-SETUP.md` | dokumentasi |

## 7. Butuh project dev khusus tim?

Kalau mau, Benny bisa membuatkan project Firebase kedua (mis. `smash-angin-dev`) yang **boleh**
dipakai bebas oleh tim — config-nya aman dibagikan karena tidak menyimpan data asli.
Sampaikan saja di grup kalau ini dibutuhkan.
