"""Tuval ogeleri: QvDoc katman sozlugune bagli Layer, sanat tahtasi ve gorunum (Canvas)."""
import os

from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import (QColor, QPainter, QPen, QBrush, QFont, QImage, QPainterPath,
                           QPainterPathStroker, QLinearGradient)
from PySide6.QtWidgets import QApplication, QGraphicsObject, QGraphicsItem, QGraphicsView, QFrame

import qv_engine as E
from qv_theme import ACCENT, FAMILY

HANDLES = {"tl": (0, 0), "t": (.5, 0), "tr": (1, 0), "r": (1, .5),
           "br": (1, 1), "b": (.5, 1), "bl": (0, 1), "l": (0, .5)}
ENGINE_HD = {"tl": "nw", "t": "n", "tr": "ne", "r": "e", "br": "se", "b": "s", "bl": "sw", "l": "w"}
CURSORS = {"tl": Qt.CursorShape.SizeFDiagCursor, "br": Qt.CursorShape.SizeFDiagCursor,
           "tr": Qt.CursorShape.SizeBDiagCursor, "bl": Qt.CursorShape.SizeBDiagCursor,
           "t": Qt.CursorShape.SizeVerCursor, "b": Qt.CursorShape.SizeVerCursor,
           "l": Qt.CursorShape.SizeHorCursor, "r": Qt.CursorShape.SizeHorCursor}


def pil_to_qimage(im):
    im = im.convert("RGBA")
    return QImage(im.tobytes("raw", "RGBA"), im.width, im.height, im.width * 4,
                  QImage.Format.Format_RGBA8888).copy()


