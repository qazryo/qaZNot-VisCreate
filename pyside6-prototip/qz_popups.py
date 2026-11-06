"""qaZNot açılır pencereleri: yazı tipi seçici, renk seçici, tema galerisi (animasyonlu)."""
from PySide6.QtCore import Qt, QPoint, QRectF, QTimer, QEvent
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QFontDatabase
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QGridLayout, QWidget, QApplication, QColorDialog)

import qv_engine as E
from qv_widgets import AButton, fade_in, slide_in, window_fade_in


class Popup(QFrame):
    def __init__(self, parent, w, h):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("qzpopup")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(w, h)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(14, 14, 14, 12)
        self.lay.setSpacing(8)

    def show_below(self, anchor, align="left"):
        gp = anchor.mapToGlobal(QPoint(0, anchor.height() + 6))
        x = gp.x() if align == "left" else gp.x() + anchor.width() - self.width()
        scr = QApplication.screenAt(gp) or QApplication.primaryScreen()
        g = scr.availableGeometry()
        x = max(g.left() + 6, min(x, g.right() - self.width() - 6))
        y = min(gp.y(), g.bottom() - self.height() - 6)
        self.move(x, y)
        self.show()
        window_fade_in(self, 170)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(e)


# ------------------------------------------------------------------ yazı tipi ----
class FontPicker(Popup):
    def __init__(self, parent, families, recent, current, on_pick, core_note=False):
        super().__init__(parent, 390, 500)
        self.families, self.recent, self.current, self.on_pick, self.core_note = families, recent, current, on_pick, core_note
        t = QLabel("Yazı Tipi")
        t.setObjectName("qzbig")
        t.setStyleSheet("font-size: 16px;")
        self.lay.addWidget(t)
        self.entry = QLineEdit()
        self.entry.setObjectName("qzentry")
        self.entry.setPlaceholderText("Ara…")
        self.entry.textChanged.connect(self.fill)
        self.entry.installEventFilter(self)
        self.lay.addWidget(self.entry)
        self.lst = QListWidget()
        self.lst.itemClicked.connect(self.pick)
        self.lay.addWidget(self.lst, 1)
        self.foot = QLabel("")
        self.foot.setObjectName("qzmuted")
        self.lay.addWidget(self.foot)
        self.fill()
        QTimer.singleShot(0, self.entry.setFocus)

    def _header(self, text):
        it = QListWidgetItem(text)
        f = QFont()
        f.setPixelSize(10)
        f.setBold(True)
        it.setFont(f)
        it.setFlags(Qt.ItemFlag.NoItemFlags)
        it.setForeground(QColor("#888888"))
        self.lst.addItem(it)

    def _item(self, fam):
        it = QListWidgetItem(fam)
        f = QFont(fam)
        f.setPixelSize(17)
        it.setFont(f)
        it.setData(Qt.ItemDataRole.UserRole, fam)
        self.lst.addItem(it)
        if fam == self.current:
            self.lst.setCurrentItem(it)

    def fill(self):
        q = self.entry.text().strip().lower()
        self.lst.clear()
        if q:
            for fam in self.families:
                if q in fam.lower():
                    self._item(fam)
            if self.lst.count() and not self.lst.currentItem():
                self.lst.setCurrentRow(0)
        else:
            rec = [f for f in self.recent if f in self.families]
            if rec:
                self._header("SON KULLANILANLAR")
                for fam in rec:
                    self._item(fam)
                self._header("TÜM YAZI TİPLERİ")
            for fam in self.families:
                self._item(fam)
        note = "  ·  Core: seçili yazı tipleri" if self.core_note else ""
        self.foot.setText(f"{len(self.families)} yazı tipi  ·  şu an: {self.current}{note}")

    def eventFilter(self, obj, ev):
        if obj is self.entry and ev.type() == QEvent.Type.KeyPress:
            k = ev.key()
            if k in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                step = 1 if k == Qt.Key.Key_Down else -1
                r = self.lst.currentRow()
                while True:
                    r += step
                    if r < 0 or r >= self.lst.count():
                        break
                    if self.lst.item(r).flags() & Qt.ItemFlag.ItemIsSelectable:
                        self.lst.setCurrentRow(r)
                        break
                return True
            if k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if self.lst.currentItem():
                    self.pick(self.lst.currentItem())
                return True
        return super().eventFilter(obj, ev)

    def pick(self, it):
        fam = it.data(Qt.ItemDataRole.UserRole)
        if fam:
            self.close()
            self.on_pick(fam)


