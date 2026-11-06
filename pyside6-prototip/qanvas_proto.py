"""qAnvas - PySide6 prototip (Figma tarzi arayuz). Motor henuz bagli degil."""
import os
import sys

if "--shot" in sys.argv:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QSize, QTimer
from PySide6.QtGui import (QColor, QPainter, QPen, QBrush, QFont, QIcon, QPixmap,
                           QPainterPath, QLinearGradient, QShortcut, QKeySequence,
                           QPolygonF, QImage)
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QFrame, QLabel, QToolButton, QButtonGroup, QDoubleSpinBox,
                               QLineEdit, QPushButton, QListWidget, QListWidgetItem,
                               QGraphicsScene, QGraphicsView, QGraphicsObject, QGraphicsItem,
                               QGraphicsRectItem, QGraphicsDropShadowEffect, QColorDialog,
                               QFileDialog, QGridLayout, QSizePolicy)

ACCENT = "#0D99FF"
FAMILY = "Segoe UI"
ART_W, ART_H = 1280, 720

HANDLES = {"tl": (0, 0), "t": (.5, 0), "tr": (1, 0), "r": (1, .5),
           "br": (1, 1), "b": (.5, 1), "bl": (0, 1), "l": (0, .5)}
CURSORS = {"tl": Qt.CursorShape.SizeFDiagCursor, "br": Qt.CursorShape.SizeFDiagCursor,
           "tr": Qt.CursorShape.SizeBDiagCursor, "bl": Qt.CursorShape.SizeBDiagCursor,
           "t": Qt.CursorShape.SizeVerCursor, "b": Qt.CursorShape.SizeVerCursor,
           "l": Qt.CursorShape.SizeHorCursor, "r": Qt.CursorShape.SizeHorCursor}
LABELS = {"rect": "Dikdörtgen", "ellipse": "Elips", "text": "Metin", "image": "Görsel"}

QSS = f"""
* {{ font-family: '{FAMILY}'; font-size: 12px; color: #E6E6E6; }}
QMainWindow, QWidget#root {{ background: #1E1E1E; }}
QFrame#topbar {{ background: #2C2C2C; border-bottom: 1px solid #3A3A3A; }}
QFrame#toolbar {{ background: #2C2C2C; border-right: 1px solid #3A3A3A; }}
QFrame#side {{ background: #2C2C2C; border-left: 1px solid #3A3A3A; }}
QLabel#logo {{ font-size: 14px; font-weight: 700; color: white; }}
QLabel#title {{ color: #9A9A9A; }}
QLabel#sec {{ color: #9A9A9A; font-size: 11px; font-weight: 600; letter-spacing: 1px; }}
QLabel#hint {{ color: #6F6F6F; }}
QFrame#sep {{ background: #3A3A3A; max-height: 1px; min-height: 1px; }}
QToolButton {{ background: transparent; border: none; border-radius: 6px; }}
QToolButton:hover {{ background: #3C3C3C; }}
QToolButton:checked {{ background: {ACCENT}; }}
QPushButton {{ background: #3C3C3C; border: none; border-radius: 6px; padding: 6px 12px; }}
QPushButton:hover {{ background: #4A4A4A; }}
QPushButton#accent {{ background: {ACCENT}; color: white; font-weight: 600; }}
QPushButton#accent:hover {{ background: #2BA8FF; }}
QFrame#field {{ background: #383838; border: 1px solid transparent; border-radius: 6px; }}
QFrame#field:hover {{ border: 1px solid #4F4F4F; }}
QFrame#field:focus-within {{ border: 1px solid {ACCENT}; }}
QFrame#field QLabel {{ color: #8C8C8C; padding-left: 8px; min-width: 14px; }}
QDoubleSpinBox {{ background: transparent; border: none; padding: 6px 0px; min-width: 40px; selection-background-color: {ACCENT}; }}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0px; height: 0px; border: none; }}
QLineEdit#bare {{ background: #383838; border: none; border-radius: 6px; padding: 6px 8px; selection-background-color: {ACCENT}; }}
QPushButton#swatch {{ border: 1px solid #555; border-radius: 4px; min-width: 22px; max-width: 22px;
                      min-height: 22px; max-height: 22px; padding: 0; }}
QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ padding: 6px 8px; border-radius: 6px; }}
QListWidget::item:hover {{ background: #383838; }}
QListWidget::item:selected {{ background: #0D5A8F; }}
QGraphicsView {{ border: none; }}
QToolTip {{ background: #111; color: white; border: 1px solid #444; padding: 4px; }}
"""


