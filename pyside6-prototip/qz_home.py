"""qaZNot başlangıç ekranı (menü): yeni belge, aç, son/sabitlenen belgeler, klasördeki dosyalar, qAnvas."""
import json
import math
import os
from datetime import datetime

from PySide6.QtCore import Qt, QRectF, QPointF, QTimer, QVariantAnimation, QEasingCurve, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QFontMetrics, QPolygonF, QLinearGradient, QPixmap
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QScrollArea, QWidget,
                               QSizePolicy)

import qv_engine as E
from qv_widgets import AButton, fade_in, slide_in
from qz_style import qz_icon
from qz_version import CODENAME

_PREV = {}


def file_preview(path):
    try:
        key = (path, os.path.getmtime(path))
    except OSError:
        return ""
    if key in _PREV:
        return _PREV[key]
    txt = ""
    try:
        if path.lower().endswith(".qaz"):
            with open(path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            txt = "🔒 Şifreli belge" if isinstance(obj.get("enc"), dict) else str(obj.get("text", ""))[:600]
        else:
            with open(path, "rb") as f:
                raw = f.read(600)
            for enc in ("utf-8-sig", "cp1254"):
                try:
                    txt = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
    except Exception:  # noqa: BLE001
        txt = ""
    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()][:4]
    out = "\n".join(ln[:26] + "…" if len(ln) > 26 else ln for ln in lines)
    if len(_PREV) > 300:
        _PREV.clear()
    _PREV[key] = out
    return out


class QAnvasPromo(QWidget):
    """'qAnvas'ı dene!' düğmesi: yumuşak renk nabzı + parıltı."""
    clicked = Signal()

    def __init__(self, sub):
        super().__init__()
        self.sub, self.t, self.hov = sub, 0.0, False
        self.setFixedSize(208, 60)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(40)

    def _tick(self):
        self.t += 0.04
        if self.isVisible():
            self.update()

    def enterEvent(self, e):
        self.hov = True

    def leaveEvent(self, e):
        self.hov = False

    def mouseReleaseEvent(self, e):
        self.clicked.emit()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        k = (math.sin(self.t) + 1) / 2
        c1 = QColor(E.mix("#7b61ff", "#ff4d8d", k))
        c2 = QColor(E.mix("#ff4d8d", "#7b61ff", k))
        g = QLinearGradient(0, 0, self.width(), self.height())
        g.setColorAt(0, c1)
        g.setColorAt(1, c2)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        if self.hov:
            r = r.adjusted(-1, -1, 1, 1)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(r, 18, 18)
        # parıltı yıldızı
        s = 8 + 3 * math.sin(self.t * 2.2)
        cx, cy = 30, self.height() / 2
        p.setBrush(QColor(255, 255, 255, 235))
        p.drawPolygon(QPolygonF([QPointF(cx, cy - s), QPointF(cx + s * .28, cy - s * .28), QPointF(cx + s, cy),
                                 QPointF(cx + s * .28, cy + s * .28), QPointF(cx, cy + s),
                                 QPointF(cx - s * .28, cy + s * .28), QPointF(cx - s, cy),
                                 QPointF(cx - s * .28, cy - s * .28)]))
        f = QFont("Segoe UI")
        f.setPixelSize(14)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor("white"))
        p.drawText(QRectF(54, 10, 150, 22), Qt.AlignmentFlag.AlignVCenter, "qAnvas'ı dene!")
        f.setPixelSize(11)
        f.setBold(False)
        p.setFont(f)
        p.setPen(QColor(255, 255, 255, 215))
        p.drawText(QRectF(54, 31, 150, 18), Qt.AlignmentFlag.AlignVCenter, self.sub)


