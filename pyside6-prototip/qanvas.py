"""qAnvas - PySide6 surumu (Figma tarzi arayuz + qAnvas motoru + lisans/Google girisi)."""
import json
import os
import subprocess
import sys

if "--shot" in sys.argv:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

from PySide6.QtCore import Qt, QRectF, QPointF, QTimer
from PySide6.QtGui import QIcon, QShortcut, QKeySequence
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGraphicsScene,
                               QListWidgetItem, QFileDialog, QMessageBox, QInputDialog, QDialog)

import qv_engine as E
from qv_theme import QSS, make_icon
from qv_items import Layer, Artboard, Canvas
from qv_panels import PanelsMixin
from qv_actions import ActionsMixin, LAYER_MIME
from qv_dialogs import NewDocDialog, BG
from qv_login import Account, AccountDialog
from qv_widgets import fade_in, window_fade_in

LABELS = {"rect": "Dikdörtgen", "ellipse": "Elips", "line": "Çizgi", "text": "Metin", "image": "Görsel"}
DEFAULTS = {
    "rect": dict(w=180, h=130, fill="#7b61ff", outline=None, ow=0, rad=0),
    "ellipse": dict(w=160, h=160, fill="#ff4d8d", outline=None, ow=0, rad=0),
    "text": dict(w=300, h=80, text="Metin", size=48, color="#1e1e1e", family="Segoe UI", bold=False,
                 italic=False, align="left"),
    "image": dict(w=300, h=300, asset="", opacity=1.0),
}


