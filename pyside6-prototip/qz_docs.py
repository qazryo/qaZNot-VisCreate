"""qaZNot sekmeler: her sekme bir belge (Doc). Pencere, geçerli sekmenin durumuna özellik olarak erişir."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTabBar, QWidget

from qv_widgets import ATool
from qz_editor import Editor
from qz_style import qz_icon


class Doc:
    """Bir sekmedeki belgenin durumu."""

    def __init__(self, editor):
        self.editor = editor
        self.filename = None
        self.fmt, self.encoding, self.plain_ok = "txt", "utf-8", False
        self.sig_raw = self.sig_ok = None
        self.password = None  # şifreli kaydedilecekse bellekte tutulur, dosyaya yazılmaz
        self.versions_key = None

    @property
    def dirty(self):
        return self.editor.document().isModified()

    @dirty.setter
    def dirty(self, v):
        self.editor.document().setModified(bool(v))

    @property
    def name(self):
        return os.path.basename(self.filename) if self.filename else "Adsız"

    def is_blank(self):
        return not self.filename and not self.dirty and self.editor.document().isEmpty()


def _dp(name):
    return property(lambda s: getattr(s.cur_doc, name), lambda s, v: setattr(s.cur_doc, name, v))


class DocsMixin:
    filename = _dp("filename")
    fmt = _dp("fmt")
    encoding = _dp("encoding")
    plain_ok = _dp("plain_ok")
    sig_raw = _dp("sig_raw")
    sig_ok = _dp("sig_ok")
    dirty = _dp("dirty")
    password = _dp("password")

    @property
    def editor(self):
        return self.cur_doc.editor

    # ---------- sekme çubuğu ----------
    def _build_tabbar(self):
        tb = QTabBar()
        tb.setObjectName("qztabs")
        tb.setTabsClosable(False)
        tb.setMovable(True)
        tb.setExpanding(False)
        tb.setDrawBase(False)
        tb.setElideMode(Qt.TextElideMode.ElideRight)
        tb.setUsesScrollButtons(True)
        tb.currentChanged.connect(self.on_tab_changed)
        tb.tabMoved.connect(self.on_tab_moved)
        tb.tabBarDoubleClicked.connect(lambda i: self.add_doc() if i < 0 else None)
        self.tabbar = tb
        return tb

    def make_editor(self):
        ed = Editor()
        ed.apply_base(self.base_family, self.base_size)
        ed.setLineWrapMode(Editor.LineWrapMode.WidgetWidth if self.cfg.get("wrap", True) else Editor.LineWrapMode.NoWrap)
        ed.match_color = self.T["match"]
        ed.setStyleSheet(f"QTextEdit#qzedit {{ color: {self.T['fg']}; background: {self.T['bg']}; }}")
        ed.style_changed.connect(self.sync_toolbar)
        ed.cursorPositionChanged.connect(self.update_pos)
        ed.textChanged.connect(self.schedule_counts)
        ed.zoom_changed.connect(lambda z: self.lbl_zoom.setText(f"%{z}"))
        ed.set_zoom(self.zoom)
        ed.document().setModified(False)
        return ed

    def add_doc(self, activate=True):
        ed = self.make_editor()
        d = Doc(ed)
        ed.document().modificationChanged.connect(lambda m, d=d: self.on_modified(d, m))
        self.estack.addWidget(ed)
        self.docs.append(d)
        self.tabbar.blockSignals(True)
        i = self.tabbar.addTab(d.name)
        btn = ATool()
        btn.setObjectName("qz")
        btn.setFixedSize(20, 20)
        btn.setIconSize(btn.size() * 0.8)
        btn.setIcon(qz_icon("close", self.T["muted"], 16))
        btn.setToolTip("Sekmeyi kapat (Ctrl+W)")
        btn.clicked.connect(lambda *_, d=d: self.close_doc(d))
        self.tabbar.setTabButton(i, QTabBar.ButtonPosition.RightSide, btn)
        self.tabbar.blockSignals(False)
        if activate:
            self.switch_to(d)
        return d

    def doc_index(self, d):
        return self.docs.index(d)

    def switch_to(self, d):
        i = self.doc_index(d)
        self.tabbar.setCurrentIndex(i)
        self.on_tab_changed(i)

    def on_tab_changed(self, i):
        if not (0 <= i < len(self.docs)):
            return
        d = self.docs[i]
        if getattr(self, "cur_doc", None) is d and self.estack.currentWidget() is d.editor:
            return
        self.cur_doc = d
        self.estack.setCurrentWidget(d.editor)
        self.findbar_refresh()
        self.sync_toolbar()
        self.update_pos()
        self.update_title()

    def on_tab_moved(self, frm, to):
        self.docs.insert(to, self.docs.pop(frm))

    def on_modified(self, d, m):
        if m:
            d.sig_raw = d.sig_ok = None
        self.refresh_tab(d)
        if d is self.cur_doc:
            self.update_title()

    def refresh_tab(self, d):
        if d in self.docs:
            self.tabbar.setTabText(self.doc_index(d), ("● " if d.dirty else "") + ("🔒 " if d.password else "") + d.name)
            self.tabbar.setTabToolTip(self.doc_index(d), d.filename or "Kaydedilmemiş belge")

    def close_doc(self, d):
        """Sekmeyi kapatır (gerekirse kaydetmeyi sorar). Son sekme kapanırsa boş bir sekme açılır."""
        self.switch_to(d)
        if not self.confirm_save():
            return False
        i = self.doc_index(d)
        if len(self.docs) == 1:
            self.add_doc()
            i = self.doc_index(d)
        self.docs.remove(d)
        self.tabbar.blockSignals(True)
        self.tabbar.removeTab(i)
        self.tabbar.blockSignals(False)
        self.estack.removeWidget(d.editor)
        d.editor.deleteLater()
        self.cur_doc = None
        self.switch_to(self.docs[min(i, len(self.docs) - 1)])
        return True

    def close_current_tab(self):
        self.close_doc(self.cur_doc)

    def next_tab(self, step=1):
        if len(self.docs) > 1:
            self.switch_to(self.docs[(self.doc_index(self.cur_doc) + step) % len(self.docs)])

    def find_doc(self, path):
        p = os.path.normcase(os.path.abspath(path))
        for d in self.docs:
            if d.filename and os.path.normcase(os.path.abspath(d.filename)) == p:
                return d
        return None

    def all_editors(self):
        return [d.editor for d in self.docs]
