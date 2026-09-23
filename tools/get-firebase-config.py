#!/usr/bin/env python3
"""Cetak konfigurasi Firebase yang dipakai sebuah berkas HTML Smash Angin.

Pemakaian:
    python3 tools/get-firebase-config.py            # default: index.html
    python3 tools/get-firebase-config.py v19.html   # versi arsip tertentu
    python3 tools/get-firebase-config.py --self-test

Versi baru menyimpan konfigurasi sebagai base64 di variabel `encConfig`;
versi lama menuliskan objek konfigurasi mentah. Keduanya didukung.
"""
import base64
import json
import pathlib
import re
import sys

FIELDS = ("apiKey", "authDomain", "projectId", "storageBucket", "messagingSenderId", "appId")
ENC_RE = re.compile(r'encConfig\s*=\s*"([A-Za-z0-9+/=]+)"')


def extract(html):
    """Kembalikan dict konfigurasi Firebase dari isi berkas HTML."""
    m = ENC_RE.search(html)
    if m:
        cfg = json.loads(base64.b64decode(m.group(1)))
        return {k: cfg[k] for k in FIELDS if k in cfg}
    cfg = {}
    for k in FIELDS:
        mm = re.search(rf'{k}\s*[:=]\s*"([^"]+)"', html)
        if mm:
            cfg[k] = mm.group(1)
    return cfg


SAMPLE = 'const encConfig = "eyJhcGlLZXkiOiAiQUl6YVRFU1QifQ==";'


def main(argv):
    if "--self-test" in argv:
        got = extract(SAMPLE)
        assert got == {"apiKey": "AIzaTEST"}, got
        raw = '<script>var firebaseConfig={apiKey:"K",projectId:"p"};</script>'
        assert extract(raw) == {"apiKey": "K", "projectId": "p"}, extract(raw)
        assert extract("<html>tanpa konfigurasi</html>") == {}
        print("self-test OK")
        return 0

    args = [a for a in argv[1:] if not a.startswith("--")]
    path = pathlib.Path(args[0]) if args else pathlib.Path(__file__).resolve().parent.parent / "index.html"
    if not path.is_file():
        sys.exit(f"berkas tidak ditemukan: {path}")
    html = path.read_text(encoding="utf-8", errors="replace")
    cfg = extract(html)
    if not cfg:
        sys.exit(
            f"Konfigurasi Firebase tidak ditemukan di {path.name} "
            "(mungkin masih placeholder MASUKAN_API_KEY_ANDA_DISINI)."
        )
    print(json.dumps(cfg, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
