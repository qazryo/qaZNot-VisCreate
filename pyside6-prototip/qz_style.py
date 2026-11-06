"""qaZNot (not defteri) temalı stil: QSS üretici, çizilmiş simgeler, Windows başlık çubuğu rengi."""
import ctypes
import os

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QIcon, QPixmap, QPolygonF

import qv_engine as E

UI_FAMILIES = ("SF Pro Text", "Segoe UI Variable Text", "Segoe UI", "Helvetica", "DejaVu Sans")


def ui_family(available):
    low = {a.lower(): a for a in available}
    for f in UI_FAMILIES:
        if f.lower() in low:
            return low[f.lower()]
    return "Segoe UI"


def qss(t, fam="Segoe UI"):
    mix = lambda a, b, k: E.mix(a, b, k)  # noqa: E731
    return f"""
* {{ font-family: '{fam}'; font-size: 13px; color: {t['fg']}; }}
QMainWindow, QWidget#qzroot {{ background: {t['chrome']}; }}
QDialog {{ background: {t['chrome']}; }}
QFrame {{ background: transparent; border: none; }}
QLabel {{ background: transparent; }}
QFrame#qztop {{ background: {t['chrome']}; border-bottom: 1px solid {t['border']}; }}
QFrame#qztool {{ background: {t['chrome']}; border-bottom: 1px solid {t['border']}; }}
QFrame#qzstatus {{ background: {t['chrome']}; border-top: 1px solid {t['border']}; }}
QFrame#qztabrow {{ background: {t['chrome']}; }}
QTabBar {{ background: transparent; qproperty-drawBase: 0; }}
QTabBar::tab {{ background: transparent; color: {t['muted']}; padding: 5px 8px 5px 12px; margin: 4px 2px 3px 0;
               border-radius: 9px; min-width: 70px; max-width: 220px; }}
QTabBar::tab:hover {{ background: {t['hover']}; color: {t['fg']}; }}
QTabBar::tab:selected {{ background: {t['bg']}; color: {t['fg']}; border: 1px solid {t['border']}; }}
QTabBar::scroller {{ width: 22px; }}
QFrame#qzfind {{ background: {t['chrome']}; border-bottom: 1px solid {t['border']}; }}
QFrame#qzside {{ background: {t['chrome']}; }}
QFrame#qzhome {{ background: {t['bg']}; }}
QFrame#qzedcard {{ background: {t['bg']}; border: 1px solid {t['border']}; border-radius: 14px; }}
QFrame#qzprofile {{ background: {t['bg']}; border: 1px solid {t['border']}; border-radius: 18px; }}
QFrame#qzpopup {{ background: {t['chrome']}; border: 1px solid {t['border']}; border-radius: 14px; }}
QFrame#qzsep {{ background: {t['border']}; min-width: 1px; max-width: 1px; }}
QFrame#qzsepv {{ background: {t['border']}; min-height: 1px; max-height: 1px; }}
QLabel#qzmuted {{ color: {t['muted']}; }}
QLabel#qzsec {{ color: {t['muted']}; font-size: 11px; font-weight: 600; letter-spacing: 1px; }}
QLabel#qzbig {{ font-size: 24px; font-weight: 700; }}
QLabel#qzgreet {{ font-size: 28px; font-weight: 700; }}
QLabel#qzdoc {{ color: {t['muted']}; font-size: 12px; }}
QLabel#qzstat {{ color: {t['muted']}; font-size: 12px; }}
QLabel#qztoast {{ background: {t['fg']}; color: {t['bg']}; border-radius: 17px; padding: 8px 20px; font-weight: 600; }}
QTextEdit#qzedit {{ background: {t['bg']}; color: {t['fg']}; border: none; selection-background-color: {t['sel']};
                    selection-color: {t['fg']}; }}
QLineEdit#qzentry, QLineEdit#qzsearch {{ background: {t['bg']}; border: 1px solid {t['border']}; border-radius: 9px;
                    padding: 5px 10px; selection-background-color: {t['sel']}; selection-color: {t['fg']}; }}
QLineEdit#qzentry:focus, QLineEdit#qzsearch:focus {{ border: 1px solid {t['accent']}; }}
QLineEdit#qzsearch {{ border-radius: 20px; padding: 8px 14px; }}
QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ padding: 5px 10px; border-radius: 7px; }}
QListWidget::item:hover {{ background: {t['hover']}; }}
QListWidget::item:selected {{ background: {t['accent']}; color: {t['accent_fg']}; }}
QMenuBar {{ background: transparent; color: {t['fg']}; spacing: 2px; }}
QMenuBar::item {{ padding: 5px 12px; border-radius: 7px; background: transparent; }}
QMenuBar::item:selected {{ background: {t['hover']}; }}
QMenu {{ background: {t['chrome']}; border: 1px solid {t['border']}; border-radius: 10px; padding: 6px; }}
QMenu::item {{ padding: 6px 26px 6px 14px; border-radius: 6px; }}
QMenu::item:selected {{ background: {t['accent']}; color: {t['accent_fg']}; }}
QMenu::item:disabled {{ color: {t['muted']}; }}
QMenu::separator {{ height: 1px; background: {t['border']}; margin: 5px 8px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {mix(t['bg'], t['muted'], 0.45)}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {t['muted']}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {mix(t['bg'], t['muted'], 0.45)}; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QToolTip {{ background: {t['fg']}; color: {t['bg']}; border: none; padding: 4px 8px; }}
QMessageBox {{ background: {t['chrome']}; }}
QPushButton {{ background: {t['hover']}; border: none; border-radius: 8px; padding: 6px 14px; }}
QPushButton:hover {{ background: {mix(t['hover'], t['fg'], 0.1)}; }}
QCheckBox {{ spacing: 8px; }}
QDoubleSpinBox, QSpinBox {{ background: {t['bg']}; border: 1px solid {t['border']}; border-radius: 8px; padding: 4px 6px; }}
"""


