"""Lisans anahtari girisi, hesap karti ve Google baglama (PySide6).
Ayarlar eski qaZNot ile ayni klasorde (%APPDATA%\\qaznote) paylasilir: acik oturum korunur."""
import math
import os
import time

from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPixmap, QPainterPath, QFont, QRadialGradient, QBrush
from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                               QStackedWidget, QWidget, QFrame, QGridLayout, QMessageBox)

import qv_engine as E
from qv_theme import QSS as DARK_QSS
from qv_widgets import AButton, fade_in, slide_in, shake, window_fade_in


def circle_pixmap(src, size):
    out = QPixmap(size, size)
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    p.setClipPath(path)
    sc = src.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation)
    p.drawPixmap((size - sc.width()) // 2, (size - sc.height()) // 2, sc)
    p.end()
    return out


def initial_pixmap(text, size, color):
    out = QPixmap(size, size)
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    p.drawEllipse(0, 0, size, size)
    f = QFont("Segoe UI")
    f.setPixelSize(int(size * 0.38))
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor("white"))
    p.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, text)
    p.end()
    return out


_ENTROPY = b"qaZNot-license-v2"


def protect(text):
    """Metni Windows DPAPI ile (bu kullanıcıya özel) şifreler; base64 döndürür. Desteklenmiyorsa None."""
    if os.name != "nt":
        return None
    try:
        import base64
        import ctypes
        from ctypes import wintypes

        class BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]
        raw = text.encode("utf-8")
        buf = ctypes.create_string_buffer(raw, len(raw))
        ent = ctypes.create_string_buffer(_ENTROPY, len(_ENTROPY))
        bin_, bent, bout = BLOB(len(raw), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), \
            BLOB(len(_ENTROPY), ctypes.cast(ent, ctypes.POINTER(ctypes.c_char))), BLOB()
        if not ctypes.windll.crypt32.CryptProtectData(ctypes.byref(bin_), None, ctypes.byref(bent), None, None, 0,
                                                      ctypes.byref(bout)):
            return None
        data = ctypes.string_at(bout.pbData, bout.cbData)
        ctypes.windll.kernel32.LocalFree(bout.pbData)
        return base64.b64encode(data).decode("ascii")
    except Exception:  # noqa: BLE001
        return None


def unprotect(b64):
    if os.name != "nt" or not b64:
        return None
    try:
        import base64
        import ctypes
        from ctypes import wintypes

        class BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]
        raw = base64.b64decode(b64)
        buf = ctypes.create_string_buffer(raw, len(raw))
        ent = ctypes.create_string_buffer(_ENTROPY, len(_ENTROPY))
        bin_, bent, bout = BLOB(len(raw), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), \
            BLOB(len(_ENTROPY), ctypes.cast(ent, ctypes.POINTER(ctypes.c_char))), BLOB()
        if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(bin_), None, ctypes.byref(bent), None, None, 0,
                                                        ctypes.byref(bout)):
            return None
        data = ctypes.string_at(bout.pbData, bout.cbData)
        ctypes.windll.kernel32.LocalFree(bout.pbData)
        return data.decode("utf-8")
    except Exception:  # noqa: BLE001
        return None


