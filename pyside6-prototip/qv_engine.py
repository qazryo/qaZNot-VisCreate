# -*- coding: utf-8 -*-
"""qAnvas motoru + lisans + Google girisi (qaznote.py'den Tk'siz olarak ayiklandi).
Bu dosya otomatik uretilmistir; arayuzden bagimsizdir (PySide6 kullanir)."""
import base64
import copy
import hashlib
import html
import io
import secrets
import socket
import struct
import threading
import webbrowser
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
import random
import re
import hmac
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime

try:
    from PIL import Image as _PILImage  # noqa: F401
    QV_HAVE_PIL = True
except Exception:  # noqa: BLE001
    QV_HAVE_PIL = False

APP = "qaZNot"
ANIM = 1.8  # genel animasyon süresi çarpanı (1.0 = eski hız)

def _data_dir():
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    d = os.path.join(base, "qaznote")
    try:
        os.makedirs(os.path.join(d, "drafts"), exist_ok=True)
        return d
    except OSError:
        d = os.path.join(tempfile.gettempdir(), "qaznote")
        os.makedirs(os.path.join(d, "drafts"), exist_ok=True)
        return d


DATA_DIR = _data_dir()
CONFIG = os.path.join(DATA_DIR, "settings.json")
SECURITY = os.path.join(DATA_DIR, "security.json")
GOOGLE = os.path.join(DATA_DIR, "google.json")
AVATARS = os.path.join(DATA_DIR, "avatars")
DRAFT = os.path.join(DATA_DIR, "drafts", "draft.json")
LEGACY_CONFIG = os.path.join(os.path.expanduser("~"), ".qaznot.json")
ENC_LABELS = {"utf-8": "UTF-8", "utf-8-sig": "BOM'lu UTF-8", "cp1254": "ANSI"}
SIZES = [8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 60, 72]
PALETTE = [
    "#000000", "#434343", "#666666", "#999999", "#b7b7b7", "#d9d9d9", "#efefef", "#ffffff",
    "#e03131", "#f08c00", "#fcc419", "#40c057", "#15aabf", "#4c6ef5", "#7950f2", "#e64980",
    "#ffc9c9", "#ffe8cc", "#fff3bf", "#d3f9d8", "#c5f6fa", "#dbe4ff", "#e5dbff", "#fcc2d7",
    "#a61e4d", "#d9480f", "#e67700", "#2b8a3e", "#0b7285", "#364fc7", "#5f3dc4", "#862e9c",
]