class Layer(QGraphicsObject):
    geo_changed = Signal()
    PAD = 60
    _tcache = {}
    _icache = {}

    def __init__(self, win, d):
        super().__init__()
        self.win, self.d = win, d
        self._rs = None
        self._syncing = True
        self._dragging = False
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
                      QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
                      QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self._syncing = False
        self.sync_from_dict()

    # ---- geometri ----
    def box(self):
        d = self.d
        if d["type"] == "line":
            return (min(d["x"], d["x2"]), min(d["y"], d["y2"]), abs(d["x2"] - d["x"]), abs(d["y2"] - d["y"]))
        return d["x"], d["y"], d["w"], d["h"]

    @property
    def kind(self):
        return self.d["type"]

    def sync_from_dict(self):
        x, y, w, h = self.box()
        self._syncing = True
        self.prepareGeometryChange()
        self.setPos(x, y)
        self._syncing = False
        self.update()

    def set_geometry(self, x, y, w, h):
        d = self.d
        if d["type"] == "line":
            fx, fy = d["x2"] >= d["x"], d["y2"] >= d["y"]
            d["x"], d["x2"] = (x, x + w) if fx else (x + w, x)
            d["y"], d["y2"] = (y, y + h) if fy else (y + h, y)
        else:
            d["x"], d["y"], d["w"], d["h"] = x, y, max(float(w), 1.0), max(float(h), 1.0)
        self.sync_from_dict()
        self.geo_changed.emit()

    def _zoom(self):
        sc = self.scene()
        if sc and sc.views():
            return max(sc.views()[0].transform().m11(), 0.01)
        return 1.0

    def boundingRect(self):
        _, _, w, h = self.box()
        return QRectF(-self.PAD, -self.PAD, w + 2 * self.PAD, h + 2 * self.PAD)

    def shape(self):
        _, _, w, h = self.box()
        path = QPainterPath()
        if self.d["type"] == "line":
            d = self.d
            bx, by = self.box()[:2]
            lp = QPainterPath(QPointF(d["x"] - bx, d["y"] - by))
            lp.lineTo(QPointF(d["x2"] - bx, d["y2"] - by))
            st = QPainterPathStroker()
            st.setWidth(max(d["ow"], 10 / self._zoom()))
            path = st.createStroke(lp)
        else:
            path.addRect(QRectF(0, 0, w, h))
        if self.isSelected():
            s = 7 / self._zoom()
            for fx, fy in HANDLES.values():
                path.addRect(QRectF(fx * w - s, fy * h - s, 2 * s, 2 * s))
        return path

    def handle_at(self, pos):
        _, _, w, h = self.box()
        s = 7 / self._zoom()
        for k, (fx, fy) in HANDLES.items():
            if abs(pos.x() - fx * w) <= s and abs(pos.y() - fy * h) <= s:
                return k
        return None

    # ---- cizim ----
    def paint(self, p, opt, widget=None):
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        d, t = self.d, self.d["type"]
        bx, by, w, h = self.box()
        rect = QRectF(0, 0, w, h)
        if t in ("rect", "ellipse"):
            ow = d["ow"] if d["outline"] else 0
            if d["fill"] and d.get("fill2"):
                g = QLinearGradient(0, 0, 0, h)
                g.setColorAt(0, QColor(d["fill"]))
                g.setColorAt(1, QColor(d["fill2"]))
                p.setBrush(QBrush(g))
            else:
                p.setBrush(QColor(d["fill"]) if d["fill"] else Qt.BrushStyle.NoBrush)
            if ow > 0:
                pen = QPen(QColor(d["outline"]), ow)
                pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
                p.setPen(pen)
            else:
                p.setPen(Qt.PenStyle.NoPen)
            r = rect.adjusted(ow / 2, ow / 2, -ow / 2, -ow / 2)
            if t == "ellipse":
                p.drawEllipse(r)
            else:
                rad = min(d["rad"], w / 2, h / 2)
                p.drawRoundedRect(r, rad, rad)
        elif t == "line":
            pen = QPen(QColor(d["color"]), d["ow"])
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.drawLine(QPointF(d["x"] - bx, d["y"] - by), QPointF(d["x2"] - bx, d["y2"] - by))
        elif t == "image":
            self._paint_image(p, rect)
        elif t == "text":
            self._paint_text(p, opt, widget, rect)
        if self.isSelected():
            lod = opt.levelOfDetailFromTransform(p.worldTransform())
            p.setPen(QPen(QColor(ACCENT), 1.5 / lod))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(rect)
            p.setBrush(QColor("white"))
            p.setPen(QPen(QColor(ACCENT), 1.2 / lod))
            hs = 8 / lod
            for fx, fy in HANDLES.values():
                p.drawRect(QRectF(fx * w - hs / 2, fy * h - hs / 2, hs, hs))

    def _paint_text(self, p, opt, widget, rect):
        d = self.d
        if not d["text"]:
            return
        lod = opt.levelOfDetailFromTransform(p.worldTransform())
        dpr = p.device().devicePixelRatioF() if p.device() else 1.0
        ss = max(0.1, min(6.0, lod * dpr))
        while rect.width() * ss * rect.height() * ss > 9e6 and ss > 0.1:
            ss *= 0.8
        key = (d["text"], d["size"], d["color"], d["family"], d["bold"], d["italic"], d["align"],
               round(rect.width(), 1), round(rect.height(), 1), round(ss, 2))
        q = Layer._tcache.get(key)
        if q is None:
            from PIL import Image, ImageDraw
            W, H = max(1, int(rect.width() * ss)), max(1, int(rect.height() * ss))
            col = tuple(int(d["color"][i:i + 2], 16) for i in (1, 3, 5))
            im = Image.new("RGBA", (W, H), col + (0,))
            L = dict(d)
            L["x"], L["y"] = 0, 0
            try:
                E.qv_draw_text(ImageDraw.Draw(im), L, ss)
            except Exception:  # noqa: BLE001
                pass
            q = pil_to_qimage(im)
            if len(Layer._tcache) > 160:
                Layer._tcache.clear()
            Layer._tcache[key] = q
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.drawImage(rect, q)

    def _qimage(self):
        doc = self.win.doc
        key = (id(doc), self.d["asset"])
        q = Layer._icache.get(key)
        if q is None:
            pil = doc.asset_image(self.d["asset"])
            if pil is None:
                q = False
            else:
                if max(pil.size) > 3000:
                    pil = pil.copy()
                    pil.thumbnail((3000, 3000))
                q = pil_to_qimage(pil)
            if len(Layer._icache) > 16:
                Layer._icache.clear()
            Layer._icache[key] = q
        return q

    def _paint_image(self, p, rect):
        q = self._qimage()
        if not q:
            p.setPen(QPen(QColor("#9ca3af"), 1))
            p.setBrush(QColor("#d1d5db"))
            p.drawRect(rect)
            return
        p.save()
        p.setOpacity(p.opacity() * self.d["opacity"])
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.drawImage(rect, q)
        p.restore()

    # ---- olaylar ----
    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            if self._dragging and not self._syncing:
                return self.win.snap_pos(self, value)
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            if not self._syncing:
                p = self.pos()
                x0, y0 = self.box()[:2]
                dx, dy = p.x() - x0, p.y() - y0
                if dx or dy:
                    d = self.d
                    d["x"] += dx
                    d["y"] += dy
                    if d["type"] == "line":
                        d["x2"] += dx
                        d["y2"] += dy
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
            self._rs = (k, self.box(), self.d.get("size", 0))
            e.accept()
            return
        if e.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._rs:
            k, b0, size0 = self._rs
            sp = e.scenePos()
            mods = QApplication.keyboardModifiers()
            is_text = self.d["type"] == "text"
            # metinde köşeden çekince kutu ve yazı birlikte, orantılı büyür/küçülür
            keep = bool(mods & Qt.KeyboardModifier.ShiftModifier) or (is_text and len(k) == 2)
            x, y, w, h = E.qv_resize(b0, ENGINE_HD[k], sp.x(), sp.y(), keep=keep,
                                     center=bool(mods & Qt.KeyboardModifier.AltModifier))
            if is_text and size0 and b0[2] > 0 and b0[3] > 0:
                if len(k) == 2:
                    f = max(w / b0[2], h / b0[3])
                elif k in ("l", "r"):
                    f = w / b0[2]
                else:
                    f = h / b0[3]
                self.d["size"] = max(4.0, min(4000.0, size0 * f))
                self.win.sync_props()
            self.set_geometry(x, y, w, h)
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._rs:
            self._rs = None
            return
        self._dragging = False
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        if self.d["type"] == "text":
            self.win.edit_text_inline(self)
        super().mouseDoubleClickEvent(e)