def make_icon(kind, color="#E6E6E6", size=24):
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 1.7)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
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
    p.end()
    return QIcon(pm)


class Layer(QGraphicsObject):
    geo_changed = Signal()
    PAD = 60

    def __init__(self, kind, w, h, name):
        super().__init__()
        self.kind, self.w, self.h, self.name = kind, float(w), float(h), name
        self.fill = QColor("#1E1E1E" if kind == "text" else "#7B61FF")
        self.text = "Metin"
        self.font_px = 32
        self.radius = 0.0
        self._rs = None
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
                      QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
                      QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)

    def _zoom(self):
        sc = self.scene()
        if sc and sc.views():
            return max(sc.views()[0].transform().m11(), 0.01)
        return 1.0

    def boundingRect(self):
        return QRectF(-self.PAD, -self.PAD, self.w + 2 * self.PAD, self.h + 2 * self.PAD)

    def shape(self):
        path = QPainterPath()
        path.addRect(QRectF(0, 0, self.w, self.h))
        if self.isSelected():
            s = 7 / self._zoom()
            for fx, fy in HANDLES.values():
                path.addRect(QRectF(fx * self.w - s, fy * self.h - s, 2 * s, 2 * s))
        return path

    def handle_at(self, pos):
        s = 7 / self._zoom()
        for k, (fx, fy) in HANDLES.items():
            if abs(pos.x() - fx * self.w) <= s and abs(pos.y() - fy * self.h) <= s:
                return k
        return None

    def set_geometry(self, x, y, w, h):
        self.prepareGeometryChange()
        self.w, self.h = max(float(w), 4.0), max(float(h), 4.0)
        self.setPos(x, y)
        self.update()
        self.geo_changed.emit()

    def paint(self, p, opt, widget=None):
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.w, self.h)
        r = min(self.radius, min(self.w, self.h) / 2)
        if self.kind == "rect":
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self.fill)
            p.drawRoundedRect(rect, r, r)
        elif self.kind == "ellipse":
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self.fill)
            p.drawEllipse(rect)
        elif self.kind == "image":
            self._paint_image(p, rect, r)
        elif self.kind == "text":
            f = QFont(FAMILY)
            f.setPixelSize(int(self.font_px))
            p.setFont(f)
            p.setPen(self.fill)
            p.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop |
                       Qt.TextFlag.TextWordWrap, self.text)
        if self.isSelected():
            lod = opt.levelOfDetailFromTransform(p.worldTransform())
            p.setPen(QPen(QColor(ACCENT), 1.5 / lod))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(rect)
            p.setBrush(QColor("white"))
            p.setPen(QPen(QColor(ACCENT), 1.2 / lod))
            hs = 8 / lod
            for fx, fy in HANDLES.values():
                p.drawRect(QRectF(fx * self.w - hs / 2, fy * self.h - hs / 2, hs, hs))

    def _paint_image(self, p, rect, r):
        clip = QPainterPath()
        clip.addRoundedRect(rect, r, r)
        p.save()
        p.setClipPath(clip)
        g = QLinearGradient(rect.topLeft(), rect.bottomRight())
        g.setColorAt(0, QColor("#FF9A8B"))
        g.setColorAt(1, QColor("#6A82FB"))
        p.fillRect(rect, g)
        w, h = rect.width(), rect.height()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 190))
        p.drawEllipse(QPointF(w * 0.72, h * 0.28), h * 0.12, h * 0.12)
        p.setBrush(QColor(30, 30, 60, 150))
        p.drawPolygon(QPolygonF([QPointF(0, h), QPointF(w * 0.35, h * 0.45),
                                 QPointF(w * 0.62, h), ]))
        p.setBrush(QColor(20, 20, 40, 190))
        p.drawPolygon(QPolygonF([QPointF(w * 0.3, h), QPointF(w * 0.68, h * 0.55),
                                 QPointF(w, h)]))
        p.restore()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.geo_changed.emit()
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.prepareGeometryChange()
        return super().itemChange(change, value)

    def hoverMoveEvent(self, e):
        k = self.handle_at(e.pos()) if self.isSelected() else None
        if k:
            self.setCursor(CURSORS[k])
        else:
            self.unsetCursor()
        super().hoverMoveEvent(e)

    def mousePressEvent(self, e):
        k = self.handle_at(e.pos()) if self.isSelected() else None
        if k and e.button() == Qt.MouseButton.LeftButton:
            self._rs = (k, QRectF(self.pos().x(), self.pos().y(), self.w, self.h))
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._rs:
            k, r0 = self._rs
            x0, y0, x1, y1 = r0.left(), r0.top(), r0.right(), r0.bottom()
            sp = e.scenePos()
            if "l" in k:
                x0 = min(sp.x(), x1 - 4)
            if "r" in k:
                x1 = max(sp.x(), x0 + 4)
            if "t" in k:
                y0 = min(sp.y(), y1 - 4)
            if "b" in k:
                y1 = max(sp.y(), y0 + 4)
            self.set_geometry(x0, y0, x1 - x0, y1 - y0)
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._rs:
            self._rs = None
            return
        super().mouseReleaseEvent(e)


