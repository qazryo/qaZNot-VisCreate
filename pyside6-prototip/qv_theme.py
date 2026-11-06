"""Ortak tema (Figma tarzi koyu) ve cizilmis simgeler."""
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QIcon, QPixmap, QPolygonF

ACCENT = "#0D99FF"
FAMILY = "Segoe UI"

QSS = f"""
* {{ font-family: '{FAMILY}'; font-size: 12px; color: #E6E6E6; }}
QMainWindow, QWidget#root {{ background: #1E1E1E; }}
QDialog {{ background: #2C2C2C; }}
QMessageBox {{ background: #2C2C2C; }}
QFrame#topbar {{ background: #2C2C2C; border-bottom: 1px solid #3A3A3A; }}
QFrame#toolbar {{ background: #2C2C2C; border-right: 1px solid #3A3A3A; }}
QFrame#flyout {{ background: #2C2C2C; border-right: 1px solid #3A3A3A; }}
QFrame#side {{ background: #2C2C2C; border-left: 1px solid #3A3A3A; }}
QDialog#loginroot {{ background: #14151A; }}
QFrame#lcard {{ background: #2C2C2C; border: 1px solid #3A3A3A; border-radius: 24px; }}
QFrame#plain {{ background: transparent; border: none; }}
QFrame#card {{ background: #1E1E1E; border: 1px solid #3A3A3A; border-radius: 16px; }}
QLabel#logo {{ font-size: 14px; font-weight: 700; color: white; }}
QLabel#title {{ color: #9A9A9A; }}
QLabel#big {{ font-size: 22px; font-weight: 700; color: white; }}
QLabel#sub {{ color: #9A9A9A; }}
QLabel#err {{ color: #FF6B5E; }}
QLabel#ok {{ color: #32D74B; }}
QLabel#sec {{ color: #9A9A9A; font-size: 11px; font-weight: 600; letter-spacing: 1px; }}
QLabel#hint {{ color: #6F6F6F; }}
QLabel#toast {{ color: #32D74B; }}
QLabel#chip {{ background: #3C3C3C; border-radius: 10px; padding: 2px 8px; font-size: 11px; font-weight: 600; }}
QFrame#sep {{ background: #3A3A3A; max-height: 1px; min-height: 1px; }}
QToolButton {{ background: transparent; border: none; border-radius: 6px; }}
QToolButton:hover {{ background: #3C3C3C; }}
QToolButton:checked {{ background: {ACCENT}; }}
QToolButton:disabled {{ background: transparent; }}
QPushButton {{ background: #3C3C3C; border: none; border-radius: 6px; padding: 6px 12px; }}
QPushButton:hover {{ background: #4A4A4A; }}
QPushButton:disabled {{ color: #6F6F6F; }}
QPushButton#accent {{ background: {ACCENT}; color: white; font-weight: 600; }}
QPushButton#accent:hover {{ background: #2BA8FF; }}
QPushButton#accent:disabled {{ background: #1C4E70; color: #8FB8D4; }}
QPushButton#big {{ padding: 11px 14px; font-size: 13px; }}
QPushButton#flat {{ background: transparent; }}
QPushButton#flat:hover {{ background: #3C3C3C; }}
QPushButton#account {{ background: #3C3C3C; border-radius: 16px; padding: 4px 12px 4px 4px; text-align: left; }}
QFrame#field {{ background: #383838; border: 1px solid transparent; border-radius: 6px; }}
QFrame#field:hover {{ border: 1px solid #4F4F4F; }}
QFrame#field:focus-within {{ border: 1px solid {ACCENT}; }}
QFrame#field QLabel {{ color: #8C8C8C; padding-left: 8px; min-width: 14px; }}
QDoubleSpinBox {{ background: transparent; border: none; padding: 6px 0px; min-width: 40px; selection-background-color: {ACCENT}; }}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0px; height: 0px; border: none; }}
QLineEdit#bare, QPlainTextEdit#bare {{ background: #383838; border: 1px solid transparent; border-radius: 6px; padding: 6px 8px; selection-background-color: {ACCENT}; }}
QLineEdit#bare:focus, QPlainTextEdit#bare:focus {{ border: 1px solid {ACCENT}; }}
QLineEdit#key {{ background: #1E1E1E; border: 1px solid #3A3A3A; border-radius: 12px; padding: 12px; font-family: Consolas; font-size: 16px; selection-background-color: {ACCENT}; }}
QLineEdit#key:focus {{ border: 2px solid {ACCENT}; }}
QLineEdit#keyerr {{ background: #1E1E1E; border: 2px solid #FF453A; border-radius: 12px; padding: 12px; font-family: Consolas; font-size: 16px; }}
QComboBox {{ background: #383838; border: 1px solid transparent; border-radius: 6px; padding: 5px 8px; }}
QComboBox:hover {{ border: 1px solid #4F4F4F; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: #2C2C2C; border: 1px solid #444; selection-background-color: {ACCENT}; outline: none; }}
QPushButton#swatch {{ border: 1px solid #555; border-radius: 4px; min-width: 22px; max-width: 22px; min-height: 22px; max-height: 22px; padding: 0; }}
QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ padding: 6px 8px; border-radius: 6px; }}
QListWidget::item:hover {{ background: #383838; }}
QListWidget::item:selected {{ background: #0D5A8F; }}
QGraphicsView {{ border: none; }}
QToolTip {{ background: #111; color: white; border: 1px solid #444; padding: 4px; }}
QMenu {{ background: #2C2C2C; border: 1px solid #444; padding: 4px; }}
QMenu::item {{ padding: 6px 22px; border-radius: 4px; }}
QMenu::item:selected {{ background: {ACCENT}; }}
QScrollBar:vertical {{ background: transparent; width: 8px; }}
QScrollBar::handle:vertical {{ background: #4A4A4A; border-radius: 4px; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QCheckBox {{ spacing: 8px; }}
"""