class Account:
    """Giris yapmis hesap: lisans anahtari + anahtara tanimli bilgiler + (varsa) Google profili.
    Anahtar settings.json'da düz metin değil, Windows DPAPI ile şifreli ('license_enc') saklanır."""

    def __init__(self, key, acc):
        self.key = key
        self.acc = acc
        self.ed = E.EDITIONS[acc["ed"]]

    @classmethod
    def from_key(cls, key):
        h, acc = E.lookup_license(key)
        return cls(E.fmt_key(key), acc) if acc else None

    @classmethod
    def load(cls):
        cfg = E.read_json(E.CONFIG)
        k = unprotect(cfg.get("license_enc")) if cfg.get("license_enc") else None
        legacy = False
        if not k and cfg.get("license"):
            k, legacy = cfg.get("license"), True
        acct = cls.from_key(k) if k else None
        if acct and legacy and protect(acct.key):
            acct.remember()  # eski düz metin anahtarı şifreliye taşı
        return acct

    def remember_into(self, cfg):
        enc = protect(self.key)
        if enc:
            cfg["license_enc"] = enc
            cfg.pop("license", None)
        else:
            cfg["license"] = self.key

    def remember(self):
        cfg = E.read_json(E.CONFIG)
        self.remember_into(cfg)
        E.write_json(E.CONFIG, cfg)

    @staticmethod
    def forget():
        cfg = E.read_json(E.CONFIG)
        cfg.pop("license", None)
        cfg.pop("license_enc", None)
        E.write_json(E.CONFIG, cfg)

    @property
    def aid(self):
        return self.acc["id"]

    @property
    def name(self):
        p = self.google_profile()
        return p["name"] if p else self.acc["name"]

    @property
    def full(self):
        return E.qv_access(self.ed)["full"]

    def google_profile(self):
        p = E.read_json(E.GOOGLE).get(self.aid)
        return p if isinstance(p, dict) and p.get("email") else None

    def avatar_file(self):
        return os.path.join(E.AVATARS, f"{self.aid}.img")

    def set_google(self, prof, photo):
        prof = dict(prof)
        prof["photo"] = False
        if photo:
            try:
                os.makedirs(E.AVATARS, exist_ok=True)
                with open(self.avatar_file(), "wb") as f:
                    f.write(photo)
                prof["photo"] = True
            except OSError:
                pass
        d = E.read_json(E.GOOGLE)
        d[self.aid] = prof
        E.write_json(E.GOOGLE, d)

    def unlink_google(self):
        d = E.read_json(E.GOOGLE)
        d.pop(self.aid, None)
        E.write_json(E.GOOGLE, d)
        try:
            os.remove(self.avatar_file())
        except OSError:
            pass

    def avatar(self, size):
        prof = self.google_profile()
        if prof and prof.get("photo") and os.path.exists(self.avatar_file()):
            pm = QPixmap(self.avatar_file())
            if not pm.isNull():
                return circle_pixmap(pm, size)
        ini = (prof["name"][:1] if prof else "".join(w[0] for w in self.acc["name"].split()[:2])).upper()
        return initial_pixmap(ini or "?", size, self.ed["color"])


