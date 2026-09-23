#!/usr/bin/env python3
"""Deploy berkas situs smashangin.cloud dari repo Git ke hosting (FTPS).

DEFAULT = DRY-RUN: tidak mengunggah apa pun tanpa --go.

Pemakaian:
  python3 tools/smashangin_deploy.py                     # laporan saja
  python3 tools/smashangin_deploy.py --go                # unggah yang perlu saja
  python3 tools/smashangin_deploy.py --go --all          # paksa unggah semua berkas situs
  python3 tools/smashangin_deploy.py --go --only index.html v19.html
  python3 tools/smashangin_deploy.py --go --json /tmp/deploy.json
  python3 tools/smashangin_deploy.py --go --backup /root/smashangin-backup/20260923

Kredensial (urutan prioritas): env FTP_HOST/FTP_USER/FTP_PASS (+FTP_PORT) lalu --creds FILE.
Tidak pernah mengunggah: dokumentasi, tools/, .github/, .git/ — plus daftar di .deployignore.

PENGAMAN: berkas HTML yang memakai signInWithEmailAndPassword akan DITAHAN bila provider
Email/Password di Firebase masih mati (kalau dipaksa tayang, panel admin jadi tidak bisa dibuka).
"""

from __future__ import annotations

import argparse
import base64
import fnmatch
import json
import os
import pathlib
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from ftplib import FTP_TLS

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_REMOTE = "/public_html/smashangin"
DEFAULT_CREDS = "/root/cahaya-ameng-website/creds.env"

TEXT_EXT = {".html", ".htm", ".css", ".js", ".mjs", ".json", ".txt", ".xml",
            ".svg", ".webmanifest", ".map", ".php", ".ini", ".conf"}
BIN_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff",
           ".woff2", ".ttf", ".otf", ".pdf", ".mp4", ".zip"}
DOTFILES_INCLUDE = {".htaccess", ".user.ini", ".robots.txt", ".htpasswd"}
NEVER = {"README.md", "FIREBASE-SETUP.md", "firestore.rules", ".deployignore",
         ".gitignore", "LICENSE", "SKILL.md"}
EXCLUDE_DIRS = {"tools", ".github", ".git", "docs", "reports", "backups", "node_modules"}


def log(msg: str) -> None:
    print(msg, flush=True)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Deploy situs smashangin.cloud dari repo ke hosting (FTPS).")
    p.add_argument("--root", default=str(REPO_ROOT), help="akar repo (default: akar repo skrip ini)")
    p.add_argument("--remote", default=DEFAULT_REMOTE, help="direktori remote (default: %(default)s)")
    p.add_argument("--creds", default=DEFAULT_CREDS, help="berkas kredensial FTP (default: %(default)s)")
    p.add_argument("--go", action="store_true", help="benar-benar unggah (tanpa ini = laporan saja)")
    p.add_argument("--all", action="store_true", help="paksa unggah semua berkas situs")
    p.add_argument("--only", nargs="+", default=None, help="batasi ke berkas tertentu")
    p.add_argument("--backup", default=None, help="salin berkas remote ke folder ini sebelum ditimpa")
    p.add_argument("--json", dest="json_out", default=None, help="tulis ringkasan JSON ke berkas ini")
    p.add_argument("--no-gate", action="store_true", help="lewati pengaman login Email/Password")
    p.add_argument("--timeout", type=int, default=90)
    return p.parse_args(argv)


def load_creds(args):
    host = os.environ.get("FTP_HOST")
    user = os.environ.get("FTP_USER")
    password = os.environ.get("FTP_PASS")
    port = os.environ.get("FTP_PORT")
    path = pathlib.Path(args.creds).expanduser()
    if not (host and user and password) and path.exists():
        cfg = {}
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            cfg[key.strip()] = val.strip().strip('"').strip("'")
        host = host or cfg.get("FTP_HOST")
        user = user or cfg.get("FTP_USER")
        password = password or cfg.get("FTP_PASS")
        port = port or cfg.get("FTP_PORT")
    if not (host and user and password):
        raise SystemExit("Kredensial FTP tidak lengkap (env FTP_HOST/FTP_USER/FTP_PASS atau --creds).")
    return host, int(port or 21), user, password