def qz_icon(kind, color, size=22):
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 1.8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    c = size / 2
    if kind in ("tx_l", "tx_c", "tx_r"):
        for i, wd in enumerate((13, 8, 13, 8)):
            y = 5 + i * 4
            x0 = {"tx_l": 4, "tx_c": c - wd / 2, "tx_r": size - 4 - wd}[kind]
            p.drawLine(QPointF(x0, y), QPointF(x0 + wd, y))
    elif kind == "clearfmt":
        f = QFont("Segoe UI")
        f.setPixelSize(14)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(0, 0, size - 6, size), Qt.AlignmentFlag.AlignCenter, "T")
        p.drawLine(QPointF(c + 1, c + 1), QPointF(c + 7, c + 7))
        p.drawLine(QPointF(c + 7, c + 1), QPointF(c + 1, c + 7))
    elif kind == "palette":
        p.drawEllipse(QRectF(3, 3, size - 6, size - 6))
        p.setBrush(QColor(color))
        p.setPen(Qt.PenStyle.NoPen)
        for dx, dy in ((-4, -2), (0, -5), (4, -2), (-3, 3)):
            p.drawEllipse(QPointF(c + dx, c + dy), 1.6, 1.6)
    elif kind == "chev":
        p.drawPolyline(QPolygonF([QPointF(c - 4, c - 2), QPointF(c, c + 2), QPointF(c + 4, c - 2)]))
    elif kind == "chev_r":
        p.drawPolyline(QPolygonF([QPointF(c - 2, c - 4), QPointF(c + 2, c), QPointF(c - 2, c + 4)]))
    elif kind == "up":
        p.drawPolyline(QPolygonF([QPointF(c - 4, c + 2), QPointF(c, c - 2), QPointF(c + 4, c + 2)]))
    elif kind == "close":
        p.drawLine(QPointF(c - 4, c - 4), QPointF(c + 4, c + 4))
        p.drawLine(QPointF(c + 4, c - 4), QPointF(c - 4, c + 4))
    elif kind == "search":
        p.drawEllipse(QRectF(4, 4, 11, 11))
        p.drawLine(QPointF(14, 14), QPointF(19, 19))
    elif kind == "bullets":
        for i in range(3):
            y = 6 + i * 5
            p.drawPoint(QPointF(5, y))
            p.drawEllipse(QPointF(5, y), 1.2, 1.2)
            p.drawLine(QPointF(10, y), QPointF(18, y))
    elif kind == "numbers":
        f = QFont("Segoe UI")
        f.setPixelSize(7)
        p.setFont(f)
        for i in range(3):
            y = 6 + i * 5
            p.drawText(QRectF(2, y - 4, 8, 8), Qt.AlignmentFlag.AlignCenter, str(i + 1))
            p.drawLine(QPointF(11, y), QPointF(19, y))
    elif kind in ("indent", "outdent"):
        for y in (5, 17):
            p.drawLine(QPointF(4, y), QPointF(18, y))
        for y in (9, 13):
            p.drawLine(QPointF(10, y), QPointF(18, y))
        tri = QPolygonF([QPointF(4, 9), QPointF(7.5, 11), QPointF(4, 13)]) if kind == "indent" else \
            QPolygonF([QPointF(8, 9), QPointF(4.5, 11), QPointF(8, 13)])
        p.setBrush(QColor(color))
        p.drawPolygon(tri)
    elif kind == "linespace":
        p.drawLine(QPointF(11, 4), QPointF(11, 18))
        p.drawPolyline(QPolygonF([QPointF(8, 7), QPointF(11, 4), QPointF(14, 7)]))
        p.drawPolyline(QPolygonF([QPointF(8, 15), QPointF(11, 18), QPointF(14, 15)]))
        p.drawLine(QPointF(16, 6), QPointF(19, 6))
        p.drawLine(QPointF(16, 11), QPointF(19, 11))
        p.drawLine(QPointF(16, 16), QPointF(19, 16))
    elif kind == "image":
        p.drawRoundedRect(QRectF(3.5, 5, 15, 12), 2, 2)
        p.drawEllipse(QRectF(7, 8, 3, 3))
        p.drawPolyline(QPolygonF([QPointF(4, 16), QPointF(9, 12), QPointF(13, 15), QPointF(15.5, 12.5), QPointF(18.5, 15.5)]))
    elif kind == "minus":
        p.drawLine(QPointF(c - 5, c), QPointF(c + 5, c))
    elif kind == "plus":
        p.drawLine(QPointF(c - 5, c), QPointF(c + 5, c))
        p.drawLine(QPointF(c, c - 5), QPointF(c, c + 5))
    p.end()
    return QIcon(pm)


def set_titlebar(win, t):
    """Windows 11: başlık çubuğunu tema renklerine boyar (diğer sistemlerde yok sayılır)."""
    if os.name != "nt":
        return
    try:
        hwnd = int(win.winId())
        dwm = ctypes.windll.dwmapi

        def bgr(h):
            c = QColor(h)
            return ctypes.c_int(c.red() | (c.green() << 8) | (c.blue() << 16))
        dark = ctypes.c_int(1 if t["dark"] else 0)
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), 4)
        for attr, col in ((35, t["chrome"]), (34, t["border"]), (36, t["fg"])):
            v = bgr(col)
            dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(v), 4)
    except Exception:  # noqa: BLE001
        pass