def lum(c):
    r, g, b = (int(c[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.299 * r + 0.587 * g + 0.114 * b


def mix(a, b, t):
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x * (1 - t) + y * t) for x, y in zip(ca, cb))


# --------------------------------------------------------------------------- #
#  Sürümler ve lisans/hesap tablosu
#  Her sürüm için 10 anahtar. Tabloda anahtarların kendisi değil SHA-256 özeti
#  durur; anahtar girilince ona tanımlı hesap bilgileri gösterilir.
# --------------------------------------------------------------------------- #
CORE_FONTS = ("Segoe UI", "Arial", "Calibri", "Times New Roman", "Georgia", "Verdana", "Tahoma",
              "Trebuchet MS", "Cambria", "Consolas", "Courier New", "Helvetica", "DejaVu Sans",
              "DejaVu Serif", "DejaVu Sans Mono", "Liberation Sans", "Liberation Serif")
EDITIONS = {
    "core": dict(label="Core", fonts=CORE_FONTS, themes=("Beyaz", "Siyah"), signing=False, qanvas="presets", color="#8e8e93",
                 info=("Belirli yazı tipleri", "Yalnızca Siyah ve Beyaz tema", "Belge imzalama yok")),
    "enterprise": dict(label="Enterprise", fonts=None, themes=None, signing=False, qanvas="full", color="#0a84ff",
                       info=("Tüm yazı tipleri", "Tüm temalar", "Belge imzalama yok")),
    "professional": dict(label="Professional", fonts=None, themes=None, signing=True, qanvas="full", color="#bf5af2",
                         info=("Tüm yazı tipleri", "Tüm temalar", "Belge imzalama dahil")),
}
LICENSES = {
    '51260bec2a2f0faca5117c2eebd8b937132ed55f5b6e76e607e6438f23597bc2': {'ed': 'core', 'user': 'QAZ Note Core kullanıcısı', 'name': 'QAZ Note Core kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-C-001', 'since': '2026-10-23'},
    'f3fb9bcce189d5693cb81c8ff19a9cff06cf93ea0b482bd45913e6d1fab30e0e': {'ed': 'core', 'user': 'QAZ Note Core kullanıcısı', 'name': 'QAZ Note Core kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-C-002', 'since': '2026-10-23'},
    '563d19e06f88e29251b5d3d21a8367e3cd2f3b4fe786d17d96452082203b6e67': {'ed': 'core', 'user': 'QAZ Note Core kullanıcısı', 'name': 'QAZ Note Core kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-C-003', 'since': '2026-10-23'},
    '4607303777806137eb75e8d1c2e91035041539ea9b612c06819fe63a99810aa5': {'ed': 'core', 'user': 'QAZ Note Core kullanıcısı', 'name': 'QAZ Note Core kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-C-004', 'since': '2026-10-23'},
    '193fa370943350cdb165718b8a16783ede1272cab1af15e14a086edbc911b341': {'ed': 'core', 'user': 'QAZ Note Core kullanıcısı', 'name': 'QAZ Note Core kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-C-005', 'since': '2026-10-23'},
    'd790f0641e9624700047bb7dad473dadf4948e4e5af7195f7c1e77cfc85f4acc': {'ed': 'core', 'user': 'QAZ Note Core kullanıcısı', 'name': 'QAZ Note Core kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-C-006', 'since': '2026-10-23'},
    '8c59073b4cb900fa77e74d694cf52fd594bb7a23ad38ea2f0ffe66860fc4cdab': {'ed': 'core', 'user': 'QAZ Note Core kullanıcısı', 'name': 'QAZ Note Core kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-C-007', 'since': '2026-10-23'},
    'b878df849fc2120a152e9066f1d9ccb2f88f6d1f07059a7baa186d55d7281b8b': {'ed': 'core', 'user': 'QAZ Note Core kullanıcısı', 'name': 'QAZ Note Core kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-C-008', 'since': '2026-10-23'},
    '6237e18779061f39e9dd58f35be7eccc67a48fc76a38efeaa218bf68e78a8a8d': {'ed': 'core', 'user': 'QAZ Note Core kullanıcısı', 'name': 'QAZ Note Core kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-C-009', 'since': '2026-10-23'},
    'b12b0998d60f1a1dcb4040ca006058428c1ebcd3016a0ab6dcc31a6cb195294c': {'ed': 'core', 'user': 'QAZ Note Core kullanıcısı', 'name': 'QAZ Note Core kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-C-010', 'since': '2026-10-23'},
    'f650550d8fe16a5ea503ffe9562a322f373da3f4fe2dbc5aa70846220a4365d1': {'ed': 'enterprise', 'user': 'QAZ Note Enterprise kullanıcısı', 'name': 'QAZ Note Enterprise kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-E-001', 'since': '2026-10-23'},
    '72d34eb07d42435c9627effb2f309b1383e531a7cd7e3aadf799251145dab4d8': {'ed': 'enterprise', 'user': 'QAZ Note Enterprise kullanıcısı', 'name': 'QAZ Note Enterprise kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-E-002', 'since': '2026-10-23'},
    '4f549fdf083b8975e9202729b2f2a43deca87b8d6cd2c10468f4740ecf8ff1a7': {'ed': 'enterprise', 'user': 'QAZ Note Enterprise kullanıcısı', 'name': 'QAZ Note Enterprise kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-E-003', 'since': '2026-10-23'},
    '09415e7458f6594f21bfee49eb1a55627f6b668d6ff9cb2daf0d1c84a8b8f517': {'ed': 'enterprise', 'user': 'QAZ Note Enterprise kullanıcısı', 'name': 'QAZ Note Enterprise kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-E-004', 'since': '2026-10-23'},
    '614daf4316158d8befc7d91499022483cde0359626483adbc876e1ce74554971': {'ed': 'enterprise', 'user': 'QAZ Note Enterprise kullanıcısı', 'name': 'QAZ Note Enterprise kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-E-005', 'since': '2026-10-23'},
    '541145835bda85473f3905bd658bf81cce3e261788c09bf8292d8f7238906989': {'ed': 'enterprise', 'user': 'QAZ Note Enterprise kullanıcısı', 'name': 'QAZ Note Enterprise kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-E-006', 'since': '2026-10-23'},
    '9c8de20b8ed97bdda8221e56a1b77756e571356c13471fd04f8bdf58cb1043cb': {'ed': 'enterprise', 'user': 'QAZ Note Enterprise kullanıcısı', 'name': 'QAZ Note Enterprise kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-E-007', 'since': '2026-10-23'},
    '9ba49f327f846957f40f2accd701493577050de29709613cf1f8dce4ca2e8381': {'ed': 'enterprise', 'user': 'QAZ Note Enterprise kullanıcısı', 'name': 'QAZ Note Enterprise kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-E-008', 'since': '2026-10-23'},
    'b5d34ed35c8ac63d6498288513f29f87ba2b784287488d14ee17f7583f6418d9': {'ed': 'enterprise', 'user': 'QAZ Note Enterprise kullanıcısı', 'name': 'QAZ Note Enterprise kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-E-009', 'since': '2026-10-23'},
    '9aab853d357b188d8b435d0692bf5fea7e07676aa071a62d728c2b267a5e318a': {'ed': 'enterprise', 'user': 'QAZ Note Enterprise kullanıcısı', 'name': 'QAZ Note Enterprise kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-E-010', 'since': '2026-10-23'},
    '038bae0792c67340a6245f27e7c84a12ecd9c5d52edd435ae432af9b58686c5c': {'ed': 'professional', 'user': 'QAZ Note Professional kullanıcısı', 'name': 'QAZ Note Professional kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-P-001', 'since': '2026-10-23'},
    '832418935a011c0c9b7b8e58ca26ad7155ed68d3dc69645d5b8a0d2c945943d0': {'ed': 'professional', 'user': 'QAZ Note Professional kullanıcısı', 'name': 'QAZ Note Professional kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-P-002', 'since': '2026-10-23'},
    '67c5617c85a62a1604c9bf94fcfbd7a84864f0a127dc39a676bf93b7d8d42ab6': {'ed': 'professional', 'user': 'QAZ Note Professional kullanıcısı', 'name': 'QAZ Note Professional kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-P-003', 'since': '2026-10-23'},
    'b6116ee935257537c78599813c20d1afad23f714e8faa608cd169a6e3861dba9': {'ed': 'professional', 'user': 'QAZ Note Professional kullanıcısı', 'name': 'QAZ Note Professional kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-P-004', 'since': '2026-10-23'},
    'bfb8ede638d2eda768a4a157dc9f552e713e5a6f41f666c4f14f8ca56fcd58cd': {'ed': 'professional', 'user': 'QAZ Note Professional kullanıcısı', 'name': 'QAZ Note Professional kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-P-005', 'since': '2026-10-23'},
    '5505786e93d24fb1f22a2a304916894d3b1443adcc15f607571d6f352f804026': {'ed': 'professional', 'user': 'QAZ Note Professional kullanıcısı', 'name': 'QAZ Note Professional kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-P-006', 'since': '2026-10-23'},
    '0a709ca4ec45dd5bf1354c339c90508784b87809dd007fcdf59c74f06f9cc3c7': {'ed': 'professional', 'user': 'QAZ Note Professional kullanıcısı', 'name': 'QAZ Note Professional kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-P-007', 'since': '2026-10-23'},
    '04f9d41e1db9ec33cf0ddecea9b517a45023e7e0c80eb04fdeced2646f811b24': {'ed': 'professional', 'user': 'QAZ Note Professional kullanıcısı', 'name': 'QAZ Note Professional kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-P-008', 'since': '2026-10-23'},
    'daece8b8db6c788150299f7299d377d5381178c7da9e8e56362f3f7e02597e6a': {'ed': 'professional', 'user': 'QAZ Note Professional kullanıcısı', 'name': 'QAZ Note Professional kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-P-009', 'since': '2026-10-23'},
    '22cd450e0d4a4b1bb4cf98a800cb47e0a22fe40ba702b8c512e9e09a2cc2e8ea': {'ed': 'professional', 'user': 'QAZ Note Professional kullanıcısı', 'name': 'QAZ Note Professional kullanıcısı', 'email': 'qaznote@qaz.local.net', 'id': 'QZ-P-010', 'since': '2026-10-23'},
}

ID_INDEX = {v["id"]: (h, v) for h, v in LICENSES.items()}


def norm_key(s):
    return "".join(ch for ch in str(s).upper() if ch.isalnum())


def fmt_key(s):
    n = norm_key(s)[:20]
    return "-".join(n[i:i + 4] for i in range(0, len(n), 4))


def lookup_license(key):
    h = hashlib.sha256(norm_key(key).encode()).hexdigest()
    acc = LICENSES.get(h)
    return (h, dict(acc)) if acc else (None, None)


def _canon(d):
    return json.dumps(d, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def make_signature(data, h, acc):
    sig = dict(id=acc["id"], user=acc["user"], name=acc["name"], edition=acc["ed"], time=datetime.now().isoformat(timespec="seconds"))
    msg = _canon(data) + "|" + _canon(sig)
    sig["mac"] = hmac.new(bytes.fromhex(h), msg.encode("utf-8"), hashlib.sha256).hexdigest()
    return sig


def verify_signature(data):
    """(geçerli_mi, imza) döndürür; imza yoksa (None, None)."""
    sig = data.get("sig")
    if not isinstance(sig, dict):
        return None, None
    body = {k: v for k, v in data.items() if k != "sig"}
    meta = {k: v for k, v in sig.items() if k != "mac"}
    entry = ID_INDEX.get(sig.get("id"))
    if not entry:
        return False, sig
    mac = hmac.new(bytes.fromhex(entry[0]), (_canon(body) + "|" + _canon(meta)).encode("utf-8"),
                   hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, str(sig.get("mac", ""))), sig

def read_json(path, default=None):
    """JSON okur; ana dosya bozuksa .bak yedeğine düşer."""
    for p in (path, path + ".bak"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except (OSError, ValueError):
            continue
    return default if default is not None else {}


def write_json(path, data):
    """Atomik yazım: önce geçici dosya, sonra yer değiştirme; eski sürüm .bak olarak kalır."""
    tmp = path + ".tmp"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.flush()
            os.fsync(f.fileno())
        if os.path.exists(path):
            try:
                os.replace(path, path + ".bak")
            except OSError:
                pass
        os.replace(tmp, path)
        return True
    except OSError:
        return False


def load_cfg():
    if not os.path.exists(CONFIG) and not os.path.exists(CONFIG + ".bak") and os.path.exists(LEGACY_CONFIG):
        cfg = read_json(LEGACY_CONFIG)
        cfg.pop("license", None)  # eski sürümün anahtarları geçersiz
        return cfg
    return read_json(CONFIG)


def save_cfg(data):
    write_json(CONFIG, data)


def load_security():
    d = read_json(SECURITY)
    return {"fails": int(d.get("fails", 0) or 0), "until": float(d.get("until", 0) or 0)}


def save_security(d):
    write_json(SECURITY, d)

# --------------------------------------------------------------------------- #
#  Google hesabı bağlama (OAuth 2.0, masaüstü uygulaması, PKCE + localhost)
#  Sunucu gerekmez. Yalnızca openid / email / profile izinleri istenir.
# --------------------------------------------------------------------------- #
GOOGLE_CLIENT_ID = "494933954206-cerjhd9dej0fo8vajjhglntpvc8n2tpo.apps.googleusercontent.com"
try:
    from qz_secrets import GOOGLE_CLIENT_SECRET  # yerel dosya, Git'e eklenmez
except ImportError:
    GOOGLE_CLIENT_SECRET = ""
G_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
G_TOKEN = "https://oauth2.googleapis.com/token"
G_INFO = "https://openidconnect.googleapis.com/v1/userinfo"


def _http(req, timeout=15):
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")[:160]
        except Exception:
            body = ""
        raise RuntimeError(f"Google hata verdi ({e.code}). {body}")
    except (urllib.error.URLError, OSError):
        raise RuntimeError("İnternet bağlantısı kurulamadı.")


def _result_page(ok, msg):
    col = "#32d74b" if ok else "#ff453a"
    mark = "✓" if ok else "✕"
    return (f"<!doctype html><html lang='tr'><meta charset='utf-8'><title>qaZNot</title>"
            f"<body style=\"margin:0;height:100vh;display:flex;align-items:center;justify-content:center;"
            f"background:#f5f5f7;font-family:-apple-system,'Segoe UI',sans-serif\">"
            f"<div style='background:#fff;border-radius:28px;padding:48px 56px;text-align:center;"
            f"box-shadow:0 20px 60px rgba(0,0,0,.12)'>"
            f"<div style='width:72px;height:72px;border-radius:50%;background:{col};color:#fff;font-size:38px;"
            f"line-height:72px;margin:0 auto 20px'>{mark}</div>"
            f"<h2 style='margin:0 0 8px;color:#1d1d1f'>{html.escape(msg)}</h2>"
            f"<p style='margin:0;color:#86868b'>Bu sekmeyi kapatıp qaZNot'a dönebilirsin.</p></div></body></html>"
            ).encode("utf-8")


class GoogleAuth(threading.Thread):
    """Tarayıcıda Google izin ekranını açar, cevabı 127.0.0.1 üzerinden alır. UI donmasın diye thread'dedir."""

    def __init__(self):
        super().__init__(daemon=True)
        self.profile = self.photo = self.error = None
        self.done = False
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            self._flow()
        except Exception as e:  # noqa: BLE001
            if not self._cancel:
                self.error = str(e) or e.__class__.__name__
        self.done = True

    def _flow(self):
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        state = secrets.token_urlsafe(16)
        got = {}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                if "code" in q or "error" in q:
                    got.update({k: v[0] for k, v in q.items()})
                    ok = "code" in q and q.get("state", [""])[0] == state
                    page = _result_page(ok, "Google hesabın bağlandı" if ok else "Bağlantı tamamlanamadı")
                else:
                    page = _result_page(False, "Geçersiz istek")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(page)))
                self.end_headers()
                self.wfile.write(page)

            def log_message(self, *a):
                pass

        srv = HTTPServer(("127.0.0.1", 0), Handler)
        srv.timeout = 1
        try:
            redirect = f"http://127.0.0.1:{srv.server_address[1]}/"
            url = G_AUTH + "?" + urllib.parse.urlencode({
                "client_id": GOOGLE_CLIENT_ID, "redirect_uri": redirect, "response_type": "code",
                "scope": "openid email profile", "state": state, "code_challenge": challenge,
                "code_challenge_method": "S256", "prompt": "select_account"})
            webbrowser.open(url)
            end = time.time() + 180
            while not got and not self._cancel and time.time() < end:
                srv.handle_request()
        finally:
            srv.server_close()
        if self._cancel:
            return
        if not got:
            raise RuntimeError("Süre doldu. Tarayıcıda izin verilmedi.")
        if got.get("error"):
            raise RuntimeError("İzin verilmedi." if got["error"] == "access_denied" else f"Google: {got['error']}")
        if got.get("state") != state or not got.get("code"):
            raise RuntimeError("Doğrulama başarısız (state uyuşmuyor).")
        data = urllib.parse.urlencode({
            "code": got["code"], "client_id": GOOGLE_CLIENT_ID, "client_secret": GOOGLE_CLIENT_SECRET,
            "code_verifier": verifier, "redirect_uri": redirect, "grant_type": "authorization_code"}).encode()
        tok = json.loads(_http(urllib.request.Request(G_TOKEN, data=data)).decode("utf-8"))
        access = tok.get("access_token")
        if not access:
            raise RuntimeError("Google erişim anahtarı vermedi.")
        info = json.loads(_http(urllib.request.Request(G_INFO, headers={"Authorization": "Bearer " + access})).decode("utf-8"))
        if not info.get("email"):
            raise RuntimeError("Google e-posta bilgisini vermedi.")
        prof = {"sub": str(info.get("sub", "")), "name": str(info.get("name") or info["email"]),
                "email": str(info["email"]), "linked": datetime.now().isoformat(timespec="seconds")}
        pic = info.get("picture")
        if pic:
            try:
                pic = re.sub(r"=s\d+(-c)?$", "", pic) + "=s192-c"
                self.photo = _http(urllib.request.Request(pic), 10)
            except Exception:  # noqa: BLE001
                self.photo = None
        self.profile = prof


def resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


MAX_TRIES = 5

# --------------------------------------------------------------------------- #
#  qAnvas motoru (Tkinter'siz; PNG/JPG çıktısı için Pillow gerekir)
#  Core  : 3 hazır boyut
#  Enterprise / Professional : şablon kitaplığı + özel çözünürlük
# --------------------------------------------------------------------------- #
QV_MIN, QV_MAX, QV_MAX_PIXELS = 16, 8192, 40_000_000
QV_MAX_LAYERS = 2000
QV_MAX_TEXT_PIXELS = 60_000_000  # tek bir satırın en fazla çizim alanı
QV_EXT = ".qanvas"

QV_CORE_PRESETS = (
    dict(id="logo", name="Logo Tasarımı", w=1024, h=1024),
    dict(id="video", name="Video Kapağı", w=1920, h=1080),
    dict(id="story", name="Dikey Video / Hikâye", w=1080, h=1920),
)
# Enterprise / Professional için ek boş tuval boyutları
QV_EXTRA_SIZES = (
    dict(id="ig-square", name="Instagram Gönderi", w=1080, h=1080),
    dict(id="ig-portrait", name="Instagram Dikey Gönderi", w=1080, h=1350),
    dict(id="yt-banner", name="YouTube Kanal Bannerı", w=2560, h=1440),
    dict(id="a4", name="A4 Baskı (300 dpi)", w=2480, h=3508),
    dict(id="card", name="Kartvizit (300 dpi)", w=1050, h=600),
    dict(id="og", name="Web Kapak Görseli", w=1200, h=630),
)


class QvPermissionError(PermissionError):
    """Bu sürümde olmayan bir qAnvas özelliği istendi."""


def qv_access(ed):
    """ed: EDITIONS[...] kaydı. Sürümün qAnvas haklarını döndürür."""
    full = (ed or {}).get("qanvas") == "full"
    return dict(full=full, presets=QV_CORE_PRESETS, templates=full, custom=full)


def qv_check_size(w, h):
    """Boyutu doğrular; (w, h) tamsayı çifti döndürür, geçersizse ValueError."""
    try:
        w, h = int(str(w).strip()), int(str(h).strip())
    except (TypeError, ValueError):
        raise ValueError("Genişlik ve yükseklik tam sayı olmalı")
    if not (QV_MIN <= w <= QV_MAX and QV_MIN <= h <= QV_MAX):
        raise ValueError(f"Boyut {QV_MIN}–{QV_MAX} piksel arasında olmalı")
    if w * h > QV_MAX_PIXELS:
        raise ValueError(f"Toplam alan en fazla {QV_MAX_PIXELS // 1_000_000} megapiksel olabilir")
    return w, h


def _qv_hex(c, default=None):
    if isinstance(c, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", c):
        return c.lower()
    return default


def _qv_num(v, default=0.0, lo=-1e6, hi=1e6):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return default
    if v != v:  # NaN
        return default
    return max(lo, min(hi, v))


# ---- katman biçimi ---------------------------------------------------------
# rect / ellipse : x y w h fill outline ow rad
# line           : x y x2 y2 color ow
# text           : x y w h text size color family bold italic align
# image          : x y w h asset (belgeye gömülü görselin kimliği) opacity
def qv_clean_layer(d):
    """Dosyadan gelen güvenilmez katmanı temizler; geçersizse None."""
    if not isinstance(d, dict):
        return None
    t = d.get("type")
    if t == "image":
        a = d.get("asset")
        a = a if isinstance(a, str) and re.fullmatch(r"[0-9a-f]{8,64}", a) else ""
        return dict(type=t, x=_qv_num(d.get("x")), y=_qv_num(d.get("y")),
                    w=_qv_num(d.get("w"), 300, 1, 100000), h=_qv_num(d.get("h"), 300, 1, 100000),
                    asset=a, opacity=_qv_num(d.get("opacity"), 1.0, 0.0, 1.0))
    if t in ("rect", "ellipse"):
        return dict(type=t, x=_qv_num(d.get("x")), y=_qv_num(d.get("y")),
                    w=_qv_num(d.get("w"), 100, 1), h=_qv_num(d.get("h"), 100, 1),
                    fill=_qv_hex(d.get("fill")), outline=_qv_hex(d.get("outline")),
                    ow=_qv_num(d.get("ow"), 0, 0, 500), rad=_qv_num(d.get("rad"), 0, 0, 10000),
                    fill2=_qv_hex(d.get("fill2")))
    if t == "line":
        return dict(type=t, x=_qv_num(d.get("x")), y=_qv_num(d.get("y")),
                    x2=_qv_num(d.get("x2")), y2=_qv_num(d.get("y2")),
                    color=_qv_hex(d.get("color"), "#000000"), ow=_qv_num(d.get("ow"), 4, 1, 500))
    if t == "text":
        al = d.get("align") if d.get("align") in ("left", "center", "right") else "center"
        return dict(type=t, x=_qv_num(d.get("x")), y=_qv_num(d.get("y")),
                    w=_qv_num(d.get("w"), 300, 1), h=_qv_num(d.get("h"), 80, 1),
                    text=str(d.get("text", ""))[:5000], size=_qv_num(d.get("size"), 48, 4, 4000),
                    color=_qv_hex(d.get("color"), "#000000"),
                    family=str(d.get("family", "Segoe UI"))[:60],
                    bold=bool(d.get("bold")), italic=bool(d.get("italic")), align=al, fit=bool(d.get("fit")))
    return None


# ---- yazı tipi kaydı (Pillow) ----------------------------------------------
_QV_FILES = {
    # eski yedek zinciri: (normal, kalın, italik, kalın+italik)
    "sans": ("segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf", "segoeuiz.ttf"),
    "arial": ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf"),
    "serif": ("georgia.ttf", "georgiab.ttf", "georgiai.ttf", "georgiaz.ttf"),
    "mono": ("consola.ttf", "consolab.ttf", "consolai.ttf", "consolaz.ttf"),
}
_QV_FALLBACK = {
    "sans": ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans-Oblique.ttf", "DejaVuSans-BoldOblique.ttf"),
    "arial": ("LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf", "LiberationSans-Italic.ttf",
              "LiberationSans-BoldItalic.ttf"),
    "serif": ("DejaVuSerif.ttf", "DejaVuSerif-Bold.ttf", "DejaVuSerif-Italic.ttf", "DejaVuSerif-BoldItalic.ttf"),
    "mono": ("DejaVuSansMono.ttf", "DejaVuSansMono-Bold.ttf", "DejaVuSansMono-Oblique.ttf",
             "DejaVuSansMono-BoldOblique.ttf"),
}
_qv_font_cache = {}
_QV_REG = None          # {küçük harf ad: {"name": ad, "files": {"r"/"b"/"i"/"bi": yol}}}
_QV_SLUGS = {}
_QV_LOCK = threading.RLock()

# Çevrimiçi (Google Fonts, OFL) seçki. Tıklayınca indirilir, sonra çevrimdışı çalışır.
QV_GFONTS = (
    "Poppins", "Montserrat", "Roboto", "Open Sans", "Lato", "Inter", "Oswald", "Raleway", "Nunito", "Rubik",
    "Work Sans", "Barlow", "Kanit", "Fira Sans", "Josefin Sans", "Quicksand", "Comfortaa", "Fredoka",
    "Playfair Display", "Merriweather", "Lora", "PT Serif", "DM Serif Display", "Cormorant Garamond",
    "Cinzel", "Abril Fatface", "Yeseva One", "Bebas Neue", "Anton", "Archivo Black", "Alfa Slab One",
    "Staatliches", "Teko", "Russo One", "Righteous", "Orbitron", "Exo 2", "Bangers", "Black Ops One",
    "Lobster", "Pacifico", "Dancing Script", "Caveat", "Satisfy", "Sacramento", "Great Vibes",
    "Permanent Marker", "Shadows Into Light", "Amatic SC", "Space Grotesk", "Press Start 2P", "Baloo 2",
)


def qv_slug(name):
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def qv_user_font_dir():
    d = os.path.join(_data_dir(), "qv_fonts")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass
    return d


def _qv_font_dirs():
    if sys.platform.startswith("win"):
        dirs = [os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts")]
    elif sys.platform == "darwin":
        dirs = ["/System/Library/Fonts", "/Library/Fonts", os.path.expanduser("~/Library/Fonts")]
    else:
        dirs = ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts"),
                os.path.expanduser("~/.local/share/fonts")]
    return dirs + [qv_user_font_dir()]


def _qv_style_key(style):
    s = (style or "").lower().replace("-", " ")
    b, i = "bold" in s, ("italic" in s or "oblique" in s)
    rest = s.replace("bold", "").replace("italic", "").replace("oblique", "").strip()
    if rest and rest not in ("regular", "book", "normal", "roman", "standard"):
        return None
    return ("b" if b else "") + ("i" if i else "") or "r"


def qv_scan_fonts(force=False):
    """Yüklü ve indirilmiş yazı tiplerini tarar (bir kez; sonuç önbellekte)."""
    global _QV_REG, _QV_SLUGS
    with _QV_LOCK:
        if _QV_REG is not None and not force:
            return _QV_REG
        from PIL import ImageFont
        reg, alias = {}, {}
        for d in _qv_font_dirs():
            if not d or not os.path.isdir(d):
                continue
            for root, _dirs, files in os.walk(d):
                for fn in files:
                    if not fn.lower().endswith((".ttf", ".otf")):
                        continue
                    p = os.path.join(root, fn)
                    try:
                        fam, sty = ImageFont.truetype(p, 12).getname()
                    except Exception:  # noqa: BLE001
                        continue
                    k = _qv_style_key(sty)
                    if k and fam:
                        if os.path.dirname(os.path.dirname(p)) == qv_user_font_dir():
                            alias.setdefault(os.path.basename(os.path.dirname(p)), fam.lower())
                        reg.setdefault(fam.lower(), dict(name=fam, files={}))["files"].setdefault(k, p)
        _QV_REG = reg
        _QV_SLUGS = {qv_slug(k): k for k in reg}
        for a, k in alias.items():
            _QV_SLUGS.setdefault(a, k)
        _qv_font_cache.clear()
        return reg


def qv_font_families():
    return sorted((e["name"] for e in qv_scan_fonts().values()), key=str.lower)


def qv_font_installed(family):
    return _qv_lookup(family) is not None


def _qv_lookup(family):
    reg = qv_scan_fonts()
    k = (family or "").lower()
    return reg.get(k) or reg.get(_QV_SLUGS.get(qv_slug(family), ""))


def _qv_kind(family):
    f = (family or "").lower()
    if any(k in f for k in ("georgia", "times", "serif", "cambria", "garamond")) and "sans" not in f:
        return "serif"
    if any(k in f for k in ("consolas", "courier", "mono")):
        return "mono"
    if any(k in f for k in ("arial", "helvetica", "liberation sans")):
        return "arial"
    return "sans"


def qv_font2(family, size, bold=False, italic=False):
    """(Pillow yazı tipi, sahte_kalın) döndürür. Kalın dosya yoksa çizimde kontur ile kalınlaştırılır."""
    from PIL import ImageFont
    size = max(4, int(round(size)))
    key = (family, size, bool(bold), bool(italic))
    hit = _qv_font_cache.get(key)
    if hit:
        return hit
    f, fake = None, False
    e = _qv_lookup(family)
    if e:
        order = {(0, 0): ("r",), (1, 0): ("b", "r"), (0, 1): ("i", "r"), (1, 1): ("bi", "b", "i", "r")}[
            (int(bool(bold)), int(bool(italic)))]
        for k in order:
            if k in e["files"]:
                try:
                    f = ImageFont.truetype(e["files"][k], size)
                    fake = bool(bold) and "b" not in k
                except OSError:
                    f = None
                break
    if f is None:
        k, i = _qv_kind(family), (1 if bold else 0) + (2 if italic else 0)
        for name in (_QV_FILES[k][i], _QV_FALLBACK[k][i], _QV_FALLBACK["sans"][i]):
            try:
                f = ImageFont.truetype(name, size)
                break
            except OSError:
                continue
    if f is None:
        try:
            f = ImageFont.load_default(size)
        except TypeError:  # eski Pillow
            f = ImageFont.load_default()
    if len(_qv_font_cache) > 400:
        _qv_font_cache.clear()
    _qv_font_cache[key] = (f, fake)
    return f, fake


def qv_font(family, size, bold=False, italic=False):
    return qv_font2(family, size, bold, italic)[0]


def qv_has_turkish(path):
    """Yazı tipi dosyasında Türkçe harfler var mı (eksik glif 'kutu' çizilir; ona benzeyen = yok)."""
    from PIL import Image, ImageDraw, ImageFont
    try:
        f = ImageFont.truetype(path, 48)
    except Exception:  # noqa: BLE001
        return False

    def shot(ch):
        im = Image.new("L", (80, 80), 0)
        ImageDraw.Draw(im).text((8, 4), ch, font=f, fill=255)
        return im.tobytes(), im.getbbox()
    nd = shot("\U0010FFFF")[0]
    for ch in "ğĞşŞıİçÇöÖüÜ":
        data, bb = shot(ch)
        if bb is None or data == nd:
            return False
    return True


def qv_layout(L, ss):
    """Metni kutu genişliğine göre sözcük sözcük kaydırır. (satırlar, yazı tipi, sahte_kalın, satır_yüksekliği)"""
    f, fake = qv_font2(L["family"], L["size"] * ss, L["bold"], L["italic"])
    maxw = max(1.0, L["w"] * ss)
    lines = []
    for para in L["text"].split("\n"):
        cur = ""
        for w in para.split(" "):
            t = w if not cur else cur + " " + w
            if cur and f.getlength(t) > maxw:
                lines.append(cur)
                cur = w
            else:
                cur = t
        lines.append(cur)
        if len(lines) > 300:
            break
    return lines[:300], f, fake, L["size"] * ss * 1.2


def qv_fit_height(L):
    """Metnin kutuya sığması için gereken yükseklik (1x ölçekte)."""
    return max(L["size"] * 1.2, len(qv_layout(L, 1.0)[0]) * L["size"] * 1.2)


def qv_draw_text(dr, L, ss, ox=0.0, oy=0.0, lay=None):
    lines, f, fake, lh = lay or qv_layout(L, ss)
    if not any(lines):
        return
    if max(f.getlength(s) for s in lines) * lh > QV_MAX_TEXT_PIXELS:
        return  # aşırı büyük metin: çizilmez
    y0 = (L["y"] + L["h"] / 2) * ss - oy - lh * len(lines) / 2
    ax = (L["x"] + L["w"] * {"left": 0, "center": .5, "right": 1}[L["align"]]) * ss - ox
    anc = {"left": "lm", "center": "mm", "right": "rm"}[L["align"]]
    kw = dict(stroke_width=max(1, round(L["size"] * ss / 30)), stroke_fill=L["color"]) if fake else {}
    for k, s in enumerate(lines):
        if s:
            dr.text((ax, y0 + lh * (k + 0.5)), s, font=f, fill=L["color"], anchor=anc, **kw)


def qv_text_width(layer, scale=1.0):
    """Katmandaki en uzun satırın piksel genişliği."""
    lines, f, _fk, _lh = qv_layout(layer, scale)
    return max(f.getlength(s) for s in lines) / scale


# ---- saf geometri yardımcıları (arayüzden bağımsız, test edilebilir) ---------
def qv_layer_box(L):
    if L["type"] == "line":
        return min(L["x"], L["x2"]), min(L["y"], L["y2"]), max(L["x"], L["x2"]), max(L["y"], L["y2"])
    return L["x"], L["y"], L["x"] + L["w"], L["y"] + L["h"]


def qv_union(boxes):
    return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))