class DocCard(QWidget):
    W, H, LIFT = 214, 172, 6
    opened = Signal(str)
    pin = Signal(str)
    remove = Signal(str)
    hovered = Signal(str)

    def __init__(self, path, T, pinned):
        super().__init__()
        self.path, self.T, self.pinned = path, T, pinned
        self.hov, self.lift, self.over = False, 0.0, None
        self.setFixedSize(self.W, self.H + self.LIFT)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(180)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.valueChanged.connect(lambda v: (setattr(self, "lift", float(v)), self.update()))
        try:
            self.mtime = os.path.getmtime(path)
        except OSError:
            self.mtime = 0

    def _go(self, v):
        self.anim.stop()
        self.anim.setStartValue(self.lift)
        self.anim.setEndValue(float(v))
        self.anim.start()

    def _star(self):
        return QRectF(self.W - 52, self.LIFT + 8, 20, 20)

    def _x(self):
        return QRectF(self.W - 28, self.LIFT + 8, 20, 20)

    def enterEvent(self, e):
        self.hov = True
        self._go(self.LIFT)
        self.hovered.emit(self.path)

    def leaveEvent(self, e):
        self.hov, self.over = False, None
        self._go(0)

    def mouseMoveEvent(self, e):
        p = QPointF(e.position())
        o = "star" if self._star().contains(p) else "x" if self._x().contains(p) else None
        if o != self.over:
            self.over = o
            self.update()

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        p = QPointF(e.position())
        if self._star().contains(p):
            self.pin.emit(self.path)
        elif self._x().contains(p):
            self.remove.emit(self.path)
        else:
            self.opened.emit(self.path)

    def paintEvent(self, e):
        T = self.T
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        y0 = self.LIFT - self.lift
        card = QRectF(1, y0 + 1, self.W - 2, self.H - 2)
        p.setBrush(QColor(T["chrome"]))
        p.setPen(QPen(QColor(T["accent"] if self.hov else T["border"]), 1.4 if self.hov else 1))
        p.drawRoundedRect(card, 14, 14)
        prev = QRectF(10, y0 + 10, self.W - 20, 78)
        p.setBrush(QColor(T["bg"]))
        p.setPen(QPen(QColor(T["border"]), 1))
        p.drawRoundedRect(prev, 9, 9)
        txt = file_preview(self.path) or "(boş belge)"
        f = QFont("Segoe UI")
        f.setPixelSize(10)
        p.setFont(f)
        p.setPen(QColor(T["muted"]))
        p.drawText(prev.adjusted(9, 6, -6, -4), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, txt)
        name = os.path.splitext(os.path.basename(self.path))[0]
        f.setPixelSize(13)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(T["fg"]))
        fm = QFontMetrics(f)
        p.drawText(QRectF(14, y0 + 96, self.W - 28, 20), Qt.AlignmentFlag.AlignVCenter,
                   fm.elidedText(name, Qt.TextElideMode.ElideRight, self.W - 28))
        f.setPixelSize(11)
        f.setBold(False)
        p.setFont(f)
        p.setPen(QColor(T["muted"]))
        date = datetime.fromtimestamp(self.mtime).strftime("%d.%m.%Y %H:%M") if self.mtime else ""
        ext = os.path.splitext(self.path)[1].lower()
        p.drawText(QRectF(14, y0 + 117, self.W - 28, 16), Qt.AlignmentFlag.AlignVCenter, f"{date} · {ext}")
        fold = os.path.basename(os.path.dirname(self.path)) or os.path.dirname(self.path)
        p.drawText(QRectF(14, y0 + 135, self.W - 28, 16), Qt.AlignmentFlag.AlignVCenter,
                   fm.elidedText("▸ " + fold, Qt.TextElideMode.ElideRight, self.W - 28))
        if self.hov or self.pinned:
            for rect, kind in ((self._star(), "star"), (self._x(), "x")):
                if kind == "x" and not self.hov:
                    continue
                r = rect.translated(0, -self.lift)
                if self.over == kind:
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QColor(T["hover"]))
                    p.drawRoundedRect(r, 6, 6)
                p.setPen(QColor(T["accent"] if (kind == "star" and self.pinned) else T["muted"]))
                f.setPixelSize(14)
                p.setFont(f)
                p.drawText(r, Qt.AlignmentFlag.AlignCenter,
                           ("★" if self.pinned else "☆") if kind == "star" else "✕")