class AccountDialog(QDialog):
    """acct=None: giris (anahtar -> hesap karti). acct verilirse: 'Hesabim' (Google bagla/kes, oturumu kapat)."""

    CW, CH = 480, 680

    def __init__(self, acct=None, required=False, parent=None):
        super().__init__(parent)
        self.setStyleSheet(DARK_QSS)
        self.setWindowTitle("qAnvas - Hesap")
        self.acct = acct
        self.required = required
        self.signout = False
        self.gauth = None
        self._fmt_lock = False
        self._pending = None
        self._busy = False
        self._t = 0.0
        self._intro = False
        self.fancy = required and acct is None  # tam ekran giriş: süzülen daireler + kart
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.holder = QFrame()
        self.holder.setFixedSize(self.CW, self.CH)
        self.holder.setObjectName("lcard" if self.fancy else "plain")
        if self.fancy:
            self.setObjectName("loginroot")
            self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
            scr = QApplication.primaryScreen().geometry()
            self.setGeometry(scr)
            outer.addStretch(1)
            outer.addWidget(self.holder, 0, Qt.AlignmentFlag.AlignHCenter)
            outer.addStretch(1)
            import random
            rnd = random.Random(7)
            cols = ["#0D99FF", "#7B61FF", "#FF4D8D", "#14C38E", "#0D99FF", "#7B61FF"]
            self.orbs = [dict(x=rnd.uniform(.1, .9), y=rnd.uniform(.1, .9), r=rnd.uniform(150, 300), c=cols[i],
                              sx=rnd.uniform(.25, .6), sy=rnd.uniform(.2, .5), ph=rnd.uniform(0, 6.3),
                              ax=rnd.uniform(.04, .12), ay=rnd.uniform(.04, .12)) for i in range(6)]
            self.orb_timer = QTimer(self)
            self.orb_timer.timeout.connect(self._orb_tick)
            self.orb_timer.start(16)
        else:
            self.setFixedSize(self.CW, self.CH)
            outer.addWidget(self.holder)
        hl = QVBoxLayout(self.holder)
        hl.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        hl.addWidget(self.stack)
        self.page_key = self._build_key_page()
        self.stack.addWidget(self.page_key)
        self.page_acc = None
        self.lock_timer = QTimer(self)
        self.lock_timer.timeout.connect(self._lock_tick)
        if acct:
            self.show_account(acct, viewing=True)
        else:
            QTimer.singleShot(500, self.entry.setFocus)

    # ---------- animasyonlar ----------
    def _orb_tick(self):
        self._t += 0.016
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        if not self.fancy:
            p.fillRect(self.rect(), QColor("#2C2C2C"))
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), QColor("#14151A"))
        p.setPen(Qt.PenStyle.NoPen)
        for o in self.orbs:
            cx = (o["x"] + math.sin(self._t * o["sx"] + o["ph"]) * o["ax"]) * w
            cy = (o["y"] + math.cos(self._t * o["sy"] + o["ph"]) * o["ay"]) * h
            g = QRadialGradient(QPointF(cx, cy), o["r"])
            c = QColor(o["c"])
            c.setAlpha(80)
            g.setColorAt(0, c)
            c.setAlpha(0)
            g.setColorAt(1, c)
            p.setBrush(QBrush(g))
            p.drawEllipse(QPointF(cx, cy), o["r"], o["r"])
        hg = self.holder.geometry()
        for i in range(14):
            sp = (i + 1) * 3
            p.setBrush(QColor(0, 0, 0, 12))
            p.drawRoundedRect(QRectF(hg).adjusted(-sp, -sp + 14, sp, sp + 14), 24 + sp, 24 + sp)
        f = QFont("Segoe UI")
        f.setPixelSize(22)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor("white"))
        p.drawText(QRectF(40, 28, 300, 36), Qt.AlignmentFlag.AlignVCenter, "qAnvas")
        f.setPixelSize(12)
        f.setBold(False)
        p.setFont(f)
        p.setPen(QColor("#98989D"))
        p.drawText(QRectF(0, h - 44, w - 40, 24), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   "Esc  ·  Çıkış")

    def showEvent(self, e):
        super().showEvent(e)
        if not self._intro:
            self._intro = True
            window_fade_in(self, 420)
            slide_in(self.holder, 0, 70, 560)
            if not self.fancy:
                slide_in(self.stack.currentWidget(), 0, 24, 420)

    def go_page(self, w, direction=1):
        if self.stack.currentWidget() is w:
            return
        self.stack.setCurrentWidget(w)
        slide_in(w, 120 * direction, 0, 400)
        fade_in(w, 360)

    # ---------- sayfa 1: anahtar ----------
    def _header(self, lay, title, sub):
        t = QLabel(title)
        t.setObjectName("big")
        s = QLabel(sub)
        s.setObjectName("sub")
        s.setWordWrap(True)
        lay.addWidget(t)
        lay.addWidget(s)
        lay.addSpacing(14)

    def _build_key_page(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(28, 28, 28, 24)
        lay.setSpacing(8)
        self._header(lay, "qAnvas'a hoş geldin",
                     "Hesabını açmak için lisans anahtarını gir. Anahtara tanımlı hesap bilgileri otomatik gelir.")
        sec = QLabel("LİSANS ANAHTARI")
        sec.setObjectName("sec")
        lay.addWidget(sec)
        self.entry = QLineEdit()
        self.entry.setObjectName("key")
        self.entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.entry.setMaxLength(24)
        self.entry.setPlaceholderText("XXXX-XXXX-XXXX-XXXX-XXXX")
        self.entry.textEdited.connect(self._on_type)
        self.entry.returnPressed.connect(self.check)
        lay.addWidget(self.entry)
        self.msg = QLabel("")
        self.msg.setObjectName("err")
        self.msg.setWordWrap(True)
        self.msg.setMinimumHeight(36)
        self.msg.setAlignment(Qt.AlignmentFlag.AlignTop)
        lay.addWidget(self.msg)
        self.btn_check = AButton("Doğrula")
        self.btn_check.setObjectName("accent")
        self.btn_check.setProperty("big", True)
        self.btn_check.setMinimumHeight(44)
        self.btn_check.clicked.connect(self.check)
        lay.addWidget(self.btn_check)
        hint = QLabel("Örnek biçim: CORE-XXXX-XXXX-XXXX-XXXX")
        hint.setObjectName("hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addSpacing(8)
        lay.addWidget(hint)
        lay.addStretch(1)
        return w

    def _on_type(self, raw):
        if self._fmt_lock:
            return
        new = E.fmt_key(raw)
        if new != raw:
            self._fmt_lock = True
            self.entry.setText(new)
            self._fmt_lock = False
        if not self._locked_for():
            self.msg.setText("")
            self._restyle("key")

    def _restyle(self, name):
        self.entry.setObjectName(name)
        st = self.entry.style()
        st.unpolish(self.entry)
        st.polish(self.entry)

    def _locked_for(self):
        return max(0, int(-(-(E.load_security()["until"] - time.time()) // 1)))

    def _lock_tick(self):
        left = self._locked_for()
        if left > 0:
            self.msg.setText(f"Çok fazla hatalı deneme. {left} sn sonra tekrar deneyebilirsin.")
        else:
            self.lock_timer.stop()
            self.msg.setText("")

    def _error(self, text):
        self.msg.setText(text)
        fade_in(self.msg, 220)
        self._restyle("keyerr")
        shake(self.entry)

    def check(self):
        if self._busy:
            return
        left = self._locked_for()
        if left > 0:
            self._lock_tick()
            self.lock_timer.start(500)
            shake(self.entry)
            return
        key = self.entry.text()
        if len(E.norm_key(key)) < 20:
            self._error("Anahtar eksik. Anahtar 20 karakterden oluşur (5 grup × 4).")
            return
        self._busy = True
        self.btn_check.setText("Doğrulanıyor…")
        self.btn_check.setEnabled(False)
        QTimer.singleShot(380, lambda: self._finish_check(key))

    def _finish_check(self, key):
        self._busy = False
        self.btn_check.setText("Doğrula")
        self.btn_check.setEnabled(True)
        h, acc = E.lookup_license(key)
        sec = E.load_security()
        if not acc:
            sec["fails"] += 1
            if sec["fails"] >= E.MAX_TRIES:
                wait = min(900, 30 * 2 ** (sec["fails"] - E.MAX_TRIES))
                sec["until"] = time.time() + wait
                self._error(f"Çok fazla hatalı deneme. {wait} sn sonra tekrar deneyebilirsin.")
                self.lock_timer.start(500)
            else:
                self._error(f"Geçersiz lisans anahtarı. Kalan deneme: {E.MAX_TRIES - sec['fails']}")
            E.save_security(sec)
            return
        E.save_security({"fails": 0, "until": 0})
        self._pending = Account(E.fmt_key(key), acc)
        self.show_account(self._pending, viewing=False)

    # ---------- sayfa 2: hesap karti ----------
    def show_account(self, acct, viewing):
        self.acct_shown = acct
        old = self.page_acc
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(28, 28, 28, 24)
        lay.setSpacing(8)
        if viewing:
            self._header(lay, "Hesabım", "Bu cihazda açık olan hesap.")
        else:
            self._header(lay, "Hesap bulundu", "Bu anahtara şu hesap tanımlı. Devam etmek için hesabı aç.")
        card = self._card(acct)
        lay.addWidget(card)
        if self.isVisible():
            slide_in(card, 0, 54, 560)
        self.msg2 = QLabel("")
        self.msg2.setObjectName("sub")
        self.msg2.setWordWrap(True)
        lay.addWidget(self.msg2)
        lay.addStretch(1)
        if viewing:
            ok = AButton("Tamam")
            ok.setObjectName("accent")
            ok.setMinimumHeight(44)
            ok.clicked.connect(self.accept)
            lay.addWidget(ok)
            row = QHBoxLayout()
            self.btn_google = AButton("")
            self.btn_google.setMinimumHeight(36)
            self.btn_google.clicked.connect(self.google_click)
            self._set_gtext()
            out = AButton("Oturumu kapat")
            out.setMinimumHeight(36)
            out.clicked.connect(self._signout)
            row.addWidget(self.btn_google)
            row.addWidget(out)
            lay.addLayout(row)
        else:
            go = AButton("Hesabı Aç")
            go.setObjectName("accent")
            go.setMinimumHeight(44)
            go.clicked.connect(self._open_it)
            lay.addWidget(go)
            back = AButton("Başka anahtar gir")
            back.setMinimumHeight(36)
            back.clicked.connect(lambda: self.go_page(self.page_key, -1))
            lay.addWidget(back)
        self.page_acc = w
        self.stack.addWidget(w)
        if self.isVisible():
            self.go_page(w, 1)
        else:
            self.stack.setCurrentWidget(w)
        if old is not None:
            self.stack.removeWidget(old)
            old.deleteLater()

    def _card(self, acct):
        card = QFrame()
        card.setObjectName("card")
        g = QVBoxLayout(card)
        g.setContentsMargins(20, 18, 20, 16)
        g.setSpacing(6)
        top = QHBoxLayout()
        av = QLabel()
        av.setPixmap(acct.avatar(60))
        av.setFixedSize(60, 60)
        top.addWidget(av)
        names = QVBoxLayout()
        names.setSpacing(1)
        nm = QLabel(acct.acc["name"])
        nm.setStyleSheet("font-weight: 600; font-size: 14px;")
        idl = QLabel(acct.acc["id"])
        idl.setObjectName("sub")
        em = QLabel(acct.acc["email"])
        em.setObjectName("sub")
        for x in (nm, idl, em):
            names.addWidget(x)
        top.addLayout(names, 1)
        chip = QLabel(acct.ed["label"])
        chip.setObjectName("chip")
        chip.setStyleSheet(f"background: {acct.ed['color']}; color: white;")
        top.addWidget(chip, 0, Qt.AlignmentFlag.AlignTop)
        g.addLayout(top)
        sep = QFrame()
        sep.setObjectName("sep")
        g.addSpacing(6)
        g.addWidget(sep)
        prof = acct.google_profile()
        key = acct.key
        rows = [("Google", prof["email"]) if prof else ("Kullanıcı adı", acct.acc["user"]),
                ("Hesap No", acct.acc["id"]), ("Üyelik", acct.acc["since"]),
                ("Anahtar", key[:4] + "-••••-••••-••••-" + key[-4:])]
        grid = QGridLayout()
        grid.setVerticalSpacing(6)
        for i, (k, v) in enumerate(rows):
            a = QLabel(k)
            a.setObjectName("sub")
            b = QLabel(v)
            b.setAlignment(Qt.AlignmentFlag.AlignRight)
            grid.addWidget(a, i, 0)
            grid.addWidget(b, i, 1)
        g.addLayout(grid)
        sep2 = QFrame()
        sep2.setObjectName("sep")
        g.addSpacing(4)
        g.addWidget(sep2)
        sec = QLabel("SÜRÜM ÖZELLİKLERİ")
        sec.setObjectName("sec")
        g.addWidget(sec)
        for line in acct.ed["info"]:
            bad = "yok" in line
            row = QLabel(("✕  " if bad else "✓  ") + line)
            row.setStyleSheet(f"color: {'#8C8C8C' if bad else '#E6E6E6'};")
            g.addWidget(row)
        return card

    # ---------- Google ----------
    def _set_gtext(self):
        if self.gauth:
            t = "İptal (tarayıcıda onayla)"
        else:
            t = "Google'ı kes" if self.acct.google_profile() else "Google ile bağlan"
        self.btn_google.setText(t)

    def google_click(self):
        a = self.acct
        if self.gauth:
            self.gauth.cancel()
            self.gauth = None
            self._set_gtext()
            return
        if a.google_profile():
            r = QMessageBox.question(self, "qAnvas", "Google bağlantısı kesilsin mi?\nProfil bilgileri bu cihazdan silinir.")
            if r == QMessageBox.StandardButton.Yes:
                a.unlink_google()
                self.show_account(a, viewing=True)
            return
        self.gauth = E.GoogleAuth()
        self.gauth.start()
        self._set_gtext()
        self.msg2.setText("Tarayıcıda Google ile devam et…")
        QTimer.singleShot(300, self._google_poll)

    def _google_poll(self):
        g = self.gauth
        if g is None:
            return
        if not g.done:
            QTimer.singleShot(300, self._google_poll)
            return
        self.gauth = None
        if g.error or not g.profile:
            self._set_gtext()
            self.msg2.setObjectName("err")
            self.msg2.setStyleSheet("color: #FF6B5E;")
            self.msg2.setText(g.error or "Google bağlantısı kurulamadı")
            return
        self.acct.set_google(g.profile, g.photo)
        self.show_account(self.acct, viewing=True)
        self.msg2.setText(f"Google bağlandı: {g.profile['email']}")
        self.msg2.setStyleSheet("color: #32D74B;")

    # ---------- sonuc ----------
    def _open_it(self):
        self.acct = self._pending
        self.acct.remember()
        self.accept()

    def _signout(self):
        self.signout = True
        self.accept()

    def reject(self):
        if self.gauth:
            self.gauth.cancel()
        if self.required:
            r = QMessageBox.question(self, "qAnvas", "Giriş yapmadan çıkmak istiyor musun?")
            if r != QMessageBox.StandardButton.Yes:
                return
        super().reject()

    def done(self, code):
        if self.gauth:
            self.gauth.cancel()
        if self.fancy:
            self.orb_timer.stop()
        super().done(code)