def qv_hit(L, x, y, tol=0.0):
    """Nokta katmana değiyor mu? Boş (dolgusuz) şekiller yalnızca kenar çizgisinden tutulur."""
    t = L["type"]
    if t == "line":
        x1, y1, x2, y2 = L["x"], L["y"], L["x2"], L["y2"]
        dx, dy = x2 - x1, y2 - y1
        d2 = dx * dx + dy * dy
        u = 0 if d2 == 0 else max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / d2))
        return math.hypot(x - (x1 + u * dx), y - (y1 + u * dy)) <= L["ow"] / 2 + tol
    x1, y1, x2, y2 = qv_layer_box(L)
    if not (x1 - tol <= x <= x2 + tol and y1 - tol <= y <= y2 + tol):
        return False
    hollow = t in ("rect", "ellipse") and not L["fill"]
    band = (L["ow"] / 2 + tol + 2) if hollow else 0
    if t == "ellipse":
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        a, b = (x2 - x1) / 2 + tol, (y2 - y1) / 2 + tol
        if ((x - cx) / a) ** 2 + ((y - cy) / b) ** 2 > 1:
            return False
        if hollow:
            a2, b2 = a - band, b - band
            return not (a2 > 0 and b2 > 0 and ((x - cx) / a2) ** 2 + ((y - cy) / b2) ** 2 < 1)
        return True
    if hollow and x1 + band < x < x2 - band and y1 + band < y < y2 - band:
        return False
    return True


