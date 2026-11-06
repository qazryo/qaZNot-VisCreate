"""Panel islemleri: ozellik uygulama, hizalama, yazi tipi, yuklemeler, panodan yapistirma, disa aktarma."""
import os
import subprocess

import json

from PySide6.QtCore import Qt, QBuffer, QIODevice, QPointF, QRect, QMimeData
from PySide6.QtGui import QColor, QIcon, QPixmap, QFont
from PySide6.QtWidgets import (QApplication, QColorDialog, QFileDialog, QListWidgetItem, QMenu, QMessageBox,
                               QPlainTextEdit)

import qv_engine as E
from qv_dialogs import BG
from qv_items import Layer
from qv_widgets import animate_width


LAYER_MIME = "application/x-qanvas-layers"


class InlineEdit(QPlainTextEdit):
    """Tuval üzerinde metin katmanını doğrudan düzenleme kutusu. Esc: vazgeç, Ctrl+Enter / odak kaybı: uygula."""

    def __init__(self, parent, on_done):
        super().__init__(parent)
        self.on_done, self._closed = on_done, False

    def _finish(self, apply):
        if not self._closed:
            self._closed = True
            self.on_done(apply, self.toPlainText())

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self._finish(False)
            return
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._finish(True)
            return
        super().keyPressEvent(e)

    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        self._finish(True)


def _fill_key(layer):
    return "fill" if layer.kind in ("rect", "ellipse") else "color"