class Flow(QWidget):
    GAP = 14

    def __init__(self):
        super().__init__()
        self.cards = []

    def add(self, c):
        c.setParent(self)
        self.cards.append(c)

    def resizeEvent(self, e):
        self.relayout()

    def relayout(self):
        if not self.cards:
            self.setFixedHeight(0)
            return
        w = max(self.width(), 1)
        cw, ch = self.cards[0].width(), self.cards[0].height()
        cols = max(1, (w + self.GAP) // (cw + self.GAP))
        for i, c in enumerate(self.cards):
            c.move((i % cols) * (cw + self.GAP), (i // cols) * (ch + 4))
            c.show()
        self.setFixedHeight(((len(self.cards) - 1) // cols + 1) * (ch + 4))


class HomeScreen(QFrame):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("qzhome")
        self.query = ""
        self.folder = None
        self._hjob = QTimer(self)
        self._hjob.setSingleShot(True)
        self._hjob.timeout.connect(lambda: self.show_folder(self._pending_folder))
        self._qjob = QTimer(self)
        self._qjob.setSingleShot(True)
        self._qjob.timeout.connect(self.fill_cards)
        self._pending_folder = None
        self.lay = QHBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(0)
        self.build()

    # ---------- kurulum ----------
    def clear(self):
        while self.lay.count():
            it = self.lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

    def build(self, anim=False):
        app = self.app
        T = app.T
        self.clear()
        # sol menü
        side = QFrame()
        side.setObjectName("qzside")
        side.setFixedWidth(244)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(18, 26, 18, 18)
        sl.setSpacing(8)
        title = QLabel("qaZNot")
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        sub = QLabel(f"{app.acct.ed['label']} sürümü · {CODENAME}")
        sub.setObjectName("qzmuted")
        sl.addWidget(title)
        sl.addWidget(sub)
        sl.addSpacing(16)
        for txt, fn, kind, h in (("Yeni belge", app.home_new, "qzprimary", 42), ("Aç…", app.home_browse, "qz", 38),
                                 ("Editöre dön", app.hide_home, "qz", 38), ("Hesabım", app.open_account, "qz", 38)):
            b = AButton(txt)
            b.setObjectName(kind)
            b.setFixedHeight(h)
            b.clicked.connect(lambda _=False, fn=fn: fn())
            sl.addWidget(b)
        sl.addSpacing(10)
        self.tbtn = AButton(self._tlabel())
        self.tbtn.setObjectName("qz")
        self.tbtn.setFixedHeight(32)
        self.tbtn.clicked.connect(self.toggle_startup)
        self.dbtn = AButton(self._dlabel())
        self.dbtn.setObjectName("qz")
        self.dbtn.setFixedHeight(32)
        self.dbtn.clicked.connect(self.toggle_discord)
        sl.addWidget(self.tbtn)
        sl.addWidget(self.dbtn)
        sl.addStretch(1)
        sl.addWidget(self._profile())
        promo = QAnvasPromo("3 hazır boyutla başla" if not app.acct.full else "Şablonlar · özel boyut")
        promo.clicked.connect(app.open_qanvas)
        sl.addWidget(promo, 0, Qt.AlignmentFlag.AlignHCenter)
        self.lay.addWidget(side)
        sep = QFrame()
        sep.setObjectName("qzsep")
        self.lay.addWidget(sep)
        # orta
        main = QFrame()
        ml = QVBoxLayout(main)
        ml.setContentsMargins(36, 28, 0, 0)
        ml.setSpacing(0)
        h = datetime.now().hour
        greet = "Günaydın" if 5 <= h < 12 else "İyi günler" if 12 <= h < 18 else "İyi akşamlar" if h < 23 else "İyi geceler"
        g = QLabel(greet)
        g.setObjectName("qzgreet")
        prof = app.acct.google_profile()
        who = prof["name"] if prof else app.acct.acc["name"]
        s2 = QLabel(f"{who}  ·  Son belgelerin burada.")
        s2.setObjectName("qzmuted")
        ml.addWidget(g)
        ml.addWidget(s2)
        ml.addSpacing(14)
        self.search = QLineEdit()
        self.search.setObjectName("qzsearch")
        self.search.setFixedWidth(380)
        self.search.setPlaceholderText("Belge ara…")
        self.search.addAction(qz_icon("search", T["muted"], 18), QLineEdit.ActionPosition.LeadingPosition)
        self.search.setText(self.query)
        self.search.textChanged.connect(self._on_query)
        ml.addWidget(self.search)
        ml.addSpacing(12)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; } QScrollArea > QWidget > QWidget { background: transparent; }")
        self.inner = QWidget()
        self.inner_l = QVBoxLayout(self.inner)
        self.inner_l.setContentsMargins(0, 0, 14, 20)
        self.inner_l.setSpacing(6)
        self.scroll.setWidget(self.inner)
        ml.addWidget(self.scroll, 1)
        self.lay.addWidget(main, 1)
        sep2 = QFrame()
        sep2.setObjectName("qzsep")
        self.lay.addWidget(sep2)
        # sağ panel
        self.fp = QFrame()
        self.fp.setObjectName("qzside")
        self.fp.setFixedWidth(272)
        self.fl = QVBoxLayout(self.fp)
        self.fl.setContentsMargins(18, 26, 18, 18)
        self.fl.setSpacing(4)
        self.lay.addWidget(self.fp)
        self.fill_cards(anim)
        pin, rec = app.home_entries()
        first = (pin + rec)[:1]
        self.show_folder(os.path.dirname(first[0]) if first else app.default_dir())

    def _profile(self):
        app, T = self.app, self.app.T
        card = QFrame()
        card.setObjectName("qzprofile")
        card.setFixedHeight(66)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        row = QHBoxLayout(card)
        row.setContentsMargins(12, 0, 12, 0)
        av = QLabel()
        av.setPixmap(app.acct.avatar(40))
        av.setFixedSize(40, 40)
        row.addWidget(av)
        col = QVBoxLayout()
        col.setSpacing(1)
        prof = app.acct.google_profile()
        n = QLabel(prof["name"] if prof else app.acct.acc["name"])
        n.setStyleSheet("font-weight: 600;")
        d = QLabel(("G · " + prof["email"]) if prof else "Google ile bağlan")
        d.setObjectName("qzmuted")
        d.setStyleSheet("font-size: 11px;")
        col.addStretch(1)
        col.addWidget(n)
        col.addWidget(d)
        col.addStretch(1)
        row.addLayout(col, 1)
        card.mouseReleaseEvent = lambda e: app.open_account()
        return card

    def _tlabel(self):
        return "Açılışta göster: " + ("Açık" if self.app.home_on else "Kapalı")

    def _dlabel(self):
        a = self.app
        if not a.discord_on:
            return "Discord'da göster: Kapalı"
        return "Discord: Açık · " + ("dosya adı görünür" if a.discord_file else "dosya adı gizli")

    def toggle_startup(self):
        self.app.home_on = not self.app.home_on
        self.app.save_settings()
        self.tbtn.setText(self._tlabel())

    def toggle_discord(self):
        a = self.app
        if not a.discord_on:
            a.set_discord(True, False)
        elif not a.discord_file:
            a.set_discord(True, True)
        else:
            a.set_discord(False, False)
        self.dbtn.setText(self._dlabel())

    # ---------- kartlar ----------
    def _on_query(self, text):
        self.query = text
        self._qjob.start(180)

    def _section(self, title, paths, anim, base):
        lab = QLabel(title)
        lab.setObjectName("qzsec")
        self.inner_l.addSpacing(8)
        self.inner_l.addWidget(lab)
        flow = Flow()
        self.inner_l.addWidget(flow)
        pinned = set(self.app.cfg_pinned())
        n = 0
        for path in paths:
            c = DocCard(path, self.app.T, path in pinned)
            c.opened.connect(self.app.home_open)
            c.pin.connect(self._pin)
            c.remove.connect(self._remove)
            c.hovered.connect(self._hover)
            flow.add(c)
            if anim:
                c.hide()
                QTimer.singleShot(60 * min(base + n, 12), lambda c=c: (c.show(), slide_in(c, 0, 60, 420), fade_in(c, 360)))
            n += 1
        flow.relayout()
        return n

    def fill_cards(self, anim=False):
        while self.inner_l.count():
            it = self.inner_l.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        q = self.query.strip().lower()
        if q:
            pin, rec = [], self.app.search_files(q)
            if rec:
                self._section(f"Arama sonuçları ({len(rec)}) · ad ve içerik", rec, anim, 0)
        else:
            pin, rec = self.app.home_entries()
            base = 0
            if pin:
                base += self._section("Sabitlenenler", pin, anim, base)
            if rec:
                self._section("Son kullanılanlar", rec, anim, base)
        if not pin and not rec:
            msg = "Sonuç bulunamadı." if q else "Henüz belge yok. Yeni belge oluştur ya da bir dosya aç."
            lab = QLabel(msg)
            lab.setObjectName("qzmuted")
            self.inner_l.addWidget(lab)
        self.inner_l.addStretch(1)

    def _pin(self, path):
        self.app.toggle_pin(path)
        self.fill_cards()

    def _remove(self, path):
        self.app.remove_entry(path)
        self.fill_cards()

    def _hover(self, path):
        self._pending_folder = os.path.dirname(path)
        self._hjob.start(170)

    # ---------- klasördeki dosyalar ----------
    def show_folder(self, folder):
        if not folder:
            return
        self.folder = folder
        while self.fl.count():
            it = self.fl.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        T = self.app.T
        sec = QLabel("KLASÖRDEKİ DOSYALAR")
        sec.setObjectName("qzsec")
        self.fl.addWidget(sec)
        self.fl.addSpacing(6)
        nm = QLabel(os.path.basename(folder) or folder)
        nm.setStyleSheet("font-size: 15px; font-weight: 700;")
        self.fl.addWidget(nm)
        pth = QLabel(folder)
        pth.setObjectName("qzmuted")
        pth.setWordWrap(True)
        pth.setStyleSheet("font-size: 11px;")
        self.fl.addWidget(pth)
        self.fl.addSpacing(8)
        files = []
        try:
            for fn in os.listdir(folder):
                if fn.lower().endswith((".qaz", ".txt")):
                    fp = os.path.join(folder, fn)
                    files.append((os.path.getmtime(fp), fp))
        except OSError:
            pass
        files.sort(reverse=True)
        for mt, fp in files[:12]:
            b = AButton("")
            b.setObjectName("qz")
            b.setFixedHeight(40)
            b.setProperty("fp", fp)
            row = QWidget(b)
            rl = QVBoxLayout(row)
            rl.setContentsMargins(10, 3, 8, 3)
            rl.setSpacing(0)
            a = QLabel(QFontMetrics(self.font()).elidedText(os.path.basename(fp), Qt.TextElideMode.ElideRight, 215))
            a.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            d = QLabel(datetime.fromtimestamp(mt).strftime("%d.%m.%Y %H:%M"))
            d.setObjectName("qzmuted")
            d.setStyleSheet("font-size: 10px;")
            d.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            rl.addWidget(a)
            rl.addWidget(d)
            row.setGeometry(0, 0, 236, 40)
            row.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            b.clicked.connect(lambda _=False, fp=fp: self.app.home_open(fp))
            self.fl.addWidget(b)
        if len(files) > 12:
            m = QLabel(f"+{len(files) - 12} dosya daha")
            m.setObjectName("qzmuted")
            self.fl.addWidget(m)
        if not files:
            m = QLabel("Bu klasörde .qaz veya .txt dosyası yok.")
            m.setObjectName("qzmuted")
            m.setWordWrap(True)
            self.fl.addWidget(m)
        self.fl.addStretch(1)
        ob = AButton("Klasörü aç")
        ob.setObjectName("qzfield")
        ob.setFixedHeight(36)
        ob.clicked.connect(lambda: self.app.open_folder(folder))
        self.fl.addWidget(ob)