def qv_snap_move(box, dx, dy, tx, ty, thr):
    """Taşınan kutunun kenar/orta çizgilerini hedeflere yapıştırır. -> (dx, dy, x_kılavuzları, y_kılavuzları)"""
    def best(cands, targets, d):
        b = None
        for c in cands:
            for t in targets:
                diff = t - (c + d)
                if abs(diff) <= thr and (b is None or abs(diff) < abs(b)):
                    b = diff
        return b
    xs = (box[0], (box[0] + box[2]) / 2, box[2])
    ys = (box[1], (box[1] + box[3]) / 2, box[3])
    bx, by = best(xs, tx, dx), best(ys, ty, dy)
    if bx is not None:
        dx += bx
    if by is not None:
        dy += by
    gx = sorted({t for t in tx for c in xs if abs(t - (c + dx)) < 0.5})
    gy = sorted({t for t in ty for c in ys if abs(t - (c + dy)) < 0.5})
    return dx, dy, gx, gy


def qv_snap_value(v, targets, thr):
    best = None
    for t in targets:
        if abs(t - v) <= thr and (best is None or abs(t - v) < abs(best - v)):
            best = t
    return (best, True) if best is not None else (v, False)


def qv_resize(b, hd, px, py, keep=False, center=False, mn=4.0):
    """b=(x,y,w,h), hd: 'n','se',… tutaç, (px,py): fare. Yeni (x,y,w,h). Köşede keep=oran korur, center=merkezden."""
    x, y, w, h = b
    cx, cy = x + w / 2, y + h / 2
    l, t, r, bt = x, y, x + w, y + h
    if "w" in hd:
        l = px
    if "e" in hd:
        r = px
    if "n" in hd:
        t = py
    if "s" in hd:
        bt = py
    if center:
        if "w" in hd:
            r = 2 * cx - l
        if "e" in hd:
            l = 2 * cx - r
        if "n" in hd:
            bt = 2 * cy - t
        if "s" in hd:
            t = 2 * cy - bt
    if keep and len(hd) == 2 and w > 0 and h > 0:
        sc = max(abs(r - l) / w, abs(bt - t) / h, mn / min(w, h))
        nw, nh = w * sc, h * sc
        if center:
            l, r, t, bt = cx - nw / 2, cx + nw / 2, cy - nh / 2, cy + nh / 2
        else:
            if "w" in hd:
                l = r - nw
            else:
                r = l + nw
            if "n" in hd:
                t = bt - nh
            else:
                bt = t + nh
    else:
        for axis in "xy":
            lo, hi, plus, minus = (l, r, "e", "w") if axis == "x" else (t, bt, "s", "n")
            if hi - lo < mn and (plus in hd or minus in hd):
                if center:
                    mid = (lo + hi) / 2
                    lo, hi = mid - mn / 2, mid + mn / 2
                elif minus in hd:
                    lo = hi - mn
                else:
                    hi = lo + mn
                if axis == "x":
                    l, r = lo, hi
                else:
                    t, bt = lo, hi
    return l, t, r - l, bt - t


def qv_align_delta(box, ref, mode):
    """box'ı ref içinde hizalamak için (dx, dy). mode: l, ch, r, t, cv, b"""
    if mode == "l":
        return ref[0] - box[0], 0
    if mode == "ch":
        return (ref[0] + ref[2]) / 2 - (box[0] + box[2]) / 2, 0
    if mode == "r":
        return ref[2] - box[2], 0
    if mode == "t":
        return 0, ref[1] - box[1]
    if mode == "cv":
        return 0, (ref[1] + ref[3]) / 2 - (box[1] + box[3]) / 2
    return 0, ref[3] - box[3]


def qv_reorder(layers, sel, mode):
    """mode: front/back/up/down. (yeni_liste, yeni_seçim) döndürür; liste yerinde değişmez."""
    n, ss = len(layers), set(sel)
    order = list(range(n))
    if mode == "front":
        order = [i for i in order if i not in ss] + [i for i in order if i in ss]
    elif mode == "back":
        order = [i for i in order if i in ss] + [i for i in order if i not in ss]
    elif mode == "up":
        for k in range(n - 2, -1, -1):
            if order[k] in ss and order[k + 1] not in ss:
                order[k], order[k + 1] = order[k + 1], order[k]
    elif mode == "down":
        for k in range(1, n):
            if order[k] in ss and order[k - 1] not in ss:
                order[k], order[k - 1] = order[k - 1], order[k]
    return [layers[i] for i in order], [k for k, i in enumerate(order) if i in ss]


# ---- çevrimiçi yazı tipi (Google Fonts, GitHub deposu) -----------------------
def qv_fetch(url, timeout=15, limit=20_000_000):
    req = urllib.request.Request(url, headers={"User-Agent": "qaZNote/1.0", "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Dosya çok büyük")
    return data


def qv_gfont_install(name, fetch=qv_fetch):
    """Google Fonts'tan indirir ve kaydı yeniler. Döndürür: (yazı_tipi_adı, türkçe_tam_mı). Hata: OSError/ValueError."""
    slug, compact = qv_slug(name), re.sub(r"[^A-Za-z0-9]", "", name)
    wanted = {"r": "Regular", "b": "Bold", "i": "Italic", "bi": "BoldItalic"}
    got = {}
    for lic in ("ofl", "apache", "ufl"):
        try:
            lst = json.loads(fetch(f"https://api.github.com/repos/google/fonts/contents/{lic}/{slug}").decode("utf-8"))
        except (OSError, ValueError):
            lst = None
        if isinstance(lst, list):
            files = {d.get("name", ""): d.get("download_url") for d in lst if isinstance(d, dict)}
            for k, suf in wanted.items():
                for fn, url in files.items():
                    if url and fn.lower().endswith(f"-{suf}.ttf".lower()):
                        got[k] = (fn, url)
                        break
            if "r" not in got:  # değişken yazı tipi: tek dosya
                for fn, url in files.items():
                    if url and fn.lower().endswith(".ttf") and "[" in fn and "italic" not in fn.lower():
                        got["r"] = (fn, url)
                        break
            if got:
                break
    if "r" not in got:  # API sınırı/erişilemedi: doğrudan ham adresleri dene
        for lic in ("ofl", "apache"):
            for k, suf in wanted.items():
                fn = f"{compact}-{suf}.ttf"
                got.setdefault(k, (fn, f"https://raw.githubusercontent.com/google/fonts/main/{lic}/{slug}/{fn}"))
            if "r" in got:
                break
    d = os.path.join(qv_user_font_dir(), slug)
    os.makedirs(d, exist_ok=True)
    saved = []
    for k, (fn, url) in got.items():
        try:
            data = fetch(url)
        except OSError:
            if k == "r":
                raise
            continue
        if data[:4] not in (b"\x00\x01\x00\x00", b"OTTO", b"true"):
            if k == "r":
                raise ValueError("Geçerli bir yazı tipi dosyası değil")
            continue
        p = os.path.join(d, re.sub(r"[^A-Za-z0-9._\[\],-]", "_", fn))
        with open(p, "wb") as fh:
            fh.write(data)
        saved.append(p)
    if not saved:
        raise OSError("Yazı tipi indirilemedi")
    qv_scan_fonts(force=True)
    e = _qv_lookup(name)
    return (e["name"] if e else name), qv_has_turkish(saved[0])


# ---- görsel yükleme / Yüklemeler kitaplığı ------------------------------------
QV_IMG_MAX_SIDE = 2400
QV_IMG_MAX_FILE = 60_000_000
QV_ASSET_MAX_TOTAL = 120_000_000
QV_IMG_TYPES = ("*.png", "*.jpg", "*.jpeg", "*.jpe", "*.jfif", "*.webp", "*.bmp", "*.gif", "*.tif", "*.tiff", "*.ico")
QV_IMG_EXTS = tuple(p[1:] for p in QV_IMG_TYPES)


def qv_prepare_image(src):
    """Dosya yolu, bayt veya PIL görüntüsünden (veri, genişlik, yükseklik, uzantı) üretir. Hata: ValueError."""
    from PIL import Image, ImageOps
    RS = getattr(Image, "Resampling", Image)
    try:
        if isinstance(src, str):
            if os.path.getsize(src) > QV_IMG_MAX_FILE:
                raise ValueError("Dosya çok büyük (en fazla 60 MB)")
            im = Image.open(src)
        elif isinstance(src, (bytes, bytearray)):
            im = Image.open(io.BytesIO(bytes(src)))
        else:
            im = src
        im.load()
        im = ImageOps.exif_transpose(im) or im
    except ValueError:
        raise
    except Exception as e:  # noqa: BLE001
        raise ValueError("Görsel açılamadı: " + (str(e) or e.__class__.__name__)[:80])
    alpha = im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info)
    im = im.convert("RGBA" if alpha else "RGB")
    if max(im.size) > QV_IMG_MAX_SIDE:
        im.thumbnail((QV_IMG_MAX_SIDE, QV_IMG_MAX_SIDE), RS.LANCZOS)
    if alpha and im.getchannel("A").getextrema()[0] == 255:
        im, alpha = im.convert("RGB"), False
    buf = io.BytesIO()
    if alpha:
        im.save(buf, "PNG")
        ext = "png"
    else:
        im.save(buf, "JPEG", quality=92)
        ext = "jpg"
    return buf.getvalue(), im.width, im.height, ext


def qv_uploads_dir():
    d = os.path.join(_data_dir(), "qv_uploads")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass
    return d


def qv_lib_path(iid, ext):
    return os.path.join(qv_uploads_dir(), f"{iid}.{ext}")


def qv_lib_thumb(iid):
    return os.path.join(qv_uploads_dir(), f"{iid}_t.png")


def qv_lib_list():
    d = read_json(os.path.join(qv_uploads_dir(), "index.json"))
    out = []
    for e in d.get("items", []) if isinstance(d.get("items"), list) else []:
        if (isinstance(e, dict) and re.fullmatch(r"[0-9a-f]{16}", str(e.get("id", ""))) and e.get("ext") in ("png", "jpg")
                and os.path.isfile(qv_lib_path(e["id"], e["ext"]))):
            out.append(e)
    return out