class Canvas(QGraphicsView):
    zoom_changed = Signal(float)

    def __init__(self, scene, win):
        super().__init__(scene)
        self.win = win
        self.setRenderHints(QPainter.RenderHint.Antialiasing |
                            QPainter.RenderHint.SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._space = False
        self._pan = None
        self._creating = None
        self._origin = None

    def zoom(self):
        return self.transform().m11()

    def zoom_by(self, f, under_mouse=True):
        z = self.zoom()
        f = max(0.05, min(8.0, z * f)) / z
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse if under_mouse
                                     else QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.scale(f, f)
        self.zoom_changed.emit(self.zoom())

    def fit(self):
        self.fitInView(QRectF(0, 0, ART_W, ART_H).adjusted(-90, -90, 90, 90),
                       Qt.AspectRatioMode.KeepAspectRatio)
        self.zoom_changed.emit(self.zoom())

    def drawBackground(self, p, rect):
        p.fillRect(rect, QColor("#1E1E1E"))
        z = self.zoom()
        step = 20.0
        while step * z < 14:
            step *= 2
        pen = QPen(QColor("#3A3A3A"), 2)
        pen.setCosmetic(True)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        x = int(rect.left() // step) * step
        while x < rect.right():
            y = int(rect.top() // step) * step
            while y < rect.bottom():
                p.drawPoint(QPointF(x, y))
                y += step
            x += step

    def wheelEvent(self, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom_by(1.0015 ** e.angleDelta().y())
            return
        d = e.angleDelta()
        if e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - d.y())
        else:
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - d.y())
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - d.x())

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Space and not e.isAutoRepeat():
            self._space = True
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
            return
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key.Key_Space and not e.isAutoRepeat():
            self._space = False
            self.viewport().unsetCursor()
            return
        super().keyReleaseEvent(e)

    def mousePressEvent(self, e):
        self.setFocus()
        if e.button() == Qt.MouseButton.MiddleButton or (
                e.button() == Qt.MouseButton.LeftButton and self._space):
            self._pan = e.position()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if e.button() == Qt.MouseButton.LeftButton and self.win.tool != "select":
            self._origin = self.mapToScene(e.position().toPoint())
            self._creating = self.win.new_layer(self.win.tool, self._origin, 1, 1)
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._pan is not None:
            d = e.position() - self._pan
            self._pan = e.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(d.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(d.y()))
            return
        if self._creating:
            p = self.mapToScene(e.position().toPoint())
            o = self._origin
            self._creating.set_geometry(min(o.x(), p.x()), min(o.y(), p.y()),
                                        abs(p.x() - o.x()), abs(p.y() - o.y()))
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._pan is not None:
            self._pan = None
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor if self._space
                                      else Qt.CursorShape.ArrowCursor)
            return
        if self._creating:
            it = self._creating
            if it.w < 8 and it.h < 8:
                dw, dh = (220, 48) if it.kind == "text" else (180, 130)
                it.set_geometry(it.pos().x(), it.pos().y(), dw, dh)
            self._creating = None
            self.win.set_tool("select")
            return
        super().mouseReleaseEvent(e)


