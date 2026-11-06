"""Yeni belge penceresi (hazir boyutlar, sablonlar, internet sablonlari, ozel boyut, dosyadan ac)."""
import json
import threading

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QStackedWidget,
                               QPushButton, QLabel, QWidget, QInputDialog, QFileDialog, QMessageBox,
                               QDoubleSpinBox, QApplication)

import qv_engine as E
from qv_theme import QSS as DARK_QSS
from qv_widgets import AButton, fade_in, window_fade_in
from qv_items import pil_to_qimage


class BG:
    """Islemi arka planda calistirir; bitince done(sonuc, hata) ana is parcacigindan cagrilir."""
    _live = []

    def __init__(self, fn, done):
        self.r = self.e = None
        self.fin = False
        self.done = done

        def run():
            try:
                self.r = fn()
            except Exception as ex:  # noqa: BLE001
                self.e = ex
            self.fin = True
        threading.Thread(target=run, daemon=True).start()
        self.t = QTimer()
        self.t.timeout.connect(self._poll)
        self.t.start(120)
        BG._live.append(self)

    def _poll(self):
        if self.fin:
            self.t.stop()
            BG._live.remove(self)
            self.done(self.r, self.e)


def doc_thumb(doc, size=200):
    im = doc.render()
    im.thumbnail((size, size))
    return QPixmap.fromImage(pil_to_qimage(im))