def qv_lib_add(src, name="Görsel"):
    """Görseli işler ve kitaplığa ekler; kayıt (dict) döndürür. Aynı görsel ikinci kez eklenmez."""
    from PIL import Image
    data, w, h, ext = qv_prepare_image(src)
    iid = hashlib.sha1(data).hexdigest()[:16]
    items = qv_lib_list()
    for e in items:
        if e["id"] == iid:
            return e
    try:
        with open(qv_lib_path(iid, ext), "wb") as f:
            f.write(data)
        th = Image.open(io.BytesIO(data))
        th.thumbnail((240, 240))
        th.save(qv_lib_thumb(iid), "PNG")
    except OSError as ex:
        raise ValueError(f"Kaydedilemedi: {ex}")
    e = dict(id=iid, name=str(name)[:80] or "Görsel", w=w, h=h, ext=ext, added=int(time.time()))
    items.insert(0, e)
    for old in items[300:]:
        for p in (qv_lib_path(old["id"], old["ext"]), qv_lib_thumb(old["id"])):
            try:
                os.remove(p)
            except OSError:
                pass
    write_json(os.path.join(qv_uploads_dir(), "index.json"), {"items": items[:300]})
    return e


def qv_lib_remove(iid):
    items = qv_lib_list()
    for e in items:
        if e["id"] == iid:
            for p in (qv_lib_path(iid, e["ext"]), qv_lib_thumb(iid)):
                try:
                    os.remove(p)
                except OSError:
                    pass
    write_json(os.path.join(qv_uploads_dir(), "index.json"), {"items": [e for e in items if e["id"] != iid]})


_QV_THUMBS = {}


def qv_thumb(e, w, h):
    """Kitaplık küçük resmi (Tk PhotoImage); yoksa None."""
    key = (e["id"], w, h)
    ph = _QV_THUMBS.get(key)
    if ph is None:
        try:
            im = _PILImage.open(qv_lib_thumb(e["id"]))
            im.thumbnail((w, h))
            ph = im.convert("RGBA")
        except Exception:  # noqa: BLE001
            return None
        if len(_QV_THUMBS) > 400:
            _QV_THUMBS.clear()
        _QV_THUMBS[key] = ph
    return ph


# ---- belge -----------------------------------------------------------------
class QvDoc:
    def __init__(self, w, h, bg="#ffffff", bg2=None, name="Adsız tasarım", layers=None, assets=None):
        self.w, self.h = qv_check_size(w, h)
        self.bg, self.bg2 = _qv_hex(bg, "#ffffff"), _qv_hex(bg2)
        self.name = str(name)[:80]
        self.layers = list(layers or [])
        self.assets = dict(assets or {})  # kimlik -> {name, data(base64), w, h}
        self._pil = {}

    # -- gömülü görseller
    def add_asset(self, aid, data, name, w, h):
        if aid in self.assets:
            return aid
        b64 = base64.b64encode(data).decode("ascii")
        if sum(len(a["data"]) for a in self.assets.values()) + len(b64) > QV_ASSET_MAX_TOTAL:
            raise ValueError("Belgedeki görseller çok yer kaplıyor")
        self.assets[aid] = dict(name=str(name)[:80], data=b64, w=int(w), h=int(h))
        return aid

    def asset_image(self, aid):
        """Gömülü görselin RGBA PIL görüntüsü (önbellekli); yoksa/bozuksa None."""
        im = self._pil.get(aid)
        if im is None:
            a = self.assets.get(aid)
            if not a:
                return None
            from PIL import Image
            try:
                im = Image.open(io.BytesIO(base64.b64decode(a["data"])))
                im.load()
                im = im.convert("RGBA")
            except Exception:  # noqa: BLE001
                return None
            if len(self._pil) > 6:
                self._pil.clear()
            self._pil[aid] = im
        return im

    # -- katman işlemleri
    def add(self, **kw):
        if len(self.layers) >= QV_MAX_LAYERS:
            raise ValueError("Katman sınırına ulaşıldı")
        L = qv_clean_layer(kw)
        if L is None:
            raise ValueError("Geçersiz katman türü")
        self.layers.append(L)
        return len(self.layers) - 1

    def remove(self, i):
        if 0 <= i < len(self.layers):
            del self.layers[i]

    def move_z(self, i, delta):
        j = i + delta
        if 0 <= i < len(self.layers) and 0 <= j < len(self.layers):
            self.layers[i], self.layers[j] = self.layers[j], self.layers[i]
            return j
        return i

    def hit(self, x, y):
        """(x, y) noktasındaki en üstteki katmanın indeksi; yoksa -1."""
        for i in range(len(self.layers) - 1, -1, -1):
            a, b, c, d = self.bbox(i)
            if a <= x <= c and b <= y <= d:
                return i
        return -1

    def bbox(self, i):
        L = self.layers[i]
        if L["type"] == "line":
            pad = L["ow"] / 2 + 4
            return (min(L["x"], L["x2"]) - pad, min(L["y"], L["y2"]) - pad,
                    max(L["x"], L["x2"]) + pad, max(L["y"], L["y2"]) + pad)
        return L["x"], L["y"], L["x"] + L["w"], L["y"] + L["h"]

    def translate(self, i, dx, dy):
        L = self.layers[i]
        L["x"] += dx
        L["y"] += dy
        if L["type"] == "line":
            L["x2"] += dx
            L["y2"] += dy

    # -- kaydet / yükle
    def to_dict(self):
        d = dict(format="qanvas", version=1, name=self.name, w=self.w, h=self.h,
                 bg=self.bg, bg2=self.bg2, layers=self.layers)
        used = {L["asset"] for L in self.layers if L["type"] == "image"}
        if used:
            d["assets"] = {k: v for k, v in self.assets.items() if k in used}
        return d

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict) or d.get("format") != "qanvas":
            raise ValueError("Geçerli bir qAnvas dosyası değil")
        layers = [L for L in map(qv_clean_layer, (d.get("layers") or [])[:QV_MAX_LAYERS]) if L]
        assets, total = {}, 0
        raw = d.get("assets")
        if isinstance(raw, dict):
            for k, v in list(raw.items())[:300]:
                if (isinstance(k, str) and re.fullmatch(r"[0-9a-f]{8,64}", k) and isinstance(v, dict)
                        and isinstance(v.get("data"), str)):
                    total += len(v["data"])
                    if total > QV_ASSET_MAX_TOTAL:
                        break
                    assets[k] = dict(name=str(v.get("name", ""))[:80], data=v["data"],
                                     w=int(_qv_num(v.get("w"), 0, 0, 100000)), h=int(_qv_num(v.get("h"), 0, 0, 100000)))
        return cls(d.get("w"), d.get("h"), d.get("bg"), d.get("bg2"), d.get("name", "Adsız tasarım"), layers, assets)

    def save(self, path):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False)
        os.replace(tmp, path)

    # -- çizim
    def _draw_image(self, img, dr, L, ss):
        from PIL import Image
        RS = getattr(Image, "Resampling", Image)
        W, H = max(1, int(round(L["w"] * ss))), max(1, int(round(L["h"] * ss)))
        px, py = int(round(L["x"] * ss)), int(round(L["y"] * ss))
        x0, y0 = max(0, -px), max(0, -py)
        x1, y1 = min(W, img.width - px), min(H, img.height - py)
        if x1 <= x0 or y1 <= y0:
            return  # tuvalin dışında
        src = self.asset_image(L["asset"])
        if src is None:
            dr.rectangle([px + x0, py + y0, px + x1 - 1, py + y1 - 1], fill="#d1d5db", outline="#9ca3af")
            return
        sw, sh = src.size
        box = (x0 * sw / W, y0 * sh / H, x1 * sw / W, y1 * sh / H)
        im = src.resize((x1 - x0, y1 - y0), RS.LANCZOS, box=box)
        if L["opacity"] < 0.999:
            op = L["opacity"]
            im.putalpha(im.getchannel("A").point(lambda a: int(a * op)))
        img.paste(im, (px + x0, py + y0), im)

    def _draw_gradient(self, img, L, t, box, rad, ss):
        """Dikey gradyan dolgu (fill -> fill2); şekil (dikdörtgen/yuvarlak köşe/elips) maskesine yapıştırılır."""
        from PIL import Image, ImageDraw
        x0, y0 = int(round(box[0])), int(round(box[1]))
        W, H = max(1, int(round(box[2] - box[0])) + 1), max(1, int(round(box[3] - box[1])) + 1)
        c1 = [int(L["fill"][i:i + 2], 16) for i in (1, 3, 5)]
        c2 = [int(L["fill2"][i:i + 2], 16) for i in (1, 3, 5)]
        strip = Image.new("RGB", (1, H))
        strip.putdata([tuple(round(a + (b - a) * y / max(1, H - 1)) for a, b in zip(c1, c2)) for y in range(H)])
        grad = strip.resize((W, H))
        mask = Image.new("L", (W, H), 0)
        md = ImageDraw.Draw(mask)
        local = [0, 0, W - 1, H - 1]
        if t == "ellipse":
            md.ellipse(local, fill=255)
        elif L["rad"] > 0:
            md.rounded_rectangle(local, radius=rad, fill=255)
        else:
            md.rectangle(local, fill=255)
        img.paste(grad, (x0, y0), mask)

    def _draw_layer(self, dr, L, ss, img=None):
        t = L["type"]
        if t == "image":
            if img is not None:
                self._draw_image(img, dr, L, ss)
        elif t in ("rect", "ellipse"):
            box = [L["x"] * ss, L["y"] * ss, (L["x"] + L["w"]) * ss - 1, (L["y"] + L["h"]) * ss - 1]
            ow = int(round(L["ow"] * ss)) if L["outline"] else 0
            kw = dict(fill=L["fill"], outline=L["outline"], width=ow)
            rad = min(L["rad"], L["w"] / 2, L["h"] / 2) * ss
            if L.get("fill2") and L["fill"] and img is not None:
                self._draw_gradient(img, L, t, box, rad, ss)
                kw = dict(fill=None, outline=L["outline"], width=ow)
            if t == "ellipse":
                dr.ellipse(box, **kw)
            elif L["rad"] > 0:
                dr.rounded_rectangle(box, radius=rad, **kw)
            else:
                dr.rectangle(box, **kw)
        elif t == "line":
            dr.line([L["x"] * ss, L["y"] * ss, L["x2"] * ss, L["y2"] * ss], fill=L["color"],
                    width=max(1, int(round(L["ow"] * ss))))
        elif t == "text" and L["text"]:
            qv_draw_text(dr, L, ss)

    def render(self, max_ss_pixels=8_000_000):
        """Pillow ile RGB görüntü üretir. Küçük tuvallerde 2x süper örnekleme (yumuşak kenar)."""
        from PIL import Image, ImageDraw
        ss = 2 if self.w * self.h <= max_ss_pixels else 1
        W, H = self.w * ss, self.h * ss
        if self.bg2:
            c1 = [int(self.bg[i:i + 2], 16) for i in (1, 3, 5)]
            c2 = [int(self.bg2[i:i + 2], 16) for i in (1, 3, 5)]
            strip = Image.new("RGB", (1, H))
            strip.putdata([tuple(round(a + (b - a) * y / max(1, H - 1)) for a, b in zip(c1, c2))
                           for y in range(H)])
            img = strip.resize((W, H))
        else:
            img = Image.new("RGB", (W, H), self.bg)
        dr = ImageDraw.Draw(img)
        for L in self.layers:
            try:
                self._draw_layer(dr, L, ss, img)
            except Exception:  # noqa: BLE001  bozuk/aşırı büyük katman diğerlerini bozmasın
                continue
        if ss > 1:
            img = img.resize((self.w, self.h), getattr(getattr(Image, "Resampling", Image), "BOX"))
        return img

    def export(self, path):
        """Uzantıya göre PNG / JPG yazar."""
        img = self.render()
        ext = os.path.splitext(path)[1].lower()
        if ext in (".jpg", ".jpeg"):
            img.save(path, "JPEG", quality=95)
        elif ext == ".pdf":
            img.save(path, "PDF", resolution=150.0)
        else:
            img.save(path, "PNG")
        return path