def connect(host, port, user, password, timeout):
    ctx = ssl.create_default_context()
    ftp = FTP_TLS(context=ctx, timeout=timeout)
    ftp.connect(host, port)
    ftp.login(user, password)
    ftp.prot_p()
    return ftp


def load_ignore(root: pathlib.Path) -> list[str]:
    path = root / ".deployignore"
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def discover(root: pathlib.Path, ignore: list[str], only=None) -> list[str]:
    names = []
    for entry in sorted(root.iterdir()):
        if entry.is_dir():
            continue
        name = entry.name
        if name in NEVER:
            continue
        if name.startswith(".") and name not in DOTFILES_INCLUDE:
            continue
        if entry.suffix.lower() not in (TEXT_EXT | BIN_EXT) and name not in DOTFILES_INCLUDE:
            continue
        if any(fnmatch.fnmatch(name, pat) for pat in ignore):
            continue
        if only and not any(fnmatch.fnmatch(name, pat) for pat in only):
            continue
        names.append(name)
    return names


def firebase_api_key(html: str) -> str | None:
    """Ambil apiKey dari berkas HTML (base64 encConfig atau apiKey: "..." biasa)."""
    m = re.search(r'encConfig\s*=\s*"([A-Za-z0-9+/=]{40,})"', html)
    if m:
        try:
            cfg = json.loads(base64.b64decode(m.group(1)).decode("utf-8", "replace"))
            if isinstance(cfg, dict) and cfg.get("apiKey"):
                return cfg["apiKey"]
        except Exception:
            pass
    m = re.search(r'apiKey\s*:\s*"([^"]{20,})"', html)
    return m.group(1) if m else None


def gate_email_password(root: pathlib.Path, names: list[str], allow_bypass: bool):
    """Tahan berkas HTML yang butuh login Email/Password bila provider Firebase masih mati.

    Kembalikan: (held: dict[nama -> alasan], notes: list[str])
    """
    held: dict[str, str] = {}
    notes: list[str] = []
    if allow_bypass:
        return held, notes
    for name in names:
        text = (root / name).read_text(errors="replace")
        if "signInWithEmailAndPassword" not in text:
            continue
        key = firebase_api_key(text)
        email_match = re.search(r"ADMIN_EMAIL\s*=\s*'([^']+)'", text)
        email = email_match.group(1) if email_match else None
        if not key or not email:
            held[name] = "butuh login Email/Password tapi apiKey/ADMIN_EMAIL tidak terbaca — periksa manual"
            continue
        body = json.dumps({"email": email, "password": "gate_check_bukan_sandi",
                           "returnSecureToken": True}).encode()
        url = ("https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=" + key)
        try:
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as resp:
                json.loads(resp.read().decode("utf-8", "replace"))
            notes.append(f"{name}: login {email} berhasil diverifikasi (sandi pemeriksa) — aneh, periksa.")
        except urllib.error.HTTPError as err:
            payload = err.read().decode("utf-8", "replace")
            msg = ""
            try:
                msg = json.loads(payload).get("error", {}).get("message", "")
            except Exception:
                msg = payload[:120]
            if msg.startswith("PASSWORD_LOGIN_DISABLED"):
                held[name] = ("provider Email/Password masih MATI di Firebase Authentication — "
                              "aktifkan dulu, kalau tidak panel admin tidak bisa dibuka")
            elif msg.startswith("EMAIL_NOT_FOUND"):
                notes.append(f"{name}: provider aktif, tapi akun {email} belum dibuat di Firebase Authentication")
            elif msg.startswith(("INVALID_LOGIN_CREDENTIALS", "INVALID_PASSWORD", "INVALID_EMAIL")):
                notes.append(f"{name}: provider aktif dan akun {email} sudah ada")
            else:
                notes.append(f"{name}: pemeriksaan login tidak konklusif ({msg[:80]}) — diteruskan")
        except Exception as err:  # jaringan dll — jangan blokir deploy karena ini
            notes.append(f"{name}: tidak bisa memeriksa login ({type(err).__name__}) — diteruskan")
    return held, notes