class MainWindow(QMainWindow, PanelsMixin, ActionsMixin):
    def __init__(self, acct, doc=None):
        super().__init__()
        self.setStyleSheet(QSS)
        self.acct = acct
        self.doc = doc or E.qv_new_preset(acct.ed, "logo")
        self.path = None
        self.dirty = False
        self.tool = "select"
        self.cur = None
        self.items = []
        self._busy = False
        self._lock = False
        self.quiet = False
        self.last_export = None
        icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "icon.png")
        if os.path.exists(icon):
            self.setWindowIcon(QIcon(icon))
        self.resize(1440, 880)

        self.scene = QGraphicsScene()
        self.artboard = Artboard(self)
        self.scene.addItem(self.artboard)
        self.view = Canvas(self.scene, self)

        self._ct = QTimer(self)
        self._ct.setSingleShot(True)
        self._ct.timeout.connect(self.commit)
        self._tt = QTimer(self)
        self._tt.setSingleShot(True)
        self._tt.timeout.connect(lambda: self.toast_lbl.setText(""))

        root = QWidget()
        root.setObjectName("root")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_topbar())
        body = QHBoxLayout()
        body.setSpacing(0)
        body.addWidget(self._build_toolbar())
        self.flyout = self._build_flyout()
        body.addWidget(self.flyout)
        body.addWidget(self.view, 1)
        body.addWidget(self._build_side())
        outer.addLayout(body, 1)
        self.setCentralWidget(root)

        self.scene.selectionChanged.connect(self.on_selection)
        self.view.zoom_changed.connect(lambda z: self.zoom_lbl.setText(f"{round(z * 100)}%"))
        self._shortcuts()
        self.refresh_account()
        self.load_doc(self.doc, None)
        BG(E.qv_scan_fonts, lambda r, e: self.populate_fonts())

    # ---------------- kisayollar ----------------
    def _shortcuts(self):
        def sc(keys, fn):
            QShortcut(QKeySequence(keys), self).activated.connect(fn)
        for k, t in (("V", "select"), ("R", "rect"), ("O", "ellipse"), ("L", "line"), ("T", "text")):
            sc(k, lambda t=t: self.set_tool(t))
        sc("I", lambda: (self.btn_uploads.setChecked(not self.btn_uploads.isChecked()), self.toggle_uploads()))
        sc("Delete", self.delete_selected)
        sc("Backspace", self.delete_selected)
        sc("Ctrl+D", self.duplicate)
        sc("Ctrl+]", lambda: self.reorder("up"))
        sc("Ctrl+[", lambda: self.reorder("down"))
        sc("Ctrl+Shift+]", lambda: self.reorder("front"))
        sc("Ctrl+Shift+[", lambda: self.reorder("back"))
        sc("Ctrl+0", lambda: self.view.fit())
        sc("Ctrl+=", lambda: self.view.zoom_by(1.25, False))
        sc("Ctrl+-", lambda: self.view.zoom_by(1 / 1.25, False))
        sc("Ctrl+Z", self.undo)
        sc("Ctrl+Y", self.redo)
        sc("Ctrl+Shift+Z", self.redo)
        sc("Ctrl+S", lambda: self.save())
        sc("Ctrl+Shift+S", lambda: self.save(True))
        sc("Ctrl+O", self.open_file)
        sc("Ctrl+N", self.new_doc_dialog)
        sc("Ctrl+E", self.export_image)
        sc("Ctrl+C", self.copy_layers)
        sc("Ctrl+X", self.cut_layers)
        sc("Ctrl+V", self.paste_if_image)
        sc("Ctrl+Shift+V", self.paste_image)
        sc("Escape", lambda: (self.set_tool("select"), self.scene.clearSelection()))

    def paste_if_image(self):
        md = QApplication.clipboard().mimeData()
        if md.hasFormat(LAYER_MIME):
            self.paste_layers()
        elif md.hasImage() or md.hasUrls():
            self.paste_image()

    # ---------------- belge ----------------
    def load_doc(self, doc, path):
        self.doc, self.path = doc, path
        Layer._icache.clear()
        Layer._tcache.clear()
        self.scene.setSceneRect(QRectF(-3000 - doc.w, -3000 - doc.h, doc.w * 3 + 6000, doc.h * 3 + 6000))
        self.artboard.refresh()
        self.rebuild([])
        self.reset_history()
        QTimer.singleShot(0, self.view.fit)

    def rebuild(self, sel=()):
        self._lock = True
        for it in self.items:
            self.scene.removeItem(it)
        self.items = []
        for i, d in enumerate(self.doc.layers):
            it = Layer(self, d)
            it.setZValue(i)
            self.scene.addItem(it)
            it.geo_changed.connect(lambda it=it: self.sync_props() if it is self.cur else None)
            self.items.append(it)
        for i in sel:
            if i < len(self.items):
                self.items[i].setSelected(True)
        self._lock = False
        self.rebuild_list()
        self.on_selection()

    def add_layer(self, kind, x, y, tiny=False, select=True, **kw):
        if kind == "line":
            props = dict(x2=x + 240, y2=y, color="#1e1e1e", ow=4)
            if tiny:
                props["x2"], props["y2"] = x, y
        else:
            props = dict(DEFAULTS[kind])
            if tiny:
                props["w"] = props["h"] = 1
        props.update(kw)
        i = self.doc.add(type=kind, x=x, y=y, **props)
        it = Layer(self, self.doc.layers[i])
        it.setZValue(i)
        self.scene.addItem(it)
        it.geo_changed.connect(lambda it=it: self.sync_props() if it is self.cur else None)
        self.items.append(it)
        if select:
            self.scene.clearSelection()
            it.setSelected(True)
        self.rebuild_list()
        self.schedule_commit()
        return it

    def delete_selected(self):
        idx = {i for i, it in enumerate(self.items) if it.isSelected()}
        if not idx:
            return
        self.doc.layers[:] = [d for i, d in enumerate(self.doc.layers) if i not in idx]
        self.rebuild([])
        self.after_edit()

    def duplicate(self):
        import copy
        idx = [i for i, it in enumerate(self.items) if it.isSelected()]
        new = []
        for i in idx:
            d = copy.deepcopy(self.doc.layers[i])
            d["x"] += 24
            d["y"] += 24
            if d["type"] == "line":
                d["x2"] += 24
                d["y2"] += 24
            self.doc.layers.append(d)
            new.append(len(self.doc.layers) - 1)
        if new:
            self.rebuild(new)
            self.after_edit()

    def reorder(self, mode):
        idx = [i for i, it in enumerate(self.items) if it.isSelected()]
        if not idx:
            return
        layers, sel = E.qv_reorder(self.doc.layers, idx, mode)
        self.doc.layers[:] = layers
        self.rebuild(sel)
        self.after_edit()

    def set_tool(self, key):
        self.tool = key
        self.tool_btns[key].setChecked(True)
        self.view.viewport().setCursor(Qt.CursorShape.ArrowCursor if key == "select" else Qt.CursorShape.CrossCursor)

    def snap_pos(self, item, newpos):
        if QApplication.keyboardModifiers() & Qt.KeyboardModifier.AltModifier or len(self.scene.selectedItems()) != 1:
            self.view.guides = ([], [])
            return newpos
        x, y, w, h = item.box()
        tx = [0, self.doc.w / 2, self.doc.w]
        ty = [0, self.doc.h / 2, self.doc.h]
        for o in self.items:
            if o is not item:
                ox, oy, ow, oh = o.box()
                tx += [ox, ox + ow / 2, ox + ow]
                ty += [oy, oy + oh / 2, oy + oh]
        thr = 6 / max(self.view.zoom(), 0.01)
        dx, dy, gx, gy = E.qv_snap_move((x, y, x + w, y + h), newpos.x() - x, newpos.y() - y, tx, ty, thr)
        self.view.guides = (gx, gy)
        self.view.viewport().update()
        return QPointF(x + dx, y + dy)

    # ---------------- gecmis (geri al / yinele) ----------------
    def snapshot(self):
        return json.dumps([self.doc.layers, self.doc.bg, self.doc.bg2], sort_keys=True)

    def sel_indices(self):
        return [i for i, it in enumerate(self.items) if it.isSelected()]

    def reset_history(self):
        self.hist, self.hist_sel, self.hi, self.dirty = [self.snapshot()], [[]], 0, False
        self.update_title()

    def schedule_commit(self):
        self._ct.start(350)

    def commit(self):
        s = self.snapshot()
        if s != self.hist[self.hi]:
            del self.hist[self.hi + 1:]
            del self.hist_sel[self.hi + 1:]
            self.hist.append(s)
            self.hist_sel.append(self.sel_indices())
            self.hi += 1
            if len(self.hist) > 120:
                self.hist.pop(0)
                self.hist_sel.pop(0)
                self.hi -= 1
            self.dirty = True
        self.update_title()

    def after_edit(self):
        self._ct.stop()
        self.commit()
        self.sync_props()
        self.refresh_list_names()

    def _restore(self, s, sel):
        layers, bg, bg2 = json.loads(s)
        self.doc.layers[:] = layers
        self.doc.bg, self.doc.bg2 = bg, bg2
        self.artboard.refresh()
        self.rebuild(sel)
        self.dirty = True
        self.update_title()

    def undo(self):
        self._ct.stop()
        self.commit()
        if self.hi > 0:
            sel = self.sel_indices()
            self.hi -= 1
            self._restore(self.hist[self.hi], sel)

    def redo(self):
        if self.hi < len(self.hist) - 1:
            self.hi += 1
            self._restore(self.hist[self.hi], self.hist_sel[self.hi])

    def update_title(self):
        self.setWindowTitle(f"{self.doc.name}{' *' if self.dirty else ''} - qAnvas")
        self.title_btn.setText(self.doc.name + (" •" if self.dirty else ""))
        self.btn_undo.setEnabled(self.hi > 0)
        self.btn_redo.setEnabled(self.hi < len(self.hist) - 1)

    # ---------------- secim / paneller ----------------
    def selected_layers(self):
        return [it for it in self.items if it.isSelected()]

    def layer_name(self, i):
        d = self.doc.layers[i]
        if d["type"] == "text" and d["text"].strip():
            return d["text"].strip().split("\n")[0][:22]
        return f"{LABELS[d['type']]} {i + 1}"

    def rebuild_list(self):
        self._lock = True
        self.layers.clear()
        for i in range(len(self.items) - 1, -1, -1):
            li = QListWidgetItem(make_icon(self.items[i].kind), self.layer_name(i))
            li.setData(Qt.ItemDataRole.UserRole, i)
            self.layers.addItem(li)
            li.setSelected(self.items[i].isSelected())
        self._lock = False

    def refresh_list_names(self):
        for k in range(self.layers.count()):
            li = self.layers.item(k)
            li.setText(self.layer_name(li.data(Qt.ItemDataRole.UserRole)))

    def on_list_selection(self):
        if self._lock:
            return
        self._lock = True
        self.scene.clearSelection()
        for li in self.layers.selectedItems():
            self.items[li.data(Qt.ItemDataRole.UserRole)].setSelected(True)
        self._lock = False
        self.on_selection(from_list=True)

    def on_selection(self, from_list=False):
        if self._lock:
            return
        try:
            sel = self.selected_layers()
        except RuntimeError:
            return
        self.cur = sel[0] if len(sel) == 1 else None
        if not from_list:
            self._lock = True
            for k in range(self.layers.count()):
                li = self.layers.item(k)
                li.setSelected(self.items[li.data(Qt.ItemDataRole.UserRole)].isSelected())
            self._lock = False
        self.sync_props()

    @staticmethod
    def _swatch(sw, hx, col):
        if col:
            sw.setStyleSheet(f"background: {col};")
            hx.setText(col.upper())
        else:
            sw.setStyleSheet("background: transparent; border: 1px dashed #777;")
            hx.setText("Yok")

    def sync_props(self):
        sel = self.selected_layers()
        c = self.cur
        t = c.kind if c else None
        self._busy = True
        for w in (self.sx, self.sy, self.sw, self.sh):
            w.setEnabled(c is not None)
        self.sr.setEnabled(t == "rect")
        self.so.setEnabled(t == "image")
        self.g_align.setEnabled(bool(sel))
        self.g_fill.setVisible(t in ("rect", "ellipse", "text", "line"))
        self.row_fill2.setVisible(t in ("rect", "ellipse"))
        self.b_disth.setEnabled(len(sel) >= 3)
        self.b_distv.setEnabled(len(sel) >= 3)
        self.g_stroke.setVisible(t in ("rect", "ellipse", "line"))
        self.g_text.setVisible(t == "text")
        self.g_canvas.setVisible(not sel)
        if c is not None:
            d = c.d
            x, y, w, h = c.box()
            self.sx.setValue(round(x))
            self.sy.setValue(round(y))
            self.sw.setValue(round(w))
            self.sh.setValue(round(h))
            self.sr.setValue(round(d.get("rad", 0)))
            self.so.setValue(round(d.get("opacity", 1.0) * 100))
            if t in ("rect", "ellipse", "text", "line"):
                key = "fill" if t in ("rect", "ellipse") else "color"
                self.lbl_fill.setText("DOLGU" if key == "fill" else "RENK")
                self.clr_fill.setVisible(key == "fill")
                self._swatch(self.sw_fill, self.hex_fill, d.get(key))
                self._swatch(self.sw_fill2, self.hex_fill2, d.get("fill2"))
                self.hex_fill2.setText(d["fill2"].upper() if d.get("fill2") else "Gradyan yok")
            if t in ("rect", "ellipse", "line"):
                self.lbl_stroke.setText("ÇİZGİ KALINLIĞI" if t == "line" else "KENARLIK")
                self.row_str_color.setVisible(t != "line")
                self._swatch(self.sw_str, self.hex_str, d.get("outline"))
                self.s_ow.setValue(round(d["ow"]))
            if t == "text":
                if self.text_edit.toPlainText() != d["text"]:
                    self.text_edit.setPlainText(d["text"])
                self.s_size.setValue(round(d["size"]))
                self.b_bold.setChecked(d["bold"])
                self.b_italic.setChecked(d["italic"])
                self.al_btns[d["align"]].setChecked(True)
                i = self.cb_font.findText(d["family"], Qt.MatchFlag.MatchFixedString)
                if i < 0:
                    self.cb_font.insertItem(0, d["family"], "local")
                    i = 0
                self.cb_font.setCurrentIndex(i)
        self.lbl_size.setText(f"{self.doc.w} × {self.doc.h} px")
        self._swatch(self.sw_bg, self.hex_bg, self.doc.bg)
        self._swatch(self.sw_bg2, self.hex_bg2, self.doc.bg2)
        self.hex_bg2.setText(self.doc.bg2.upper() if self.doc.bg2 else "Gradyan yok")
        self._busy = False

    def toast(self, msg, error=False):
        self.toast_lbl.setStyleSheet("color: #FF6B5E;" if error else "color: #32D74B;")
        self.toast_lbl.setText(msg[:90])
        fade_in(self.toast_lbl, 260)
        self._tt.start(5000)

    # ---------------- dosya ----------------
    def confirm_discard(self):
        if not self.dirty:
            return True
        r = QMessageBox.question(self, "qAnvas", f"'{self.doc.name}' kaydedilsin mi?",
                                 QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                 QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Save:
            return self.save()
        return r == QMessageBox.StandardButton.Discard

    def new_doc_dialog(self):
        if not self.confirm_discard():
            return
        dlg = NewDocDialog(self.acct, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.doc:
            self.load_doc(dlg.doc, dlg.path)

    def open_file(self, *_):
        if not self.confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, "qAnvas dosyası aç", "", "qAnvas (*.qanvas);;Tüm dosyalar (*)")
        if path:
            self._open_path(path)

    def open_path(self, path):
        """Dışarıdan (qaZNot menüsü, çift tık) gelen dosyayı açar."""
        if self.confirm_discard():
            self._open_path(path)

    def bring_to_front(self):
        self.setWindowState((self.windowState() & ~Qt.WindowState.WindowMinimized) | Qt.WindowState.WindowActive)
        self.show()
        self.raise_()
        self.activateWindow()

    def open_notepad(self):
        """Orijinal qaZNot not defterini açar (exe yanında ya da kaynak dosyası)."""
        nb = getattr(self, "notepad", None)
        if nb is not None:  # qaZNot'tan açıldıysak aynı süreçteki not defterini öne getir
            nb.show()
            nb.raise_()
            nb.activateWindow()
            return
        here = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
        try:
            exe = os.path.join(here, "qaZNot.exe")
            script = os.path.join(here, "qaznote_qt.py")
            if os.path.isfile(exe):
                cmd = [exe]
            elif os.path.isfile(script):
                import shutil
                cmd = [shutil.which("pythonw") or sys.executable, script]
            else:
                self.toast("qaZNot bulunamadı", error=True)
                return
            subprocess.Popen(cmd, cwd=here, creationflags=0x00000008 | 0x00000200)
            self.toast("qaZNot açılıyor…")
        except OSError as ex:
            self.toast(f"Açılamadı: {ex}", error=True)

    def _open_path(self, path):
        try:
            doc = E.qv_load(self.acct.ed, path)
        except (E.QvPermissionError, ValueError, OSError) as ex:
            QMessageBox.warning(self, "qAnvas", f"Açılamadı: {ex}")
            return
        self.load_doc(doc, path)

    def save(self, as_new=False):
        path = self.path
        if as_new or not path:
            safe = "".join(c for c in self.doc.name if c.isalnum() or c in " -_") or "tasarim"
            path, _ = QFileDialog.getSaveFileName(self, "Kaydet", safe + E.QV_EXT, "qAnvas (*.qanvas)")
            if not path:
                return False
            if not path.lower().endswith(E.QV_EXT):
                path += E.QV_EXT
        try:
            self.doc.save(path)
        except OSError as ex:
            QMessageBox.warning(self, "qAnvas", f"Kaydedilemedi: {ex}")
            return False
        self.path = path
        self.dirty = False
        self.update_title()
        self.toast("Kaydedildi")
        return True

    def rename_doc(self):
        name, ok = QInputDialog.getText(self, "Ad", "Tasarım adı:", text=self.doc.name)
        if ok and name.strip():
            self.doc.name = name.strip()[:80]
            self.dirty = True
            self.update_title()

    def closeEvent(self, e):
        if self.confirm_discard():
            e.accept()
        else:
            e.ignore()

    # ---------------- hesap ----------------
    def refresh_account(self):
        a = self.acct
        self.acc_btn.setIcon(QIcon(a.avatar(56)))
        self.acc_btn.setText(f"  {a.name}  ·  {a.ed['label']}")
        if hasattr(self, "cb_font"):
            self.populate_fonts()

    def open_account(self):
        dlg = AccountDialog(self.acct, parent=self)
        dlg.exec()
        if dlg.signout:
            self.sign_out()
        else:
            self.refresh_account()

    def sign_out(self):
        if not self.confirm_discard():
            return
        Account.forget()
        self.hide()
        dlg = AccountDialog(None, required=True)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.acct:
            self.acct = dlg.acct
            self.refresh_account()
            self.show()
        else:
            self.dirty = False
            QApplication.quit()


def fake_account(ed="enterprise"):
    acc = dict(ed=ed, user="Test", name="Test kullanıcısı", email="test@qaz.local.net", id="QZ-T-000", since="2026-11-03")
    return Account("TEST-0000-0000-0000-0000", acc)


def main():
    args = sys.argv[1:]
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
    path_arg = next((a for a in args if a.lower().endswith(E.QV_EXT) and os.path.isfile(a)), None)
    if path_arg:
        path_arg = os.path.abspath(path_arg)
    inst = os.environ.get("QV_INSTANCE", "qanvas-pyside6")
    single = "--shot" not in args and "--multi" not in args
    if single:  # zaten açıksa yenisini açma: var olanı öne getir (gerekirse dosyayı ona ilet)
        sk = QLocalSocket()
        sk.connectToServer(inst)
        if sk.waitForConnected(400):
            sk.write(("OPEN:" + path_arg if path_arg else "FOCUS").encode("utf-8"))
            sk.flush()
            sk.waitForBytesWritten(800)
            sk.disconnectFromServer()
            return 0
    if "--fake" in args:
        acct = fake_account(args[args.index("--fake") + 1])
    else:
        acct = Account.load()
        if acct is None:
            dlg = AccountDialog(None, required=True)
            if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.acct:
                return 0
            acct = dlg.acct
    doc = None
    if "--template" in args:
        doc = E.qv_new_template(acct.ed, args[args.index("--template") + 1])
    if path_arg and doc is None:
        try:
            doc = E.qv_load(acct.ed, path_arg)
        except (E.QvPermissionError, ValueError, OSError) as ex:
            QMessageBox.warning(None, "qAnvas", f"Açılamadı: {ex}")
            path_arg = None
    win = MainWindow(acct, doc)
    if path_arg and doc is not None:
        win.path = path_arg
    win.show()
    if single:
        server = QLocalServer(win)
        QLocalServer.removeServer(inst)
        server.listen(inst)

        def on_conn():
            c = server.nextPendingConnection()
            c.waitForReadyRead(400)
            msg = bytes(c.readAll()).decode("utf-8", "replace")
            c.disconnectFromServer()
            win.bring_to_front()
            if msg.startswith("OPEN:"):
                win.open_path(msg[5:])
        server.newConnection.connect(on_conn)
        win._server = server
    if os.environ.get("QV_DEBUG_EXIT_MS"):  # yalnızca test için
        QTimer.singleShot(int(os.environ["QV_DEBUG_EXIT_MS"]),
                          lambda: (print("PATH=", win.path, "DOC=", win.doc.name, flush=True), win.dirty and None,
                                   setattr(win, "dirty", False), app.quit()))
    if "--shot" not in args:
        window_fade_in(win, 450)
    if "--shot" in args:
        out = args[args.index("--shot") + 1]

        def shot():
            if win.items:
                win.items[min(1, len(win.items) - 1)].setSelected(True)
            win.grab().save(out)
            app.quit()
        QTimer.singleShot(1200, shot)
    elif "--no-launcher" not in args and doc is None and not path_arg:
        QTimer.singleShot(200, win.new_doc_dialog)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