# ------------------------------------------------------------------ renk ----
class Swatch(QWidget):
    def __init__(self, color, selected, cb, border):
        super().__init__()
        self.color, self.selected, self.cb, self.border, self.hov = color, selected, cb, border, False
        self.setFixedSize(34, 34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def enterEvent(self, e):
        self.hov = True
        self.update()

    def leaveEvent(self, e):
        self.hov = False
        self.update()

    def mouseReleaseEvent(self, e):
        self.cb(self.color)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(3, 3, -3, -3)
        if self.hov:
            r = r.adjusted(-1.5, -1.5, 1.5, 1.5)
        p.setBrush(QColor(self.color))
        p.setPen(QPen(QColor(self.border), 1))
        p.drawRoundedRect(r, 7, 7)
        if self.selected:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#0a84ff"), 2))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 8, 8)


class ColorPopup(Popup):
    def __init__(self, parent, title, current, on_pick, none_label, border):
        super().__init__(parent, 8 * 34 + 28, 4 * 34 + 130)
        self.on_pick, self.current = on_pick, current
        t = QLabel(title)
        t.setObjectName("qzbig")
        t.setStyleSheet("font-size: 16px;")
        self.lay.addWidget(t)
        g = QGridLayout()
        g.setSpacing(0)
        for i, c in enumerate(E.PALETTE):
            g.addWidget(Swatch(c, (current or "").lower() == c.lower(), self.pick, border), i // 8, i % 8)
        self.lay.addLayout(g)
        row = QHBoxLayout()
        b1 = AButton(none_label)
        b1.setObjectName("qzfield")
        b1.setMinimumHeight(32)
        b1.clicked.connect(lambda: self.pick(None))
        b2 = AButton("Özel renk…")
        b2.setObjectName("qzfield")
        b2.setMinimumHeight(32)
        b2.clicked.connect(self.custom)
        row.addWidget(b1)
        row.addWidget(b2)
        self.lay.addLayout(row)

    def pick(self, color):
        self.close()
        self.on_pick(color)

    def custom(self):
        self.close()

        def go():
            c = QColorDialog.getColor(QColor(self.current or "#ffffff"), self.parent(), "Renk seç")
            if c.isValid():
                self.on_pick(c.name())
        QTimer.singleShot(0, go)


# ------------------------------------------------------------------ tema ----
class ThemeCard(QWidget):
    W, H = 150, 96

    def __init__(self, th, selected, locked, cb):
        super().__init__()
        self.th, self.selected, self.locked, self.cb, self.hov = th, selected, locked, cb, False
        self.setFixedSize(self.W + 8, self.H + 8)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def enterEvent(self, e):
        self.hov = True
        self.update()

    def leaveEvent(self, e):
        self.hov = False
        self.update()

    def mouseReleaseEvent(self, e):
        self.cb(self.th["name"])

    def paintEvent(self, e):
        th, W, H = self.th, self.W, self.H
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.translate(4, 4 - (2 if self.hov else 0))
        p.setBrush(QColor(th["bg"]))
        p.setPen(QPen(QColor(th["accent"] if self.selected else th["border"]), 2 if self.selected else 1))
        p.drawRoundedRect(QRectF(1, 1, W - 2, H - 2), 10, 10)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(th["chrome"]))
        p.drawRoundedRect(QRectF(8, 8, W - 16, 14), 5, 5)
        p.setBrush(QColor(th["muted"]))
        for i in range(3):
            p.drawEllipse(QRectF(14 + i * 9, 12, 5, 5))
        p.setBrush(QColor(th["accent"]))
        p.drawRoundedRect(QRectF(W - 46, 11, 31, 8), 3, 3)
        soft = E.mix(th["bg"], th["fg"], 0.35)
        p.setBrush(QColor(soft))
        for i, wd in enumerate((96, 120, 78)):
            p.drawRoundedRect(QRectF(15, 32 + i * 10, wd, 4), 2, 2)
        p.setBrush(QColor(th["sel"]))
        p.drawRoundedRect(QRectF(15, 62, 55, 5), 2, 2)
        p.setBrush(QColor(th["match"]))
        p.drawRoundedRect(QRectF(76, 62, 28, 5), 2, 2)
        p.setPen(QColor(th["fg"]))
        f = QFont()
        f.setPixelSize(11)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(15, H - 22, W - 30, 16), Qt.AlignmentFlag.AlignVCenter, th["name"])
        if self.locked:
            c = QColor(th["chrome"])
            c.setAlpha(190)
            p.setBrush(c)
            p.setPen(QPen(QColor(th["border"]), 1))
            p.drawRoundedRect(QRectF(1, 1, W - 2, H - 2), 10, 10)
            p.setPen(QColor(th["muted"]))
            p.drawText(QRectF(0, H / 2 - 18, W, 16), Qt.AlignmentFlag.AlignCenter, th["name"])
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(th["border"]))
            p.drawRoundedRect(QRectF(W / 2 - 38, H / 2 + 2, 76, 20), 9, 9)
            p.setPen(QColor(th["fg"]))
            f.setBold(False)
            p.setFont(f)
            p.drawText(QRectF(W / 2 - 38, H / 2 + 2, 76, 20), Qt.AlignmentFlag.AlignCenter, "Enterprise+")


class ThemePopup(Popup):
    def __init__(self, parent, current, allowed, on_pick, on_locked):
        super().__init__(parent, 3 * 158 + 28, 3 * 104 + 62)
        self.on_pick, self.on_locked, self.allowed = on_pick, on_locked, allowed
        t = QLabel("Tema")
        t.setObjectName("qzbig")
        t.setStyleSheet("font-size: 16px;")
        self.lay.addWidget(t)
        g = QGridLayout()
        g.setSpacing(0)
        for i, th in enumerate(E.THEME_LIST):
            g.addWidget(ThemeCard(th, th["name"] == current, not allowed(th["name"]), self.pick), i // 3, i % 3)
        self.lay.addLayout(g)
        self.lay.addStretch(1)

    def pick(self, name):
        if not self.allowed(name):
            self.on_locked()
            return
        self.close()
        self.on_pick(name)