class Artboard(QGraphicsObject):
    """Belgenin tuvali (arka plan / gradyan + golge)."""

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.setZValue(-1e6)

    def refresh(self):
        self.prepareGeometryChange()
        self.update()

    def boundingRect(self):
        return QRectF(-90, -90, self.win.doc.w + 180, self.win.doc.h + 190)

    def paint(self, p, opt, widget=None):
        doc = self.win.doc
        r = QRectF(0, 0, doc.w, doc.h)
        lod = opt.levelOfDetailFromTransform(p.worldTransform())
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(10):
            sp = (i + 1) * 3 / lod
            p.setBrush(QColor(0, 0, 0, 14))
            p.drawRoundedRect(r.adjusted(-sp, -sp + 8 / lod, sp, sp + 8 / lod), sp, sp)
        if doc.bg2:
            g = QLinearGradient(0, 0, 0, doc.h)
            g.setColorAt(0, QColor(doc.bg))
            g.setColorAt(1, QColor(doc.bg2))
            p.setBrush(QBrush(g))
        else:
            p.setBrush(QColor(doc.bg))
        p.drawRect(r)


class Canvas(QGraphicsView):
    zoom_changed = Signal(float)

    def __init__(self, scene, win):
        super().__init__(scene)
        self.win = win
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAcceptDrops(True)
        self._space = False
        self._pan = None
        self._creating = None
        self._origin = None
        self.guides = ([], [])

    def zoom(self):
        return self.transform().m11()

    def zoom_by(self, f, under_mouse=True):
        z = self.zoom()
        f = max(0.02, min(8.0, z * f)) / z
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse if under_mouse
                                     else QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.scale(f, f)
        self.zoom_changed.emit(self.zoom())

    def fit(self):
        d = self.win.doc
        self.fitInView(QRectF(0, 0, d.w, d.h).adjusted(-90, -90, 90, 90), Qt.AspectRatioMode.KeepAspectRatio)
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

    def drawForeground(self, p, rect):
        gx, gy = self.guides
        if not (gx or gy):
            return
        pen = QPen(QColor("#FF3B6B"), 1)
        pen.setCosmetic(True)
        p.setPen(pen)
        for x in gx:
            p.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
        for y in gy:
            p.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))

    def wheelEvent(self, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom_by(1.0015 ** e.angleDelta().y())
            return
        d = e.angleDelta()
        hb, vb = self.horizontalScrollBar(), self.verticalScrollBar()
        if e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            hb.setValue(hb.value() - d.y())
        else:
            vb.setValue(vb.value() - d.y())
            hb.setValue(hb.value() - d.x())

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Space and not e.isAutoRepeat():
            self._space = True
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
            return
        arrows = {Qt.Key.Key_Left: (-1, 0), Qt.Key.Key_Right: (1, 0), Qt.Key.Key_Up: (0, -1), Qt.Key.Key_Down: (0, 1)}
        if e.key() in arrows and self.scene().selectedItems():
            step = 10 if e.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
            dx, dy = arrows[e.key()]
            for it in self.scene().selectedItems():
                if isinstance(it, Layer):
                    x, y, w, h = it.box()
                    it.set_geometry(x + dx * step, y + dy * step, w, h)
            self.win.schedule_commit()
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
            self._creating = self.win.add_layer(self.win.tool, self._origin.x(), self._origin.y(), tiny=True)
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._pan is not None:
            dlt = e.position() - self._pan
            self._pan = e.position()
            hb, vb = self.horizontalScrollBar(), self.verticalScrollBar()
            hb.setValue(hb.value() - int(dlt.x()))
            vb.setValue(vb.value() - int(dlt.y()))
            return
        if self._creating:
            p = self.mapToScene(e.position().toPoint())
            o = self._origin
            it = self._creating
            if it.kind == "line":
                it.d["x2"], it.d["y2"] = p.x(), p.y()
                it.sync_from_dict()
                it.geo_changed.emit()
            else:
                it.set_geometry(min(o.x(), p.x()), min(o.y(), p.y()), abs(p.x() - o.x()), abs(p.y() - o.y()))
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._pan is not None:
            self._pan = None
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor if self._space else Qt.CursorShape.ArrowCursor)
            return
        if self._creating:
            it = self._creating
            self._creating = None
            x, y, w, h = it.box()
            if w < 8 and h < 8:
                dw, dh = {"text": (300, 80), "ellipse": (160, 160), "line": (240, 0)}.get(it.kind, (180, 130))
                it.set_geometry(x, y, dw, dh)
            self.win.set_tool("select")
            self.win.after_edit()
            return
        super().mouseReleaseEvent(e)
        self.guides = ([], [])
        self.viewport().update()
        self.win.after_edit()

    # ---- gorsel surukle-birak ----
    def _ok_drop(self, e):
        md = e.mimeData()
        if md.hasImage():
            return True
        return any(u.isLocalFile() and os.path.splitext(u.toLocalFile())[1].lower() in E.QV_IMG_EXTS
                   for u in md.urls())

    def dragEnterEvent(self, e):
        if self._ok_drop(e):
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if self._ok_drop(e):
            e.acceptProposedAction()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e):
        if not self._ok_drop(e):
            super().dropEvent(e)
            return
        pos = self.mapToScene(e.position().toPoint())
        paths = [u.toLocalFile() for u in e.mimeData().urls()
                 if u.isLocalFile() and os.path.splitext(u.toLocalFile())[1].lower() in E.QV_IMG_EXTS]
        if paths:
            self.win.add_images(paths, pos)
        elif e.mimeData().hasImage():
            self.win.paste_image()
        e.acceptProposedAction()