class NewDocDialog(QDialog):
    _thumbs = {}

    def __init__(self, acct, parent=None, can_cancel=True):
        super().__init__(parent)
        self.setStyleSheet(DARK_QSS)
        self.setWindowTitle("qAnvas - Yeni tasarım")
        self.resize(860, 560)
        self.acct = acct
        self.ed = acct.ed
        self.full = acct.full
        self.doc = None
        self.path = None
        root = QVBoxLayout(self)
        body = QHBoxLayout()
        root.addLayout(body, 1)
        self.cats = QListWidget()
        self.cats.setFixedWidth(190)
        names = ["Hazır Boyutlar"]
        if self.full:
            names += [c for c in E.qv_categories(self.ed)[1:] if c != E.QV_ONLINE_CAT]
            names += [E.QV_ONLINE_CAT, "Özel boyut"]
        for n in names:
            self.cats.addItem(n)
        body.addWidget(self.cats)
        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)
        self.p_presets = self._build_presets()
        self.p_tpl = self._build_tpl()
        self.p_online = self._build_online()
        self.p_custom = self._build_custom()
        for w in (self.p_presets, self.p_tpl, self.p_online, self.p_custom):
            self.stack.addWidget(w)
        foot = QHBoxLayout()
        self.msg = QLabel("")
        self.msg.setObjectName("sub")
        foot.addWidget(self.msg, 1)
        b = AButton("Dosyadan aç…")
        b.clicked.connect(self.open_file)
        foot.addWidget(b)
        if can_cancel:
            c = AButton("Vazgeç")
            c.clicked.connect(self.reject)
            foot.addWidget(c)
        root.addLayout(foot)
        if not self.full:
            self.msg.setText("Core sürümde yalnızca 3 hazır boyut var. Şablonlar ve özel boyut Enterprise/Professional'da.")
        self.cats.currentTextChanged.connect(self.on_cat)
        self.cats.setCurrentRow(0)

    # ---- sayfalar ----
    def _icon_list(self, size=170):
        lw = QListWidget()
        lw.setViewMode(QListWidget.ViewMode.IconMode)
        lw.setIconSize(QSize(size, size))
        lw.setResizeMode(QListWidget.ResizeMode.Adjust)
        lw.setMovement(QListWidget.Movement.Static)
        lw.setSpacing(8)
        lw.setWordWrap(True)
        lw.setGridSize(QSize(size + 24, size + 46))
        return lw

    def _build_presets(self):
        lw = QListWidget()
        pool = list(E.QV_CORE_PRESETS) + (list(E.QV_EXTRA_SIZES) if self.full else [])
        for p in pool:
            it = QListWidgetItem(f"{p['name']}    {p['w']} × {p['h']} px")
            it.setData(Qt.ItemDataRole.UserRole, p["id"])
            lw.addItem(it)
        lw.itemDoubleClicked.connect(lambda it: self.pick(lambda: E.qv_new_preset(self.ed, it.data(Qt.ItemDataRole.UserRole))))
        self.lw_presets = lw
        return lw

    def _build_tpl(self):
        self.lw_tpl = self._icon_list()
        self.lw_tpl.itemDoubleClicked.connect(
            lambda it: self.pick(lambda: E.qv_new_template(self.ed, it.data(Qt.ItemDataRole.UserRole))))
        return self.lw_tpl

    def _build_online(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        row = QHBoxLayout()
        b1 = AButton("Şablonları yenile")
        b1.clicked.connect(self.online_refresh)
        b2 = AButton("Adresten ekle…")
        b2.clicked.connect(self.online_url)
        row.addWidget(b1)
        row.addWidget(b2)
        row.addStretch(1)
        lay.addLayout(row)
        self.lw_online = self._icon_list()
        self.lw_online.itemDoubleClicked.connect(
            lambda it: self.pick(lambda: E.qv_online_load(it.data(Qt.ItemDataRole.UserRole))))
        lay.addWidget(self.lw_online, 1)
        return w

    def _build_custom(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Özel çözünürlük (piksel)"))
        row = QHBoxLayout()
        self.cw, self.ch = QDoubleSpinBox(), QDoubleSpinBox()
        for s, v in ((self.cw, 1920), (self.ch, 1080)):
            s.setRange(E.QV_MIN, E.QV_MAX)
            s.setDecimals(0)
            s.setValue(v)
            s.setMinimumWidth(110)
        row.addWidget(self.cw)
        row.addWidget(QLabel("×"))
        row.addWidget(self.ch)
        row.addStretch(1)
        lay.addLayout(row)
        hint = QLabel(f"{E.QV_MIN}–{E.QV_MAX} px, en fazla {E.QV_MAX_PIXELS // 1_000_000} megapiksel")
        hint.setObjectName("hint")
        lay.addWidget(hint)
        go = AButton("Oluştur")
        go.setObjectName("accent")
        go.setFixedWidth(140)
        go.clicked.connect(lambda: self.pick(lambda: E.qv_new_custom(self.ed, self.cw.value(), self.ch.value())))
        lay.addWidget(go)
        lay.addStretch(1)
        return w

    # ---- islevler ----
    def showEvent(self, e):
        super().showEvent(e)
        if not getattr(self, "_shown", False):
            self._shown = True
            window_fade_in(self, 300)

    def on_cat(self, name):
        if not name:
            return
        QTimer.singleShot(0, lambda: fade_in(self.stack.currentWidget(), 260))
        if name == "Hazır Boyutlar":
            self.stack.setCurrentWidget(self.p_presets)
        elif name == "Özel boyut":
            self.stack.setCurrentWidget(self.p_custom)
        elif name == E.QV_ONLINE_CAT:
            self.stack.setCurrentWidget(self.p_online)
            self.fill_online()
        else:
            self.stack.setCurrentWidget(self.p_tpl)
            self.fill_tpl(name)

    def fill_tpl(self, cat):
        self.lw_tpl.clear()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for t in E.qv_template_list(self.ed, cat):
                pm = NewDocDialog._thumbs.get(t["id"])
                if pm is None:
                    try:
                        pm = doc_thumb(E.qv_new_template(self.ed, t["id"]))
                    except Exception:  # noqa: BLE001
                        continue
                    NewDocDialog._thumbs[t["id"]] = pm
                it = QListWidgetItem(QIcon(pm), f"{t['name']}\n{t['w']}×{t['h']}")
                it.setData(Qt.ItemDataRole.UserRole, t["id"])
                self.lw_tpl.addItem(it)
        finally:
            QApplication.restoreOverrideCursor()

    def fill_online(self):
        self.lw_online.clear()
        entries = E.qv_online_list()
        if not entries:
            self.msg.setText("Henüz internet şablonu yok. 'Şablonları yenile'ye bas.")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for e in entries:
                key = "online-" + e["id"]
                pm = NewDocDialog._thumbs.get(key)
                if pm is None:
                    try:
                        pm = doc_thumb(E.qv_online_load(e))
                    except Exception:  # noqa: BLE001
                        continue
                    NewDocDialog._thumbs[key] = pm
                it = QListWidgetItem(QIcon(pm), f"{e['name']}\n{e['w']}×{e['h']}")
                it.setData(Qt.ItemDataRole.UserRole, e)
                self.lw_online.addItem(it)
        finally:
            QApplication.restoreOverrideCursor()

    def online_refresh(self):
        self.msg.setText("Şablonlar indiriliyor…")

        def done(res, err):
            if err:
                self.msg.setText(f"Hata: {err}")
                return
            added, errs = res
            self.msg.setText(f"{added} şablon eklendi." + (f" ({len(errs)} hata)" if errs else ""))
            self.fill_online()
        BG(E.qv_online_refresh, done)

    def online_url(self):
        url, ok = QInputDialog.getText(self, "Adresten ekle", "qAnvas ya da Fabric.js JSON adresi:")
        if not ok or not url.strip():
            return
        self.msg.setText("İndiriliyor…")

        def done(res, err):
            self.msg.setText(f"Hata: {err}" if err else "Şablon eklendi.")
            if not err:
                self.fill_online()
        BG(lambda: E.qv_import_url(url.strip()), done)

    def pick(self, make):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.doc = make()
        except (E.QvPermissionError, ValueError, OSError) as ex:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "qAnvas", str(ex))
            return
        QApplication.restoreOverrideCursor()
        self.accept()

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "qAnvas dosyası aç", "", "qAnvas (*.qanvas);;Tüm dosyalar (*)")
        if not path:
            return
        try:
            self.doc = E.qv_load(self.ed, path)
        except (E.QvPermissionError, ValueError, OSError, json.JSONDecodeError) as ex:
            QMessageBox.warning(self, "qAnvas", f"Açılamadı: {ex}")
            return
        self.path = path
        self.accept()