# ---- şablonlar -------------------------------------------------------------
class _Build:
    """Şablon yazarken oranlarla (0–1) çalışmayı sağlar; piksele çevirir."""

    def __init__(self, w, h):
        self.W, self.H, self.m, self.layers = w, h, min(w, h), []

    def rect(self, x, y, w, h, fill, rad=0.0, outline=None, ow=0.0):
        self.layers.append(dict(type="rect", x=x * self.W, y=y * self.H, w=w * self.W, h=h * self.H, fill=fill,
                                outline=outline, ow=ow * self.m, rad=rad * self.m))

    def circ(self, cx, cy, d, fill, outline=None, ow=0.0):
        """Daire: merkez (cx, cy) oran, çap d = kısa kenarın oranı."""
        r = d * self.m / 2
        self.layers.append(dict(type="ellipse", x=cx * self.W - r, y=cy * self.H - r, w=2 * r, h=2 * r,
                                fill=fill, outline=outline, ow=ow * self.m, rad=0))

    def line(self, x, y, x2, y2, color, ow=0.01):
        self.layers.append(dict(type="line", x=x * self.W, y=y * self.H, x2=x2 * self.W, y2=y2 * self.H,
                                color=color, ow=max(1, ow * self.m)))

    def text(self, s, x, y, w, h, size, color, bold=False, align="center", family="Segoe UI", italic=False):
        """size: yüksekliğin oranı."""
        self.layers.append(dict(type="text", x=x * self.W, y=y * self.H, w=w * self.W, h=h * self.H, text=s,
                                size=size * self.H, color=color, family=family, bold=bold, italic=italic,
                                align=align))


QV_TEMPLATES = []


def _tpl(tid, cat, name, w, h, bg, bg2=None):
    def deco(fn):
        QV_TEMPLATES.append(dict(id=tid, cat=cat, name=name, w=w, h=h, bg=bg, bg2=bg2, build=fn))
        return fn
    return deco


# --- Logo
@_tpl("logo-monogram", "Logo", "Monogram Daire", 1024, 1024, "#0f172a")
def _(b):
    b.circ(.5, .42, .56, None, "#38bdf8", .022)
    b.text("Q", .2, .22, .6, .4, .34, "#ffffff", True)
    b.text("MARKA ADI", .1, .74, .8, .1, .075, "#ffffff", True)
    b.text("Slogan buraya", .1, .84, .8, .06, .04, "#94a3b8")


@_tpl("logo-rozet", "Logo", "Modern Rozet", 1024, 1024, "#6d28d9", "#2563eb")
def _(b):
    b.rect(.2, .2, .6, .6, "#ffffff", .12)
    b.text("Aa", .2, .3, .6, .3, .24, "#4c1d95", True)
    b.text("Markanız", .2, .6, .6, .12, .08, "#1e293b", True)


@_tpl("logo-minimal", "Logo", "Minimal Yazı Logosu", 1024, 1024, "#fafaf9")
def _(b):
    b.text("studio", .1, .34, .8, .22, .17, "#1c1917", False, "center", "Georgia", True)
    b.line(.32, .58, .68, .58, "#1c1917", .004)
    b.text("TASARIM ATÖLYESİ", .1, .62, .8, .07, .04, "#57534e", True)


@_tpl("logo-gundogumu", "Logo", "Gün Doğumu", 1024, 1024, "#f97316", "#ec4899")
def _(b):
    b.circ(.5, .46, .5, "#fde68a")
    b.rect(0, .5, 1, .5, "#9d174d")
    b.line(.15, .6, .85, .6, "#fde68a", .006)
    b.line(.25, .68, .75, .68, "#fde68a", .006)
    b.text("GÜN DOĞUMU", .05, .8, .9, .1, .075, "#ffffff", True)


# --- Video kapağı
@_tpl("vid-baslik", "Video Kapağı", "Büyük Başlık", 1920, 1080, "#0f0f1a", "#312e81")
def _(b):
    b.rect(.06, .16, .16, .09, "#facc15", .02)
    b.text("YENİ", .06, .16, .16, .09, .06, "#111827", True)
    b.text("Videonun Başlığı\nBurada Olacak", .06, .3, .88, .42, .15, "#ffffff", True, "left")
    b.rect(.06, .78, .3, .012, "#facc15")
    b.text("Alt başlık veya kanal adı", .06, .82, .7, .08, .05, "#c7d2fe", False, "left")


@_tpl("vid-bolunmus", "Video Kapağı", "Bölünmüş", 1920, 1080, "#111827")
def _(b):
    b.rect(0, 0, .5, 1, "#ef4444")
    b.text("TOP 10", .03, .12, .44, .26, .17, "#ffffff", True)
    b.text("Kaçırmamanız\nGerekenler", .03, .42, .44, .34, .09, "#fee2e2", True)
    b.circ(.75, .5, .55, "#1f2937", "#ffffff", .012)
    b.text("GÖRSEL", .55, .44, .4, .12, .06, "#9ca3af", True)


@_tpl("vid-oyun", "Video Kapağı", "Neon Sahne", 1920, 1080, "#020617", "#4c1d95")
def _(b):
    b.rect(.05, .08, .9, .84, None, .03, "#22d3ee", .008)
    b.text("BÖLÜM 07", .08, .14, .84, .1, .06, "#22d3ee", True)
    b.text("FİNAL\nKARŞILAŞMASI", .08, .28, .84, .46, .16, "#f0abfc", True)
    b.text("Canlı yayın kaydı", .08, .78, .84, .08, .045, "#e2e8f0")


@_tpl("vid-egitim", "Video Kapağı", "Eğitim Serisi", 1920, 1080, "#f8fafc")
def _(b):
    b.rect(0, 0, .035, 1, "#2563eb")
    b.text("BÖLÜM 01", .08, .2, .6, .1, .06, "#2563eb", True, "left")
    b.text("Sıfırdan Başlayarak\nÖğren", .08, .34, .8, .38, .115, "#0f172a", True, "left")
    b.text("Başlangıç seviyesi · 12 ders", .08, .78, .8, .08, .045, "#64748b", False, "left")


# --- Sosyal medya
@_tpl("sm-alinti", "Sosyal Medya", "Alıntı Gönderisi", 1080, 1080, "#fde68a", "#fb923c")
def _(b):
    b.text("“", .06, .02, .3, .3, .25, "#7c2d12", True, "left", "Georgia")
    b.text("Küçük adımlar,\nbüyük yolculuklar\nbaşlatır.", .1, .26, .8, .44, .075, "#431407", True, "center", "Georgia")
    b.line(.4, .76, .6, .76, "#7c2d12", .005)
    b.text("— Yazar Adı", .1, .8, .8, .08, .045, "#7c2d12")


@_tpl("sm-duyuru", "Sosyal Medya", "Duyuru (Dikey Gönderi)", 1080, 1350, "#0ea5e9", "#1e3a8a")
def _(b):
    b.rect(.08, .08, .3, .06, "#ffffff", .03)
    b.text("DUYURU", .08, .08, .3, .06, .035, "#1e3a8a", True)
    b.text("Büyük\nHaber!", .08, .24, .84, .36, .14, "#ffffff", True, "left")
    b.text("Tarih · Saat · Yer bilgisini\nburaya yazabilirsin.", .08, .64, .84, .16, .04, "#bae6fd", False, "left")
    b.rect(.08, .84, .4, .08, "#facc15", .04)
    b.text("Detaylar", .08, .84, .4, .08, .04, "#1e3a8a", True)


@_tpl("sm-hikaye", "Sosyal Medya", "Yeni Ürün (Hikâye)", 1080, 1920, "#18181b", "#be185d")
def _(b):
    b.circ(.5, .4, .62, "#fbcfe8")
    b.text("ÜRÜN\nGÖRSELİ", .2, .34, .6, .12, .04, "#9d174d", True)
    b.text("YENİ", .1, .08, .8, .08, .06, "#ffffff", True)
    b.text("Koleksiyon\nyayında", .08, .68, .84, .14, .06, "#ffffff", True)
    b.rect(.25, .86, .5, .05, "#ffffff", .025)
    b.text("Yukarı kaydır", .25, .86, .5, .05, .022, "#be185d", True)


@_tpl("sm-fb-kapak", "Sosyal Medya", "Facebook Kapak", 1640, 624, "#1e293b", "#0f766e")
def _(b):
    b.text("Sayfa Adı", .06, .24, .6, .3, .22, "#ffffff", True, "left")
    b.text("Kısa bir tanıtım cümlesi", .06, .58, .6, .14, .09, "#99f6e4", False, "left")
    b.circ(.84, .5, .62, None, "#5eead4", .02)


@_tpl("sm-x-baslik", "Sosyal Medya", "X Başlık", 1500, 500, "#111827", "#1d4ed8")
def _(b):
    b.text("@kullaniciadi", .06, .3, .6, .2, .15, "#ffffff", True, "left")
    b.text("Biyografi veya slogan", .06, .54, .6, .14, .09, "#bfdbfe", False, "left")


@_tpl("sm-linkedin", "Sosyal Medya", "LinkedIn Banner", 1584, 396, "#0b3d62", "#0a66c2")
def _(b):
    b.text("Ad Soyad · Unvan", .3, .24, .66, .26, .17, "#ffffff", True, "left")
    b.text("Uzmanlık alanı · Şehir", .3, .54, .66, .18, .11, "#cfe6fa", False, "left")
    b.circ(.14, .5, .7, "#ffffff", None, 0)


@_tpl("sm-yt-banner", "Sosyal Medya", "YouTube Kanal Bannerı", 2560, 1440, "#0f172a", "#7c3aed")
def _(b):
    b.text("KANAL ADI", .2, .36, .6, .16, .13, "#ffffff", True)
    b.text("Her Salı yeni video", .2, .54, .6, .08, .05, "#ddd6fe")


# --- Sunum & baskı
@_tpl("sun-baslik", "Sunum ve Baskı", "Sunum Başlık Slaytı", 1920, 1080, "#ffffff")
def _(b):
    b.rect(0, 0, 1, .06, "#0f766e")
    b.text("Sunum Başlığı", .08, .3, .84, .22, .13, "#0f172a", True, "left")
    b.text("Alt başlık · Konuşmacı · Tarih", .08, .54, .84, .1, .05, "#475569", False, "left")
    b.rect(.08, .7, .12, .01, "#0f766e")


@_tpl("bas-afis", "Sunum ve Baskı", "Etkinlik Afişi (A4)", 2480, 3508, "#fef3c7", "#fbbf24")
def _(b):
    b.rect(.06, .04, .88, .92, None, .02, "#78350f", .006)
    b.text("FESTİVAL", .1, .1, .8, .08, .06, "#78350f", True)
    b.text("YAZ\nŞENLİĞİ", .1, .22, .8, .3, .11, "#451a03", True, "center", "Georgia")
    b.circ(.5, .64, .36, "#f59e0b")
    b.text("12 Temmuz · 19:00", .1, .84, .8, .05, .03, "#451a03", True)


@_tpl("bas-kartvizit", "Sunum ve Baskı", "Kartvizit", 1050, 600, "#ffffff")
def _(b):
    b.rect(0, 0, .04, 1, "#0f172a")
    b.text("Ad Soyad", .1, .16, .8, .2, .13, "#0f172a", True, "left")
    b.text("Unvan", .1, .38, .8, .1, .07, "#64748b", False, "left")
    b.text("0 (500) 000 00 00\nad@ornek.com", .1, .62, .8, .24, .075, "#0f172a", False, "left")


@_tpl("bas-davetiye", "Sunum ve Baskı", "Davetiye (A5)", 1748, 2480, "#fdf2f8")
def _(b):
    b.rect(.07, .05, .86, .9, None, .0, "#be185d", .004)
    b.text("DAVETLİSİNİZ", .1, .14, .8, .06, .03, "#be185d", True)
    b.text("Ayşe & Mehmet", .1, .3, .8, .14, .07, "#831843", False, "center", "Georgia", True)
    b.line(.35, .48, .65, .48, "#be185d", .003)
    b.text("20 Eylül 2026 · 18:30\nMekân adı, İstanbul", .1, .52, .8, .14, .035, "#831843")


@_tpl("web-blog", "Sunum ve Baskı", "Blog / Web Kapak Görseli", 1200, 630, "#0f172a", "#134e4a")
def _(b):
    b.text("Yazı başlığı iki satıra\nrahatça sığar", .06, .2, .88, .5, .13, "#ffffff", True, "left")
    b.text("site-adi.com", .06, .76, .5, .1, .06, "#5eead4", True, "left")


