"""Animasyonlu dugmeler ve gecis yardimcilari (hover/basma/secili gecisleri, kayma, solma, titreme)."""
from PySide6.QtCore import (Qt, QPropertyAnimation, QVariantAnimation, QEasingCurve, QPoint, QRect, QRectF, QTimer,
                            QSequentialAnimationGroup)
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QPushButton, QToolButton, QGraphicsOpacityEffect

_KEEP = []


def mix(a, b, t):
    a, b = QColor(a), QColor(b)
    return QColor(round(a.red() + (b.red() - a.red()) * t), round(a.green() + (b.green() - a.green()) * t),
                  round(a.blue() + (b.blue() - a.blue()) * t), round(a.alpha() + (b.alpha() - a.alpha()) * t))


def _run(anim):
    _KEEP.append(anim)

    def done():
        if anim in _KEEP:
            _KEEP.remove(anim)
    anim.finished.connect(done)
    anim.start()
    return anim


def fade_in(w, dur=320):
    """Ogeyi 0'dan 1'e soldurur (kucuk ogeler icin; bitince efekt kaldirilir)."""
    eff = QGraphicsOpacityEffect(w)
    eff.setOpacity(0.0)
    w.setGraphicsEffect(eff)
    a = QPropertyAnimation(eff, b"opacity", w)
    a.setDuration(dur)
    a.setStartValue(0.0)
    a.setEndValue(1.0)
    a.setEasingCurve(QEasingCurve.Type.OutCubic)

    def done():
        try:
            if w.graphicsEffect() is eff:
                w.setGraphicsEffect(None)
        except RuntimeError:
            pass
    a.finished.connect(done)
    return _run(a)


def slide_in(w, dx=0, dy=0, dur=380):
    """Ogeyi (dx, dy) uzaktan kendi yerine kaydirir. Yerlesim bittikten sonra baslar."""
    def go():
        try:
            end = w.pos()
        except RuntimeError:
            return
        w.move(end + QPoint(dx, dy))
        a = QPropertyAnimation(w, b"pos", w)
        a.setDuration(dur)
        a.setStartValue(end + QPoint(dx, dy))
        a.setEndValue(end)
        a.setEasingCurve(QEasingCurve.Type.OutCubic)
        _run(a)
    QTimer.singleShot(0, go)


def window_fade_in(win, dur=360):
    win.setWindowOpacity(0.0)
    a = QPropertyAnimation(win, b"windowOpacity", win)
    a.setDuration(dur)
    a.setStartValue(0.0)
    a.setEndValue(1.0)
    a.setEasingCurve(QEasingCurve.Type.OutCubic)
    return _run(a)


def shake(w, amp=9, dur=320):
    """Hatali girisi belirtmek icin ogeyi yatayda titretir."""
    base = w.pos()
    g = QSequentialAnimationGroup(w)
    step = dur // 5
    for off in (-amp, amp, -amp * 0.6, amp * 0.6, 0):
        a = QPropertyAnimation(w, b"pos", w)
        a.setDuration(step)
        a.setEndValue(QPoint(base.x() + int(off), base.y()))
        a.setEasingCurve(QEasingCurve.Type.InOutSine)
        g.addAnimation(a)
    return _run(g)


def animate_width(w, to, dur=260, hide_when_zero=True):
    a = QPropertyAnimation(w, b"maximumWidth", w)
    a.setDuration(dur)
    a.setStartValue(w.width() if w.isVisible() else 0)
    a.setEndValue(to)
    a.setEasingCurve(QEasingCurve.Type.OutCubic)
    if to == 0 and hide_when_zero:
        a.finished.connect(w.hide)
    return _run(a)


STYLES = {
    # taban, uzerine gelince, basilince, yazi
    "accent": ("#0D99FF", "#2BA8FF", "#0A7FD6", "#FFFFFF"),
    "flat": ("#00000000", "#3C3C3C", "#505050", "#E6E6E6"),
    "default": ("#3C3C3C", "#4C4C4C", "#5C5C5C", "#E6E6E6"),
    "account": ("#3C3C3C", "#4C4C4C", "#5C5C5C", "#E6E6E6"),
    "tool": ("#00000000", "#3C3C3C", "#505050", "#E6E6E6"),
}


THEME = {}  # qaZNot'un geçerli teması (qz* düğmeler bunu kullanır)