class ScrubLabel(QLabel):
    def __init__(self, text, spin, step=1.0):
        super().__init__(text)
        self.spin, self.step, self._x = spin, step, 0
        self.setCursor(Qt.CursorShape.SizeHorCursor)

    def mousePressEvent(self, e):
        self._x = e.globalPosition().x()

    def mouseMoveEvent(self, e):
        x = e.globalPosition().x()
        self.spin.setValue(self.spin.value() + (x - self._x) * self.step)
        self._x = x


def make_field(label, lo=-99999, hi=99999, step=1.0, suffix=""):
    fr = QFrame()
    fr.setObjectName("field")
    lay = QHBoxLayout(fr)
    lay.setContentsMargins(0, 0, 4, 0)
    lay.setSpacing(0)
    sp = QDoubleSpinBox()
    sp.setRange(lo, hi)
    sp.setDecimals(0)
    sp.setSuffix(suffix)
    sp.setKeyboardTracking(False)
    lay.addWidget(ScrubLabel(label, sp, step))
    lay.addWidget(sp, 1)
    return fr, sp


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("qAnvas - PySide6 prototip")
        icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "icon.png")
        if os.path.exists(icon):
            self.setWindowIcon(QIcon(icon))
        self.resize(1440, 860)
        self.tool = "select"
        self.cur = None
        self._busy = False
        self._z = 0
        self._count = {}

        self.scene = QGraphicsScene(-4000, -4000, 9280, 8720)
        art = QGraphicsRectItem(0, 0, ART_W, ART_H)
        art.setBrush(QColor("white"))
        art.setPen(Qt.PenStyle.NoPen)
        art.setZValue(-1e6)
        sh = QGraphicsDropShadowEffect()
        sh.setBlurRadius(40)
        sh.setOffset(0, 8)
        sh.setColor(QColor(0, 0, 0, 160))
        art.setGraphicsEffect(sh)
        self.scene.addItem(art)
        self.art = art
        self.view = Canvas(self.scene, self)

        root = QWidget()
        root.setObjectName("root")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_topbar())
        body = QHBoxLayout()
        body.setSpacing(0)
        body.addWidget(self._build_toolbar())
        body.addWidget(self.view, 1)
        body.addWidget(self._build_side())
        outer.addLayout(body, 1)
        self.setCentralWidget(root)

        self.scene.selectionChanged.connect(self.on_selection)
        self.view.zoom_changed.connect(lambda z: self.zoom_lbl.setText(f"{round(z * 100)}%"))
        self._shortcuts()
        self._demo()
        self.sync_props()
        QTimer.singleShot(0, self.view.fit)

    # ---- arayuz parcalari ----
    def _build_topbar(self):
        bar = QFrame()
        bar.setObjectName("topbar")
        bar.setFixedHeight(46)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 0, 12, 0)
        logo = QLabel("qAnvas")
        logo.setObjectName("logo")
        sep = QLabel("/")
        sep.setObjectName("title")
        title = QLabel("Adsız tasarım")
        title.setObjectName("title")
        lay.addWidget(logo)
        lay.addSpacing(8)
        lay.addWidget(sep)
        lay.addSpacing(4)
        lay.addWidget(title)
        lay.addStretch(1)
        for txt, f in (("−", 1 / 1.25), ):
            b = QToolButton()
            b.setText(txt)
            b.setFixedSize(28, 28)
            b.clicked.connect(lambda _=False, f=f: self.view.zoom_by(f, False))
            lay.addWidget(b)
        self.zoom_lbl = QLabel("100%")
        self.zoom_lbl.setFixedWidth(46)
        self.zoom_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.zoom_lbl)
        b = QToolButton()
        b.setText("+")
        b.setFixedSize(28, 28)
        b.clicked.connect(lambda: self.view.zoom_by(1.25, False))
        lay.addWidget(b)
        fit = QPushButton("Sığdır")
        fit.clicked.connect(self.view.fit)
        lay.addWidget(fit)
        lay.addSpacing(10)
        exp = QPushButton("Dışa aktar")
        exp.setObjectName("accent")
        exp.clicked.connect(self.export_png)
        lay.addWidget(exp)
        return bar

    def _build_toolbar(self):
        bar = QFrame()
        bar.setObjectName("toolbar")
        bar.setFixedWidth(52)
        lay = QVBoxLayout(bar)
        lay.setContentsMargins(8, 10, 8, 10)
        lay.setSpacing(4)
        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)
        self.tool_btns = {}
        for key, tip in (("select", "Seç (V)"), ("rect", "Dikdörtgen (R)"),
                         ("ellipse", "Elips (O)"), ("text", "Metin (T)"),
                         ("image", "Görsel (I)")):
            b = QToolButton()
            b.setIcon(make_icon(key))
            b.setIconSize(QSize(22, 22))
            b.setFixedSize(36, 36)
            b.setCheckable(True)
            b.setToolTip(tip)
            b.clicked.connect(lambda _=False, k=key: self.set_tool(k))
            self.tool_group.addButton(b)
            self.tool_btns[key] = b
            lay.addWidget(b)
        self.tool_btns["select"].setChecked(True)
        lay.addStretch(1)
        return bar

    def _build_side(self):
        side = QFrame()
        side.setObjectName("side")
        side.setFixedWidth(264)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(14, 14, 14, 10)
        lay.setSpacing(8)

        sec = QLabel("TASARIM")
        sec.setObjectName("sec")
        lay.addWidget(sec)
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        f, self.sx = make_field("X")
        grid.addWidget(f, 0, 0)
        f, self.sy = make_field("Y")
        grid.addWidget(f, 0, 1)
        f, self.sw = make_field("W", 4)
        grid.addWidget(f, 1, 0)
        f, self.sh = make_field("H", 4)
        grid.addWidget(f, 1, 1)
        f, self.sr = make_field("R", 0, 2000)
        grid.addWidget(f, 2, 0)
        f, self.so = make_field("%", 0, 100, 1.0)
        grid.addWidget(f, 2, 1)
        lay.addLayout(grid)
        for sp in (self.sx, self.sy, self.sw, self.sh):
            sp.valueChanged.connect(self.apply_geo)
        self.sr.valueChanged.connect(self.apply_radius)
        self.so.valueChanged.connect(self.apply_opacity)

        sep = QFrame()
        sep.setObjectName("sep")
        lay.addSpacing(4)
        lay.addWidget(sep)
        lay.addSpacing(2)

        sec = QLabel("DOLGU")
        sec.setObjectName("sec")
        lay.addWidget(sec)
        row = QHBoxLayout()
        self.swatch = QPushButton()
        self.swatch.setObjectName("swatch")
        self.swatch.clicked.connect(self.pick_color)
        self.hex_lbl = QLabel("#7B61FF")
        row.addWidget(self.swatch)
        row.addWidget(self.hex_lbl, 1)
        lay.addLayout(row)

        self.text_edit = QLineEdit()
        self.text_edit.setObjectName("bare")
        self.text_edit.setPlaceholderText("Metin")
        self.text_edit.textChanged.connect(self.apply_text)
        lay.addWidget(self.text_edit)
        f, self.sfont = make_field("Aa", 6, 400)
        lay.addWidget(f)
        self.sfont.valueChanged.connect(self.apply_font)

        sep = QFrame()
        sep.setObjectName("sep")
        lay.addSpacing(4)
        lay.addWidget(sep)
        lay.addSpacing(2)

        sec = QLabel("KATMANLAR")
        sec.setObjectName("sec")
        lay.addWidget(sec)
        self.layers = QListWidget()
        self.layers.setIconSize(QSize(16, 16))
        self.layers.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.layers.itemSelectionChanged.connect(self.on_list_selection)
        lay.addWidget(self.layers, 1)
        hint = QLabel("V R O T I araçlar · Ctrl+tekerlek yakınlaştır · Boşluk+sürükle kaydır")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        return side

    def _shortcuts(self):
        def sc(keys, fn):
            s = QShortcut(QKeySequence(keys), self)
            s.activated.connect(fn)
        for k, t in (("V", "select"), ("R", "rect"), ("O", "ellipse"), ("T", "text"), ("I", "image")):
            sc(k, lambda t=t: self.set_tool(t))
        sc("Delete", self.delete_selected)
        sc("Backspace", self.delete_selected)
        sc("Ctrl+D", self.duplicate)
        sc("Ctrl+]", lambda: self.reorder(+1))
        sc("Ctrl+[", lambda: self.reorder(-1))
        sc("Ctrl+0", self.view.fit)
        sc("Ctrl+=", lambda: self.view.zoom_by(1.25, False))
        sc("Ctrl+-", lambda: self.view.zoom_by(1 / 1.25, False))
        sc("Escape", lambda: (self.set_tool("select"), self.scene.clearSelection()))

    # ---- islevler ----
    def set_tool(self, key):
        self.tool = key
        self.tool_btns[key].setChecked(True)
        self.view.viewport().setCursor(Qt.CursorShape.ArrowCursor if key == "select"
                                       else Qt.CursorShape.CrossCursor)

    def new_layer(self, kind, pos, w, h, select=True):
        self._count[kind] = self._count.get(kind, 0) + 1
        it = Layer(kind, w, h, f"{LABELS[kind]} {self._count[kind]}")
        self._z += 1
        it.setZValue(self._z)
        it.setPos(pos)
        self.scene.addItem(it)
        it.geo_changed.connect(lambda it=it: self.sync_props() if it is self.cur else None)
        if select:
            self.scene.clearSelection()
            it.setSelected(True)
        self.rebuild_list()
        return it

    def _demo(self):
        img = self.new_layer("image", QPointF(80, 80), 520, 360, False)
        img.radius = 24
        card = self.new_layer("rect", QPointF(680, 80), 520, 250, False)
        card.radius = 24
        card.fill = QColor("#7B61FF")
        circ = self.new_layer("ellipse", QPointF(700, 380), 160, 160, False)
        circ.fill = QColor("#FF4D8D")
        bar = self.new_layer("rect", QPointF(900, 420), 300, 80, False)
        bar.fill = QColor("#14C38E")
        bar.radius = 40
        t1 = self.new_layer("text", QPointF(716, 112), 460, 90, False)
        t1.text, t1.font_px, t1.fill = "qAnvas", 76, QColor("white")
        t2 = self.new_layer("text", QPointF(718, 220), 460, 80, False)
        t2.text, t2.font_px, t2.fill = "Yeni nesil tasarım aracı", 30, QColor(255, 255, 255, 220)
        t3 = self.new_layer("text", QPointF(80, 520), 900, 120, False)
        t3.text, t3.font_px = "Figma tarzı arayüz prototipi", 52
        self.scene.clearSelection()
        self.rebuild_list()

    def layer_items(self):
        return sorted((i for i in self.scene.items() if isinstance(i, Layer)),
                      key=lambda i: i.zValue(), reverse=True)

    def rebuild_list(self):
        self._busy = True
        self.layers.clear()
        for it in self.layer_items():
            li = QListWidgetItem(make_icon(it.kind), it.name)
            li.setData(Qt.ItemDataRole.UserRole, it)
            self.layers.addItem(li)
            li.setSelected(it.isSelected())
        self._busy = False

    def on_list_selection(self):
        if self._busy:
            return
        self._busy = True
        self.scene.clearSelection()
        for li in self.layers.selectedItems():
            li.data(Qt.ItemDataRole.UserRole).setSelected(True)
        self._busy = False
        self.on_selection(from_list=True)

    def on_selection(self, from_list=False):
        try:
            sel = [i for i in self.scene.selectedItems() if isinstance(i, Layer)]
        except RuntimeError:
            return
        self.cur = sel[0] if len(sel) == 1 else None
        if not from_list and not self._busy:
            self._busy = True
            for k in range(self.layers.count()):
                li = self.layers.item(k)
                li.setSelected(li.data(Qt.ItemDataRole.UserRole).isSelected())
            self._busy = False
        self.sync_props()

    def sync_props(self):
        c = self.cur
        self._busy = True
        widgets = (self.sx, self.sy, self.sw, self.sh, self.sr, self.so, self.swatch)
        for w in widgets:
            w.setEnabled(c is not None)
        is_text = c is not None and c.kind == "text"
        self.text_edit.setEnabled(is_text)
        self.sfont.setEnabled(is_text)
        self.sr.setEnabled(c is not None and c.kind in ("rect", "image"))
        if c is not None:
            self.sx.setValue(round(c.pos().x()))
            self.sy.setValue(round(c.pos().y()))
            self.sw.setValue(round(c.w))
            self.sh.setValue(round(c.h))
            self.sr.setValue(round(c.radius))
            self.so.setValue(round(c.opacity() * 100))
            self.hex_lbl.setText(c.fill.name().upper())
            self.swatch.setStyleSheet(f"background: {c.fill.name()};")
            if is_text:
                if self.text_edit.text() != c.text:
                    self.text_edit.setText(c.text)
                self.sfont.setValue(c.font_px)
        else:
            self.hex_lbl.setText("—")
            self.swatch.setStyleSheet("background: #444;")
            self.text_edit.setText("")
        self._busy = False

    def _ok(self):
        return self.cur is not None and not self._busy

    def apply_geo(self):
        if self._ok():
            self.cur.set_geometry(self.sx.value(), self.sy.value(), self.sw.value(), self.sh.value())

    def apply_radius(self):
        if self._ok():
            self.cur.radius = self.sr.value()
            self.cur.update()

    def apply_opacity(self):
        if self._ok():
            self.cur.setOpacity(self.so.value() / 100)

    def apply_text(self, t):
        if self._ok() and self.cur.kind == "text":
            self.cur.text = t
            self.cur.update()

    def apply_font(self):
        if self._ok() and self.cur.kind == "text":
            self.cur.font_px = self.sfont.value()
            self.cur.update()

    def pick_color(self):
        if self.cur is None:
            return
        col = QColorDialog.getColor(self.cur.fill, self, "Renk seç")
        if col.isValid():
            self.cur.fill = col
            self.cur.update()
            self.sync_props()

    def delete_selected(self):
        for it in list(self.scene.selectedItems()):
            if isinstance(it, Layer):
                self.scene.removeItem(it)
        self.cur = None
        self.rebuild_list()
        self.sync_props()

    def duplicate(self):
        new = []
        for it in list(self.scene.selectedItems()):
            if not isinstance(it, Layer):
                continue
            n = self.new_layer(it.kind, it.pos() + QPointF(24, 24), it.w, it.h, False)
            n.fill, n.text, n.font_px, n.radius = QColor(it.fill), it.text, it.font_px, it.radius
            n.setOpacity(it.opacity())
            n.name = it.name + " kopya"
            new.append(n)
        if new:
            self.scene.clearSelection()
            for n in new:
                n.setSelected(True)
            self.rebuild_list()

    def reorder(self, d):
        items = [i for i in self.scene.selectedItems() if isinstance(i, Layer)]
        if not items:
            return
        zs = [i.zValue() for i in self.layer_items()]
        for it in items:
            if d > 0:
                self._z += 1
                it.setZValue(self._z)
            else:
                it.setZValue(min(zs) - 1)
        self.rebuild_list()

    def export_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "Dışa aktar", "tasarim.png", "PNG (*.png)")
        if not path:
            return
        self.scene.clearSelection()
        img = QImage(ART_W, ART_H, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.white)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.scene.render(p, QRectF(img.rect()), QRectF(0, 0, ART_W, ART_H))
        p.end()
        img.save(path)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
    win = MainWindow()
    win.show()
    if "--shot" in sys.argv:
        out = sys.argv[sys.argv.index("--shot") + 1]

        def shot():
            win.scene.clearSelection()
            lay = win.layer_items()
            lay[-2].setSelected(True)
            win.grab().save(out)
            app.quit()
        QTimer.singleShot(900, shot)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