def remote_size(ftp, path: str):
    try:
        return int(ftp.size(path))
    except Exception:
        return None


def main(argv=None) -> int:
    args = parse_args(argv)
    root = pathlib.Path(args.root).resolve()
    ignore = load_ignore(root)
    names = discover(root, ignore, args.only)
    if not names:
        log("Tidak ada berkas situs yang cocok untuk di-deploy.")
        return 0

    if args.only:
        html_needing_gate = [n for n in names if "signInWithEmailAndPassword"
                             in (root / n).read_text(errors="replace")]
    else:
        html_needing_gate = [n for n in names if n.endswith((".html", ".htm"))
                             and "signInWithEmailAndPassword" in (root / n).read_text(errors="replace")]
    held, notes = gate_email_password(root, html_needing_gate, args.no_gate)

    host, port, user, password = load_creds(args)
    log(f"Host   : {host}:{port}   Remote: {args.remote}")
    log(f"Mode   : {'UNGGAH (--go)' if args.go else 'DRY-RUN (tidak mengunggah)'}"
        f"{'   [paksa semua]' if args.all else ''}")
    for note in notes:
        log(f"Catatan: {note}")
    for name, reason in held.items():
        log(f"DITAHAN: {name} — {reason}")

    ftp = connect(host, port, user, password, args.timeout)
    backup_dir = pathlib.Path(args.backup) if args.backup else None
    if backup_dir:
        backup_dir.mkdir(parents=True, exist_ok=True)

    uploaded, skipped, failed, verified = [], [], [], []
    start = time.time()
    try:
        for name in names:
            if name in held:
                continue
            local = root / name
            size_local = local.stat().st_size
            remote = f"{args.remote}/{name}"
            size_remote = remote_size(ftp, remote)
            is_text = local.suffix.lower() in TEXT_EXT or name in DOTFILES_INCLUDE
            if size_remote is None:
                action, why = "UPLOAD", "belum ada di server"
            elif size_remote != size_local:
                action, why = "UPLOAD", f"beda ukuran ({size_remote} -> {size_local})"
            elif is_text:
                action, why = "UPLOAD", "berkas teks (selalu disegarkan)"
            elif args.all:
                action, why = "UPLOAD", "dipaksa (--all)"
            else:
                action, why = "SKIP", "ukuran sama"

            if action == "SKIP":
                skipped.append(name)
                log(f"  lewat   {name} ({why})")
                continue
            if not args.go:
                uploaded.append(name)
                log(f"  AKAN    {name} ({why})")
                continue
            try:
                if backup_dir and size_remote is not None:
                    dest = backup_dir / name
                    with open(dest, "wb") as fh:
                        ftp.retrbinary(f"RETR {remote}", fh.write)
                with open(local, "rb") as fh:
                    ftp.storbinary(f"STOR {remote}", fh, blocksize=32768)
                now_size = remote_size(ftp, remote)
                if now_size == size_local:
                    uploaded.append(name)
                    verified.append(name)
                    log(f"  OK      {name} ({size_local} byte, terverifikasi)")
                else:
                    failed.append(name)
                    log(f"  GAGAL   {name} (ukuran di server {now_size} != {size_local})")
            except Exception as err:
                failed.append(name)
                log(f"  GAGAL   {name} ({type(err).__name__}: {err})")
    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()

    elapsed = time.time() - start
    summary = {
        "dry_run": not args.go,
        "remote": args.remote,
        "root": str(root),
        "uploaded": sorted(uploaded),
        "verified": sorted(verified),
        "skipped": sorted(skipped),
        "held": held,
        "failed": sorted(failed),
        "notes": notes,
        "seconds": round(elapsed, 1),
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    log("")
    log(f"RINGKASAN: {len(uploaded)} diunggah, {len(verified)} terverifikasi, "
        f"{len(skipped)} dilewati, {len(held)} ditahan, {len(failed)} gagal ({elapsed:.1f} detik)")
    if args.json_out:
        pathlib.Path(args.json_out).write_text(json.dumps(summary, indent=2, ensure_ascii=False))
        log(f"Ringkasan JSON: {args.json_out}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