def make_icon(kind, color="#E6E6E6", size=24):
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 1.7)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    if kind == "select":
        poly = QPolygonF([QPointF(6, 3), QPointF(6, 19), QPointF(10.5, 15), QPointF(13.5, 21),
                          QPointF(16, 20), QPointF(13, 14), QPointF(19, 14)])
        p.setBrush(QColor(color))
        p.drawPolygon(poly)
    elif kind == "rect":
        p.drawRoundedRect(QRectF(4, 5, 16, 14), 2, 2)
    elif kind == "ellipse":
        p.drawEllipse(QRectF(4, 4, 16, 16))
    elif kind == "line":
        p.drawLine(QPointF(5, 19), QPointF(19, 5))
    elif kind == "text":
        f = QFont(FAMILY)
        f.setPixelSize(17)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, "T")
    elif kind == "image":
        p.drawRoundedRect(QRectF(4, 5, 16, 14), 2, 2)
        p.drawEllipse(QRectF(8, 8, 3, 3))
        p.drawPolyline(QPolygonF([QPointF(4.5, 18), QPointF(10, 13), QPointF(14, 16),
                                  QPointF(16.5, 13.5), QPointF(19.5, 17)]))
    elif kind in ("al_l", "al_ch", "al_r", "al_t", "al_cv", "al_b"):
        p.setBrush(QColor(color))
        p.setPen(Qt.PenStyle.NoPen)
        if kind in ("al_l", "al_ch", "al_r"):
            x = {"al_l": 5, "al_ch": 12, "al_r": 19}[kind]
            p.drawRect(QRectF(x - 0.8, 3, 1.6, 18))
            p.drawRoundedRect(QRectF(x if kind == "al_l" else (x - 4 if kind == "al_ch" else x - 9), 7, 9 if kind != "al_ch" else 8, 4), 1, 1)
            p.drawRoundedRect(QRectF(x if kind == "al_l" else (x - 3 if kind == "al_ch" else x - 6), 13, 6 if kind != "al_ch" else 6, 4), 1, 1)
        else:
            y = {"al_t": 5, "al_cv": 12, "al_b": 19}[kind]
            p.drawRect(QRectF(3, y - 0.8, 18, 1.6))
            p.drawRoundedRect(QRectF(7, y if kind == "al_t" else (y - 4 if kind == "al_cv" else y - 9), 4, 9 if kind != "al_cv" else 8), 1, 1)
            p.drawRoundedRect(QRectF(13, y if kind == "al_t" else (y - 3 if kind == "al_cv" else y - 6), 4, 6), 1, 1)
    elif kind in ("dist_h", "dist_v"):
        p.setBrush(QColor(color))
        p.setPen(Qt.PenStyle.NoPen)
        if kind == "dist_h":
            p.drawRect(QRectF(3, 4, 1.6, 16))
            p.drawRect(QRectF(19.4, 4, 1.6, 16))
            p.drawRoundedRect(QRectF(9, 8, 6, 8), 1, 1)
        else:
            p.drawRect(QRectF(4, 3, 16, 1.6))
            p.drawRect(QRectF(4, 19.4, 16, 1.6))
            p.drawRoundedRect(QRectF(8, 9, 8, 6), 1, 1)
    elif kind in ("tx_l", "tx_c", "tx_r"):
        for i, wd in enumerate((14, 9, 14, 9)):
            y = 6 + i * 4
            x0 = {"tx_l": 5, "tx_c": 12 - wd / 2, "tx_r": 19 - wd}[kind]
            p.drawLine(QPointF(x0, y), QPointF(x0 + wd, y))
    elif kind == "undo":
        p.drawArc(QRectF(6, 7, 13, 11), 0, 170 * 16)
        p.drawPolyline(QPolygonF([QPointF(9, 4), QPointF(5.5, 8), QPointF(10, 11)]))
    elif kind == "redo":
        p.drawArc(QRectF(5, 7, 13, 11), 10 * 16, 170 * 16)
        p.drawPolyline(QPolygonF([QPointF(15, 4), QPointF(18.5, 8), QPointF(14, 11)]))
    p.end()
    return QIcon(pm)