def set_theme(t):
    THEME.clear()
    THEME.update(t)


def qz_colors(kind):
    t = THEME or {"bg": "#ffffff", "fg": "#1d1d1f", "chrome": "#f5f5f7", "hover": "#e8e8ed", "accent": "#0071e3",
                  "accent_fg": "#ffffff", "border": "#e5e5ea"}
    if kind == "qzprimary":
        a = t["accent"]
        return a, mix(a, "#ffffff", 0.16).name(), mix(a, "#000000", 0.16).name(), t["accent_fg"]
    if kind == "qzfield":
        return t["bg"], t["hover"], mix(t["hover"], t["fg"], 0.15).name(), t["fg"]
    return "#00000000", t["hover"], mix(t["hover"], t["fg"], 0.14).name(), t["fg"]


class _Anim:
    """Hover / basili / secili gecislerini yumusak animasyonla boyar."""

    def _anim_init(self):
        self._h = self._pr = self._ck = 0.0
        self._anims = {}
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggled.connect(lambda c: self._go("_ck", 1.0 if c else 0.0, 220))

    def _go(self, attr, target, dur=150):
        a = self._anims.get(attr)
        if a is None:
            a = QVariantAnimation(self)
            a.setEasingCurve(QEasingCurve.Type.OutCubic)
            a.valueChanged.connect(lambda v, attr=attr: (setattr(self, attr, float(v)), self.update()))
            self._anims[attr] = a
        a.stop()
        a.setDuration(dur)
        a.setStartValue(float(getattr(self, attr)))
        a.setEndValue(float(target))
        a.start()

    def enterEvent(self, e):
        self._go("_h", 1.0, 140)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._go("_h", 0.0, 220)
        self._go("_pr", 0.0, 160)
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        self._go("_pr", 1.0, 70)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._go("_pr", 0.0, 180)
        super().mouseReleaseEvent(e)

    def _kind(self):
        n = self.objectName()
        if n in STYLES or n.startswith("qz"):
            return n
        return "tool" if isinstance(self, QToolButton) else "default"

    def paintEvent(self, e):
        kind = self._kind()
        qz = kind.startswith("qz")
        base, hover, press, fg = qz_colors(kind) if qz else STYLES[kind]
        col = mix(base, hover, self._h)
        col = mix(col, press, self._pr)
        if self.isCheckable():
            if qz:
                col = mix(col, mix(THEME.get("hover", "#e8e8ed"), THEME.get("accent", "#0071e3"), 0.5), self._ck)
            else:
                col = mix(col, "#0D99FF", self._ck)
        fgc = QColor(fg)
        if not self.isEnabled():
            col.setAlpha(int(col.alpha() * 0.55))
            fgc.setAlpha(110)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect())
        s = 1.0 - 0.035 * self._pr
        p.translate(r.center())
        p.scale(s, s)
        p.translate(-r.center())
        rad = 16.0 if kind == "account" else (8.0 if qz else 6.0)
        if kind == "qzfield":
            p.setPen(QPen(QColor(THEME.get("border", "#e5e5ea")), 1))
            r = r.adjusted(0.5, 0.5, -0.5, -0.5)
        else:
            p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawRoundedRect(r, rad, rad)
        f = self.font()
        if kind in ("accent", "qzprimary"):
            f.setBold(True)
        p.setFont(f)
        p.setPen(fgc)
        text, icon = self.text(), self.icon()
        isz = self.iconSize()
        if not icon.isNull() and text:
            ir = QRect(6 if kind == "account" else 10, int(r.center().y() - isz.height() / 2), isz.width(), isz.height())
            icon.paint(p, ir)
            tr = QRectF(ir.right() + 4, 0, r.width() - ir.right() - 10, r.height())
            p.drawText(tr, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text.strip())
        elif not icon.isNull():
            ir = QRect(int(r.center().x() - isz.width() / 2), int(r.center().y() - isz.height() / 2),
                       isz.width(), isz.height())
            icon.paint(p, ir)
        else:
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, text)
        p.end()


class AButton(_Anim, QPushButton):
    def __init__(self, *a):
        super().__init__(*a)
        self._anim_init()


class ATool(_Anim, QToolButton):
    def __init__(self, *a):
        super().__init__(*a)
        self._anim_init()