# --- Yeni şablonlar (v2)
@_tpl("logo-golge", "Logo", "Gölge Harf", 1024, 1024, "#fff7ed")
def _(b):
    b.circ(.5, .44, .62, "#fb923c")
    b.circ(.53, .47, .62, None, "#7c2d12", .014)
    b.text("Q", .2, .2, .6, .48, .36, "#ffffff", True)
    b.text("Marka Adı", .1, .78, .8, .1, .07, "#7c2d12", True)


@_tpl("logo-damga", "Logo", "Damga", 1024, 1024, "#ecfeff")
def _(b):
    b.rect(.14, .14, .72, .72, None, .04, "#0e7490", .016)
    b.rect(.2, .2, .6, .6, None, .02, "#0e7490", .006)
    b.text("ATÖLYE", .22, .34, .56, .16, .11, "#155e75", True)
    b.line(.34, .54, .66, .54, "#0e7490", .006)
    b.text("EST. 2026", .22, .58, .56, .08, .045, "#0e7490", False)


@_tpl("vid-podcast", "Video Kapağı", "Podcast Bölümü", 1920, 1080, "#1e1b4b", "#7c3aed")
def _(b):
    b.circ(.8, .5, .62, "#a78bfa")
    b.circ(.8, .5, .46, "#4c1d95")
    b.text("BÖLÜM 12", .06, .2, .5, .08, .06, "#c4b5fd", True, "left")
    b.text("Konuk ile\nkonuşuyoruz", .06, .32, .58, .38, .12, "#ffffff", True, "left")
    b.text("Podcast adı", .06, .78, .5, .08, .05, "#ddd6fe", False, "left")


@_tpl("vid-vlog", "Video Kapağı", "Vlog Sade", 1920, 1080, "#fef08a", "#facc15")
def _(b):
    b.rect(.05, .1, .9, .8, None, .03, "#111827", .012)
    b.text("BİR GÜN", .08, .22, .84, .24, .2, "#111827", True)
    b.text("benimle", .08, .5, .84, .2, .16, "#111827", False, "center", "Georgia", True)


@_tpl("sm-indirim", "Sosyal Medya", "İndirim Gönderisi", 1080, 1080, "#dc2626", "#7f1d1d")
def _(b):
    b.circ(.5, .46, .7, "#fef2f2")
    b.text("%50", .2, .3, .6, .3, .26, "#dc2626", True)
    b.text("BÜYÜK İNDİRİM", .1, .72, .8, .1, .07, "#ffffff", True)
    b.text("Sadece bu hafta sonu", .1, .83, .8, .06, .04, "#fecaca")


@_tpl("sm-soru", "Sosyal Medya", "Soru Hikâyesi", 1080, 1920, "#0f766e", "#134e4a")
def _(b):
    b.rect(.1, .3, .8, .36, "#ffffff", .05)
    b.text("Bana bir şey sor", .14, .34, .72, .12, .035, "#0f766e", True)
    b.rect(.14, .48, .72, .12, "#ccfbf1", .03)
    b.text("Sorunu buraya yaz…", .16, .5, .68, .08, .026, "#115e59", False, "left")


@_tpl("sun-tesekkur", "Sunum ve Baskı", "Teşekkürler Slaytı", 1920, 1080, "#0f172a", "#1d4ed8")
def _(b):
    b.text("Teşekkürler", .08, .3, .84, .28, .17, "#ffffff", True)
    b.line(.4, .62, .6, .62, "#93c5fd", .006)
    b.text("ad.soyad@site.com", .08, .68, .84, .1, .05, "#bfdbfe")


@_tpl("bas-menu", "Sunum ve Baskı", "Menü Kartı (A5)", 1748, 2480, "#fffbeb")
def _(b):
    b.text("MENÜ", .1, .08, .8, .1, .06, "#78350f", True)
    b.line(.3, .2, .7, .2, "#b45309", .003)
    b.text("Çorba\nAna yemek\nTatlı", .1, .26, .8, .36, .05, "#92400e", False, "center", "Georgia", True)
    b.text("Afiyet olsun", .1, .78, .8, .08, .035, "#b45309")


def qv_categories(ed):
    """Sürüme göre kullanılabilir kategoriler."""
    if not qv_access(ed)["full"]:
        return []
    cats = ["Hazır Boyutlar"]
    for t in QV_TEMPLATES:
        if t["cat"] not in cats:
            cats.append(t["cat"])
    return cats + [QV_ONLINE_CAT]


def qv_template_list(ed, cat=None):
    if not qv_access(ed)["templates"]:
        raise QvPermissionError("Şablon kitaplığı Enterprise ve Professional sürümlerinde")
    return [t for t in QV_TEMPLATES if cat in (None, t["cat"])]


# ---- belge oluşturma (sürüm kontrolü burada) -------------------------------
def qv_new_preset(ed, preset_id):
    """Core dâhil herkes: 3 hazır boyut. Enterprise/Pro: ek boyutlar da."""
    pool = list(QV_CORE_PRESETS) + (list(QV_EXTRA_SIZES) if qv_access(ed)["full"] else [])
    for p in pool:
        if p["id"] == preset_id:
            return QvDoc(p["w"], p["h"], "#ffffff", name=p["name"])
    raise QvPermissionError("Bu boyut sürümünüzde yok" if any(p["id"] == preset_id for p in QV_EXTRA_SIZES)
                            else "Bilinmeyen boyut")


def qv_new_custom(ed, w, h):
    if not qv_access(ed)["custom"]:
        raise QvPermissionError("Özel çözünürlük Enterprise ve Professional sürümlerinde")
    w, h = qv_check_size(w, h)
    return QvDoc(w, h, "#ffffff", name=f"Özel {w}×{h}")


def qv_new_template(ed, tid):
    if not qv_access(ed)["templates"]:
        raise QvPermissionError("Şablon kitaplığı Enterprise ve Professional sürümlerinde")
    for t in QV_TEMPLATES:
        if t["id"] == tid:
            b = _Build(t["w"], t["h"])
            t["build"](b)
            return QvDoc(t["w"], t["h"], t["bg"], t["bg2"], t["name"], [qv_clean_layer(L) for L in b.layers])
    raise ValueError("Şablon bulunamadı")


def qv_load(ed, path):
    """Dosyadan yükler. Core'da yalnızca hazır boyutlardaki belgeler açılır."""
    with open(path, "r", encoding="utf-8") as f:
        doc = QvDoc.from_dict(json.load(f))
    if not qv_access(ed)["custom"] and (doc.w, doc.h) not in {(p["w"], p["h"]) for p in QV_CORE_PRESETS}:
        raise QvPermissionError("Bu belgenin boyutu Core sürümünde açılamaz (Enterprise/Professional gerekir)")
    return doc


# ---- internet şablonları (Fabric.js JSON -> qAnvas) --------------------------
QV_ONLINE_CAT = "İnternet"
QV_ONLINE_SOURCES = (
    dict(id="opendesign", name="OpenDesign", cat="LinkedIn", kind="ts",
         url="https://raw.githubusercontent.com/clawnify/OpenDesign/main/src/server/seed-templates.ts",
         info="OpenDesign (MIT) · github.com/clawnify/OpenDesign"),
)


def _qv_css_hex(c):
    """CSS/Fabric renk metnini '#rrggbb'e çevirir; desteklenmiyorsa/saydamsa None."""
    if not isinstance(c, str):
        return None
    c = c.strip().lower()
    m = re.fullmatch(r"#([0-9a-f])([0-9a-f])([0-9a-f])", c)
    if m:
        return "#" + "".join(ch * 2 for ch in m.groups())
    if re.fullmatch(r"#[0-9a-f]{6}", c):
        return c
    if re.fullmatch(r"#[0-9a-f]{8}", c):
        return c[:7]
    m = re.fullmatch(r"rgba?\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)(?:[\s,/]+([\d.]+))?\s*\)", c)
    if m:
        if m[4] is not None and float(m[4]) < 0.05:
            return None
        return "#%02x%02x%02x" % tuple(min(255, int(m[i])) for i in (1, 2, 3))
    return {"white": "#ffffff", "black": "#000000", "red": "#ff0000"}.get(c)


def qv_http_url(url):
    u = urllib.parse.urlparse(str(url).strip())
    if u.scheme not in ("http", "https") or not u.netloc:
        raise ValueError("Adres http:// ya da https:// ile başlamalı")
    return u.geturl()


def qv_fetch_image(src):
    """Fabric 'image' nesnesinin kaynağını (data: ya da http) bayt olarak getirir; olmazsa None."""
    try:
        if src.startswith("data:"):
            return base64.b64decode(src.split(",", 1)[1])
        return qv_fetch(qv_http_url(src), 15, 15_000_000)
    except Exception:  # noqa: BLE001
        return None


def qv_from_fabric(js, name="Şablon", w=None, h=None, fetch_img=qv_fetch_image):
    """Fabric.js JSON'unu (rect, circle, ellipse, line, textbox/text, image) qAnvas belgesine çevirir.
    Döndürür: (belge, atlanan_nesne_sayısı). Dönme ve gruplar desteklenmez (atlanır/yok sayılır)."""
    if not isinstance(js, dict) or not isinstance(js.get("objects"), list):
        raise ValueError("Fabric.js şablonu değil")
    W = int(_qv_num(w or js.get("width"), 1080, QV_MIN, QV_MAX))
    H = int(_qv_num(h or js.get("height"), 1080, QV_MIN, QV_MAX))
    doc = QvDoc(W, H, _qv_css_hex(js.get("background")) or "#ffffff", name=name)
    skipped = 0
    for o in js["objects"][:300]:
        if not isinstance(o, dict):
            continue
        t = str(o.get("type", "")).lower()
        sx, sy = _qv_num(o.get("scaleX"), 1, 0.01, 100), _qv_num(o.get("scaleY"), 1, 0.01, 100)
        ow, oh = _qv_num(o.get("width"), 0, 0, 1e5) * sx, _qv_num(o.get("height"), 0, 0, 1e5) * sy
        if t == "circle":
            ow = oh = 2 * _qv_num(o.get("radius"), 0, 0, 1e5) * sx
        elif t == "ellipse":
            ow, oh = 2 * _qv_num(o.get("rx"), 0, 0, 1e5) * sx, 2 * _qv_num(o.get("ry"), 0, 0, 1e5) * sy
        x, y = _qv_num(o.get("left")), _qv_num(o.get("top"))
        ox_, oy_ = o.get("originX", "left"), o.get("originY", "top")
        x -= ow / 2 if ox_ == "center" else (ow if ox_ == "right" else 0)
        y -= oh / 2 if oy_ == "center" else (oh if oy_ == "bottom" else 0)
        fill, stroke = _qv_css_hex(o.get("fill")), _qv_css_hex(o.get("stroke"))
        sw = _qv_num(o.get("strokeWidth"), 0, 0, 500) * sx if stroke else 0
        try:
            if t == "rect":
                if fill and not stroke and ow >= W - 1 and oh >= H - 1 and x <= 1 and y <= 1 and not doc.layers:
                    doc.bg = fill
                    continue
                doc.add(type="rect", x=x, y=y, w=ow, h=oh, fill=fill, outline=stroke, ow=sw,
                        rad=_qv_num(o.get("rx"), 0, 0, 1e5) * sx)
            elif t in ("circle", "ellipse"):
                doc.add(type="ellipse", x=x, y=y, w=ow, h=oh, fill=fill, outline=stroke, ow=sw)
            elif t == "line":
                ax, ay, bx, by = x, y, x + ow, y + oh
                if _qv_num(o.get("x1")) > _qv_num(o.get("x2")):
                    ax, bx = bx, ax
                if _qv_num(o.get("y1")) > _qv_num(o.get("y2")):
                    ay, by = by, ay
                doc.add(type="line", x=ax, y=ay, x2=bx, y2=by, color=stroke or fill or "#000000", ow=sw or 2)
            elif t in ("textbox", "text", "i-text", "itext"):
                fam = str(o.get("fontFamily") or "Segoe UI").split(",")[0].strip(" '\"") or "Segoe UI"
                wt = str(o.get("fontWeight", "")).lower()
                bold = wt == "bold" or (wt.isdigit() and int(wt) >= 600)
                al = o.get("textAlign") if o.get("textAlign") in ("left", "center", "right") else "left"
                L = dict(type="text", x=x, y=y, w=ow or 10000, h=10, text=str(o.get("text", "")),
                         size=_qv_num(o.get("fontSize"), 40, 4, 2000) * sy, color=fill or "#000000", family=fam,
                         bold=bold, italic=o.get("fontStyle") == "italic", align=al, fit=True)
                if t != "textbox":
                    L["w"] = 10000
                    L["w"] = qv_text_width(qv_clean_layer(L)) * 1.04 + 4
                L = qv_clean_layer(L)
                L["h"] = qv_fit_height(L)
                doc.add(**L)
            elif t == "image":
                data = fetch_img(str(o.get("src", ""))) if fetch_img else None
                if not data:
                    skipped += 1
                    continue
                raw, iw, ih, _ext = qv_prepare_image(data)
                aid = hashlib.sha1(raw).hexdigest()[:16]
                doc.add_asset(aid, raw, "Görsel", iw, ih)
                doc.add(type="image", x=x, y=y, w=(ow or iw * sx), h=(oh or ih * sy), asset=aid,
                        opacity=_qv_num(o.get("opacity"), 1, 0, 1))
            else:
                skipped += 1
        except Exception:  # noqa: BLE001
            skipped += 1
    return doc, skipped