class ActionsMixin:
    def _ok(self):
        return self.cur is not None and not self._busy

    def touch(self):
        if self.cur is not None:
            self.cur.update()
        self.schedule_commit()

    # ---- geometri / genel ----
    def apply_geo(self):
        if self._ok():
            self.cur.set_geometry(self.sx.value(), self.sy.value(), self.sw.value(), self.sh.value())
            self.schedule_commit()

    def apply_radius(self):
        if self._ok() and self.cur.kind == "rect":
            self.cur.d["rad"] = float(self.sr.value())
            self.touch()

    def apply_opacity(self):
        if self._ok() and self.cur.kind == "image":
            self.cur.d["opacity"] = self.so.value() / 100
            self.touch()

    def align(self, mode):
        sel = self.selected_layers()
        if not sel:
            return
        boxes = [(x, y, x + w, y + h) for x, y, w, h in (it.box() for it in sel)]
        union = E.qv_union(boxes)
        ref = (0, 0, self.doc.w, self.doc.h) if len(sel) == 1 else union
        dx, dy = E.qv_align_delta(union, ref, mode)
        for it in sel:
            x, y, w, h = it.box()
            it.set_geometry(x + dx, y + dy, w, h)
        self.after_edit()

    def distribute(self, axis):
        sel = self.selected_layers()
        if len(sel) < 3:
            self.toast("Eşit dağıtmak için en az 3 nesne seç", error=True)
            return
        i = 0 if axis == "h" else 1
        items = sorted(sel, key=lambda it: it.box()[i])
        first, last = items[0].box(), items[-1].box()
        total = (last[i] + last[i + 2]) - first[i]
        gap = (total - sum(it.box()[i + 2] for it in items)) / (len(items) - 1)
        pos = first[i]
        for it in items:
            x, y, w, h = it.box()
            it.set_geometry(pos, y, w, h) if axis == "h" else it.set_geometry(x, pos, w, h)
            pos += (w if axis == "h" else h) + gap
        self.after_edit()

    # ---- kopyala / kes / yapıştır (katmanlar) ----
    def copy_layers(self):
        sel = self.selected_layers()
        if not sel:
            return False
        layers = [json.loads(json.dumps(it.d)) for it in sel]
        assets = {L["asset"]: self.doc.assets[L["asset"]] for L in layers
                  if L["type"] == "image" and L["asset"] in self.doc.assets}
        md = QMimeData()
        md.setData(LAYER_MIME, json.dumps({"layers": layers, "assets": assets}).encode("utf-8"))
        md.setText(f"{len(layers)} qAnvas katmanı")
        QApplication.clipboard().setMimeData(md)
        self._paste_n = 0
        return True

    def cut_layers(self):
        if self.copy_layers():
            self.delete_selected()

    def paste_layers(self):
        md = QApplication.clipboard().mimeData()
        if not md.hasFormat(LAYER_MIME):
            return False
        try:
            data = json.loads(bytes(md.data(LAYER_MIME)).decode("utf-8"))
        except ValueError:
            return False
        self._paste_n = getattr(self, "_paste_n", 0) + 1
        off = 24 * self._paste_n
        for aid, a in (data.get("assets") or {}).items():
            if aid not in self.doc.assets and isinstance(a, dict) and isinstance(a.get("data"), str):
                self.doc.assets[aid] = dict(name=str(a.get("name", ""))[:80], data=a["data"],
                                            w=int(a.get("w", 0) or 0), h=int(a.get("h", 0) or 0))
        new = []
        for L in data.get("layers", []):
            L = dict(L)
            L["x"] = L.get("x", 0) + off
            L["y"] = L.get("y", 0) + off
            if L.get("type") == "line":
                L["x2"] = L.get("x2", 0) + off
                L["y2"] = L.get("y2", 0) + off
            cl = E.qv_clean_layer(L)
            if cl is None:
                continue
            self.doc.layers.append(cl)
            new.append(len(self.doc.layers) - 1)
        if new:
            self.rebuild(new)
            self.after_edit()
        return bool(new)

    # ---- tuval üzerinde metin düzenleme ----
    def edit_text_inline(self, it):
        old = getattr(self, "_inline", None)
        if old is not None:
            old._finish(True)
        d = it.d
        z = self.view.zoom()
        x, y, w, h = it.box()
        tl = self.view.mapFromScene(QPointF(x, y))
        br = self.view.mapFromScene(QPointF(x + w, y + h))

        def done(apply, text):
            self._inline = None
            if apply and text != d["text"]:
                d["text"] = text[:5000]
                it.update()
                self.after_edit()
            ed.deleteLater()
            self.view.setFocus()
        ed = InlineEdit(self.view.viewport(), done)
        f = QFont(d["family"])
        f.setPixelSize(max(6, int(d["size"] * z)))
        f.setBold(d["bold"])
        f.setItalic(d["italic"])
        ed.setFont(f)
        ed.setStyleSheet(f"QPlainTextEdit {{ color: {d['color']}; background: {self.doc.bg}; "
                         f"border: 1px solid #0D99FF; padding: 0; }}")
        ed.setPlainText(d["text"])
        ed.setGeometry(QRect(tl, br))
        al = {"left": Qt.AlignmentFlag.AlignLeft, "center": Qt.AlignmentFlag.AlignHCenter,
              "right": Qt.AlignmentFlag.AlignRight}[d["align"]]
        opt = ed.document().defaultTextOption()
        opt.setAlignment(al)
        ed.document().setDefaultTextOption(opt)
        ed.show()
        ed.setFocus()
        ed.selectAll()
        self._inline = ed

    # ---- renkler ----
    def _pick(self, current):
        col = QColorDialog.getColor(QColor(current or "#ffffff"), self, "Renk seç")
        return col.name() if col.isValid() else None

    def pick_fill(self):
        if self.cur is None:
            return
        k = _fill_key(self.cur)
        c = self._pick(self.cur.d.get(k))
        if c:
            self.cur.d[k] = c
            self.cur.update()
            self.sync_props()
            self.after_edit()

    def clear_fill(self):
        if self.cur is not None and self.cur.kind in ("rect", "ellipse"):
            self.cur.d["fill"] = None
            self.cur.update()
            self.sync_props()
            self.after_edit()

    def pick_fill2(self):
        if self.cur is None or self.cur.kind not in ("rect", "ellipse"):
            return
        c = self._pick(self.cur.d.get("fill2") or self.cur.d.get("fill"))
        if c:
            if not self.cur.d.get("fill"):
                self.cur.d["fill"] = "#7b61ff"
            self.cur.d["fill2"] = c
            self.cur.update()
            self.sync_props()
            self.after_edit()

    def clear_fill2(self):
        if self.cur is not None and self.cur.kind in ("rect", "ellipse"):
            self.cur.d["fill2"] = None
            self.cur.update()
            self.sync_props()
            self.after_edit()

    def pick_stroke(self):
        if self.cur is None or self.cur.kind not in ("rect", "ellipse"):
            return
        c = self._pick(self.cur.d.get("outline"))
        if c:
            self.cur.d["outline"] = c
            if self.cur.d["ow"] <= 0:
                self.cur.d["ow"] = 4.0
            self.cur.update()
            self.sync_props()
            self.after_edit()

    def clear_stroke(self):
        if self.cur is not None and self.cur.kind in ("rect", "ellipse"):
            self.cur.d["outline"] = None
            self.cur.update()
            self.sync_props()
            self.after_edit()

    def apply_ow(self):
        if self._ok() and self.cur.kind in ("rect", "ellipse", "line"):
            self.cur.d["ow"] = float(self.s_ow.value())
            if self.cur.kind != "line" and self.cur.d["ow"] > 0 and not self.cur.d["outline"]:
                self.cur.d["outline"] = "#000000"
                self.sync_props()
            self.touch()

    def pick_bg(self):
        c = self._pick(self.doc.bg)
        if c:
            self.doc.bg = c
            self.artboard.refresh()
            self.sync_props()
            self.after_edit()

    def pick_bg2(self):
        c = self._pick(self.doc.bg2 or self.doc.bg)
        if c:
            self.doc.bg2 = c
            self.artboard.refresh()
            self.sync_props()
            self.after_edit()

    def clear_bg2(self):
        self.doc.bg2 = None
        self.artboard.refresh()
        self.sync_props()
        self.after_edit()

    # ---- metin ----
    def focus_text_edit(self):
        self.text_edit.setFocus()
        self.text_edit.selectAll()

    def apply_text(self):
        if self._ok() and self.cur.kind == "text":
            self.cur.d["text"] = self.text_edit.toPlainText()[:5000]
            self.touch()
            self.refresh_list_names()

    def apply_size(self):
        if self._ok() and self.cur.kind == "text":
            self.cur.d["size"] = float(self.s_size.value())
            self.touch()

    def apply_bold(self):
        if self._ok() and self.cur.kind == "text":
            self.cur.d["bold"] = self.b_bold.isChecked()
            self.touch()

    def apply_italic(self):
        if self._ok() and self.cur.kind == "text":
            self.cur.d["italic"] = self.b_italic.isChecked()
            self.touch()

    def apply_align(self, a):
        if self._ok() and self.cur.kind == "text":
            self.cur.d["align"] = a
            self.touch()

    def populate_fonts(self):
        cb = self.cb_font
        cb.blockSignals(True)
        cb.clear()
        fams = list(E.qv_font_families())
        allowed = self.acct.ed.get("fonts")
        if allowed:
            low = {a.lower() for a in allowed}
            fams = [f for f in fams if f.lower() in low] or ["Segoe UI"]
        for f in fams:
            cb.addItem(f, "local")
        if self.acct.full and E.QV_HAVE_PIL:
            cb.insertSeparator(cb.count())
            have = {f.lower() for f in fams}
            for g in E.QV_GFONTS:
                if g.lower() not in have:
                    cb.addItem(g + "  (indir)", "web:" + g)
        cb.blockSignals(False)
        self.sync_props()

    def pick_font(self, i):
        if self.cur is None or self.cur.kind != "text":
            return
        data = self.cb_font.itemData(i)
        name = self.cb_font.itemText(i)
        if isinstance(data, str) and data.startswith("web:"):
            name = data[4:]
            layer = self.cur
            self.toast(f"{name} indiriliyor…")

            def done(res, err):
                if err:
                    self.toast(f"İndirilemedi: {err}", error=True)
                    return
                layer.d["family"] = res[0] if isinstance(res, tuple) else name
                Layer._tcache.clear()
                layer.update()
                self.populate_fonts()
                self.toast(f"{name} eklendi")
                self.after_edit()
            BG(lambda: E.qv_gfont_install(name), done)
            return
        self.cur.d["family"] = name
        Layer._tcache.clear()
        self.touch()

    # ---- yuklemeler ----
    def toggle_uploads(self):
        show = self.btn_uploads.isChecked()
        if show:
            self.flyout.setMaximumWidth(0)
            self.flyout.show()
            self.refresh_uploads()
            animate_width(self.flyout, 270, 280)
        else:
            animate_width(self.flyout, 0, 220)

    def refresh_uploads(self):
        self.up_list.clear()
        for e in E.qv_lib_list():
            it = QListWidgetItem(QIcon(QPixmap(E.qv_lib_thumb(e["id"]))), e["name"][:14])
            it.setData(Qt.ItemDataRole.UserRole, e)
            it.setToolTip(f"{e['name']}  {e['w']}×{e['h']}")
            self.up_list.addItem(it)

    def upload_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Görsel yükle", "",
                                                "Görseller (" + " ".join(E.QV_IMG_TYPES) + ");;Tüm dosyalar (*)")
        if paths:
            self.add_images(paths)

    def add_images(self, paths, pos=None):
        added = 0
        for p in paths:
            try:
                e = E.qv_lib_add(p, os.path.splitext(os.path.basename(p))[0])
                self.add_image_from_lib(e, pos)
                added += 1
            except (ValueError, OSError) as ex:
                self.toast(str(ex), error=True)
        if added and self.flyout.isVisible():
            self.refresh_uploads()

    def add_upload_item(self, it):
        self.add_image_from_lib(it.data(Qt.ItemDataRole.UserRole))

    def add_image_from_lib(self, e, center=None):
        with open(E.qv_lib_path(e["id"], e["ext"]), "rb") as f:
            data = f.read()
        self.doc.add_asset(e["id"], data, e["name"], e["w"], e["h"])
        sc = min(1.0, 0.6 * self.doc.w / e["w"], 0.6 * self.doc.h / e["h"])
        w, h = e["w"] * sc, e["h"] * sc
        c = center or QPointF(self.doc.w / 2, self.doc.h / 2)
        self.add_layer("image", c.x() - w / 2, c.y() - h / 2, w=w, h=h, asset=e["id"], opacity=1.0)
        self.after_edit()

    def paste_image(self):
        cb = QApplication.clipboard()
        md = cb.mimeData()
        if md.hasUrls():
            paths = [u.toLocalFile() for u in md.urls() if u.isLocalFile()
                     and os.path.splitext(u.toLocalFile())[1].lower() in E.QV_IMG_EXTS]
            if paths:
                self.add_images(paths)
                return
        img = cb.image()
        if img.isNull():
            self.toast("Panoda görsel yok", error=True)
            return
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        img.save(buf, "PNG")
        try:
            e = E.qv_lib_add(bytes(buf.data()), "Panodan görsel")
            self.add_image_from_lib(e)
            if self.flyout.isVisible():
                self.refresh_uploads()
        except (ValueError, OSError) as ex:
            self.toast(str(ex), error=True)

    def upload_menu(self, pos):
        it = self.up_list.itemAt(pos)
        if not it:
            return
        m = QMenu(self)
        a1 = m.addAction("Tuvale ekle")
        a2 = m.addAction("Kitaplıktan sil")
        r = m.exec(self.up_list.mapToGlobal(pos))
        if r is a1:
            self.add_upload_item(it)
        elif r is a2:
            E.qv_lib_remove(it.data(Qt.ItemDataRole.UserRole)["id"])
            self.refresh_uploads()

    def list_menu(self, pos):
        m = QMenu(self)
        acts = {}
        for key, txt in (("front", "En öne getir"), ("up", "Bir öne"), ("down", "Bir arkaya"),
                         ("back", "En arkaya gönder"), ("dup", "Çoğalt"), ("del", "Sil")):
            acts[m.addAction(txt)] = key
        r = m.exec(self.layers.mapToGlobal(pos))
        k = acts.get(r)
        if k == "dup":
            self.duplicate()
        elif k == "del":
            self.delete_selected()
        elif k:
            self.reorder(k)

    # ---- disa aktarma (fotograf) ----
    def export_image(self):
        base = os.path.splitext(self.path)[0] if self.path else os.path.join(
            os.path.expanduser("~"), "Pictures", "".join(c for c in self.doc.name if c.isalnum() or c in " -_") or "tasarim")
        path, flt = QFileDialog.getSaveFileName(self, "Fotoğraf olarak dışa aktar", base + ".png",
                                                "PNG görsel (*.png);;JPEG görsel (*.jpg);;PDF belge (*.pdf)")
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        if ext not in (".png", ".jpg", ".jpeg", ".pdf"):
            path += ".jpg" if "jpg" in flt.lower() else ".pdf" if "pdf" in flt.lower() else ".png"
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.doc.export(path)
        except Exception as ex:  # noqa: BLE001
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "qAnvas", f"Dışa aktarılamadı: {ex}")
            return
        QApplication.restoreOverrideCursor()
        self.last_export = path
        self.toast(f"Dışa aktarıldı: {os.path.basename(path)}")
        if not getattr(self, "quiet", False):
            box = QMessageBox(self)
            box.setWindowTitle("qAnvas")
            box.setText(f"Fotoğraf kaydedildi ({self.doc.w}×{self.doc.h} px):\n{path}")
            b_open = box.addButton("Klasörde göster", QMessageBox.ButtonRole.ActionRole)
            box.addButton("Tamam", QMessageBox.ButtonRole.AcceptRole)
            box.exec()
            if box.clickedButton() is b_open:
                try:
                    subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
                except OSError:
                    pass