def qv_parse_ts_templates(text):
    """OpenDesign'ın seed-templates.ts dosyasından şablonları ayıklar: [{id, name, w, h, json}]."""
    out = []
    pat = (r'id:\s*"([^"]+)",\s*name:\s*"([^"]+)",\s*category:\s*"([^"]+)",\s*canvas_json:\s*("(?:[^"\\]|\\.)*"),'
           r'\s*width:\s*(\d+),\s*height:\s*(\d+)')
    for m in re.finditer(pat, text):
        try:
            out.append(dict(id=m[1], name=m[2], w=int(m[5]), h=int(m[6]), json=json.loads(json.loads(m[4]))))
        except ValueError:
            continue
    return out


def qv_online_dir():
    d = os.path.join(_data_dir(), "qv_templates")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass
    return d


def qv_online_list():
    d = read_json(os.path.join(qv_online_dir(), "index.json"))
    out = []
    for e in d.get("items", []) if isinstance(d.get("items"), list) else []:
        if (isinstance(e, dict) and re.fullmatch(r"[\w\-]{1,80}", str(e.get("id", "")))
                and os.path.isfile(os.path.join(qv_online_dir(), e["id"] + QV_EXT))):
            out.append(e)
    return out


def qv_online_store(tid, doc, info):
    """Belgeyi önbelleğe yazar ve dizine ekler/günceller."""
    tid = re.sub(r"[^\w\-]", "-", tid)[:80]
    doc.save(os.path.join(qv_online_dir(), tid + QV_EXT))
    items = [e for e in qv_online_list() if e["id"] != tid]
    items.append(dict(id=tid, name=doc.name, w=doc.w, h=doc.h, info=info))
    write_json(os.path.join(qv_online_dir(), "index.json"), {"items": items})
    return tid


def qv_online_load(entry):
    with open(os.path.join(qv_online_dir(), entry["id"] + QV_EXT), "r", encoding="utf-8") as f:
        return QvDoc.from_dict(json.load(f))


def qv_online_refresh():
    """Açık kaynaklı şablon paketlerini indirir, dönüştürür, önbelleğe yazar. (eklenen, hata_listesi)."""
    added, errs = 0, []
    for src in QV_ONLINE_SOURCES:
        try:
            text = qv_fetch(src["url"], 20, 2_000_000).decode("utf-8", "replace")
        except (OSError, ValueError) as e:
            errs.append(f"{src['name']}: {e or 'bağlantı kurulamadı'}")
            continue
        found = qv_parse_ts_templates(text)
        if not found:
            errs.append(f"{src['name']}: şablon bulunamadı")
        for t in found:
            try:
                doc, _sk = qv_from_fabric(t["json"], t["name"], t["w"], t["h"])
                qv_online_store(f"{src['id']}-{t['id']}", doc, src["info"])
                added += 1
            except Exception as e:  # noqa: BLE001
                errs.append(f"{t['name']}: {e}")
    return added, errs


def qv_import_url(url):
    """Kullanıcının verdiği adresten (qAnvas ya da Fabric.js JSON) şablon alır. Hata: ValueError/OSError."""
    url = qv_http_url(url)
    js = json.loads(qv_fetch(url, 20, 20_000_000).decode("utf-8", "replace"))
    name = os.path.splitext(os.path.basename(urllib.parse.urlparse(url).path))[0] or "İnternet şablonu"
    if isinstance(js, dict) and js.get("format") == "qanvas":
        doc = QvDoc.from_dict(js)
    else:
        doc, _sk = qv_from_fabric(js, name[:60])
    return qv_online_store("url-" + hashlib.sha1(url.encode()).hexdigest()[:10], doc, url[:120])


# ---- temalar (qaznote.py'den) ----
def _theme(name, bg, fg, chrome, border, muted, hover, accent, sel, match):
    return dict(name=name, bg=bg, fg=fg, chrome=chrome, border=border, muted=muted,
                hover=hover, accent=accent, sel=sel, match=match, caret=accent,
                accent_fg="#ffffff" if lum(accent) < 0.55 else "#111111",
                dark=lum(bg) < 0.5)


THEME_LIST = [
    _theme("Beyaz", "#ffffff", "#1d1d1f", "#f5f5f7", "#e5e5ea", "#86868b", "#e8e8ed", "#0071e3", "#b3d7ff", "#ffe58f"),
    _theme("Siyah", "#000000", "#f5f5f7", "#1c1c1e", "#38383a", "#98989d", "#2c2c2e", "#0a84ff", "#0a3d7a", "#5c4b1a"),
    _theme("Gece Yarısı", "#0b1020", "#cdd6f4", "#111830", "#1f2a4d", "#7f8bb3", "#1a2444", "#7aa2f7", "#283a6b", "#524710"),
    _theme("Dracula", "#282a36", "#f8f8f2", "#21222c", "#44475a", "#8190c9", "#343746", "#bd93f9", "#44475a", "#6b5f1a"),
    _theme("Nord", "#2e3440", "#eceff4", "#272c36", "#3b4252", "#8fa6c2", "#3b4252", "#88c0d0", "#434c5e", "#5e5a3a"),
    _theme("Solarized Açık", "#fdf6e3", "#586e75", "#eee8d5", "#ddd6c1", "#93a1a1", "#e6dfc8", "#268bd2", "#cfe3e6", "#f1e29a"),
    _theme("Solarized Koyu", "#002b36", "#93a1a1", "#073642", "#0f4a58", "#657b83", "#0d4452", "#2aa198", "#174a56", "#5a5a14"),
    _theme("Sepya", "#f4ecd8", "#433422", "#e9dfc6", "#d8cba8", "#8a7a5c", "#e0d5b8", "#b45309", "#ead7a8", "#f3d98a"),
    _theme("Monokai", "#272822", "#f8f8f2", "#1e1f1c", "#3e3d32", "#8f8b73", "#34352f", "#a6e22e", "#49483e", "#66591a"),
]
THEMES = {t["name"]: t for t in THEME_LIST}
LEGACY_THEMES = {"Aydınlık": "Beyaz", "Karanlık": "Siyah"}


# ---- Discord Rich Presence (qaznote.py'den) ----
DISCORD_APP_ID = "1563435180033843310"
DISCORD_ASSET = "qaznote"      # Developer Portal > Rich Presence > Art Assets anahtar adı
DISCORD_MIN_GAP = 15           # Discord sınırı: durum en sık 15 sn'de bir güncellenir
DISCORD_RETRY = 30             # Discord kapalıysa yeniden deneme aralığı (sn)



class DiscordRPC(threading.Thread):
    """Arka planda Discord istemcisine bağlanıp 'şu an ne yapıyor' bilgisini yazar.
    Arayüzü asla bloklamaz; Discord yoksa sessizce bekler."""

    def __init__(self):
        super().__init__(daemon=True, name="discord-rpc")
        self.lock = threading.Lock()
        self.wake = threading.Event()
        self.halt = threading.Event()
        self.enabled, self.want = False, None
        self.conn, self.sent = None, None
        self.last_send, self.next_try = 0.0, 0.0
        self.connected = False
        self.start_ts = int(time.time())

    # ---- dışarıya açık ----
    def update(self, enabled, activity):
        with self.lock:
            self.enabled, self.want = bool(enabled), activity
        self.wake.set()

    def stop(self):
        self.halt.set()
        with self.lock:
            self.enabled = False
        self.wake.set()
        if self.is_alive() and threading.current_thread() is not self:
            self.join(1.5)

    # ---- düşük seviye ----
    def _pipe_paths(self):
        if os.name == "nt":
            return [r"\\?\pipe\discord-ipc-%d" % i for i in range(10)]
        out = []
        dirs = [os.environ.get(k) for k in ("XDG_RUNTIME_DIR", "TMPDIR", "TMP", "TEMP")] + ["/tmp"]
        for d in dirs:
            if not d:
                continue
            for sub in ("", "app/com.discordapp.Discord/", "snap.discord/"):
                for i in range(10):
                    out.append(os.path.join(d, sub, f"discord-ipc-{i}"))
        return out

    def _open(self):
        for path in self._pipe_paths():
            try:
                if os.name == "nt":
                    return open(path, "r+b", buffering=0)
                sk = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sk.settimeout(5)
                sk.connect(path)
                return sk
            except OSError:
                try:
                    sk.close()
                except Exception:
                    pass
        return None

    def _write(self, data):
        if os.name == "nt":
            self.conn.write(data)
        else:
            self.conn.sendall(data)

    def _read(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.conn.read(n - len(buf)) if os.name == "nt" else self.conn.recv(n - len(buf))
            if not chunk:
                raise OSError("Discord bağlantısı kapandı")
            buf += chunk
        return buf

    def _packet(self, op, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._write(struct.pack("<II", op, len(data)) + data)

    def _recv(self):
        op, ln = struct.unpack("<II", self._read(8))
        body = self._read(ln) if ln else b"{}"
        try:
            return op, json.loads(body.decode("utf-8"))
        except ValueError:
            return op, {}

    def _close(self):
        c, self.conn = self.conn, None
        self.connected, self.sent = False, None
        if c:
            try:
                c.close()
            except Exception:
                pass

    def _connect(self):
        self.conn = self._open()
        if not self.conn:
            return False
        try:
            self._packet(0, {"v": 1, "client_id": DISCORD_APP_ID})
            op, data = self._recv()
            if op != 1 or data.get("evt") != "READY":
                raise OSError("el sıkışma reddedildi")
            self.connected = True
            return True
        except (OSError, struct.error):
            self._close()
            return False

    def _set(self, activity):
        self._packet(1, {"cmd": "SET_ACTIVITY", "nonce": secrets.token_hex(8),
                         "args": {"pid": os.getpid(), "activity": activity}})
        self._recv()  # yanıtı tüket
        self.sent, self.last_send = activity, time.time()

    # ---- döngü ----
    def run(self):
        while not self.halt.is_set():
            self.wake.wait(1.0)
            self.wake.clear()
            try:
                with self.lock:
                    en, want = self.enabled, self.want
                if self.conn and (not en or want is None):
                    if self.sent is not None:
                        try:
                            self._set(None)
                        except (OSError, struct.error):
                            pass
                    if not en:
                        self._close()
                    self.sent = None
                    continue
                if not en or want is None or self.halt.is_set():
                    continue
                now = time.time()
                if not self.conn:
                    if now < self.next_try:
                        continue
                    if not self._connect():
                        self.next_try = now + DISCORD_RETRY
                        continue
                if want != self.sent and now - self.last_send >= DISCORD_MIN_GAP:
                    self._set(want)
            except (OSError, struct.error, ValueError):
                self._close()
                self.next_try = time.time() + DISCORD_RETRY
        # çıkış: durumu temizle
        if self.conn:
            try:
                self._set(None)
            except Exception:
                pass
            self._close()


_PREV = {}


def fmt_date(ts):
    try:
        return datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M")
    except (OverflowError, OSError, ValueError):
        return ""


