"""qaZNot (PySide6) ana pencere: ayarlar, tema, biçim komutları, bul/değiştir, başlangıç ekranı, hesap, qAnvas, Discord."""
import os
import re
import subprocess
import sys
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QIcon, QFontDatabase, QShortcut, QKeySequence
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QStackedWidget, QFrame, QApplication, QLabel,
                               QInputDialog, QDialog, QTextBrowser, QTabBar)

import qv_engine as E
from qv_login import Account, AccountDialog
from qv_theme import QSS as DARK_QSS
from qv_widgets import AButton, set_theme, fade_in, slide_in
from qz_version import VERSION, CODENAME, BUILD_DATE, history_html
from qz_editor import Editor
from qz_docs import DocsMixin
from qz_files import FilesMixin
from qz_export import ExportMixin
from qz_extra import ExtraMixin, IMG_EXT
from qz_home import HomeScreen
from qz_popups import FontPicker, ColorPopup, ThemePopup
from qz_style import qss, ui_family, set_titlebar, qz_icon
from qz_ui import UIMixin

APP = "qaZNot"


class QazWindow(QMainWindow, DocsMixin, ExportMixin, ExtraMixin, FilesMixin, UIMixin):
    def __init__(self, acct, start_file=None):
        super().__init__()
        self.acct = acct
        self.testing = acct.key.startswith("TEST-")  # sahte hesapla testte gerçek ayar/Discord'a dokunma
        self.cfg = E.read_json(E.CONFIG)
        self.docs, self.cur_doc = [], None
        self.open_count = 0
        self.home = None
        self.qv_win = None
        self.signed_out = False
        self.focus_on = False
        self.start_file = start_file if isinstance(start_file, str) else None
        self.start_files = list(start_file) if isinstance(start_file, (list, tuple)) else None
        c = self.cfg
        self.home_on = c.get("show_home", True)
        self.discord_on = c.get("discord_on", False) and not self.testing
        self.discord_file = c.get("discord_file", False)
        self.theme_name = E.LEGACY_THEMES.get(c.get("theme"), c.get("theme")) if c.get("theme") in E.THEMES or \
            c.get("theme") in E.LEGACY_THEMES else "Beyaz"
        if not self.theme_ok(self.theme_name):
            self.theme_name = "Beyaz"
        self.T = E.THEMES[self.theme_name]
        set_theme(self.T)
        self.ui_fam = ui_family(QFontDatabase.families())
        self.setWindowTitle(APP)
        icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "icon.png")
        if os.path.exists(icon):
            self.setWindowIcon(QIcon(icon))
        self.setMinimumSize(560, 360)

        self.base_family = c.get("family") or self.default_family()
        self.base_size = int(c.get("size", 12))
        self.zoom = int(c.get("zoom", 100))
        self.estack = QStackedWidget()

        # sayfa: editör kabuğu + başlangıç ekranı
        root = QWidget()
        root.setObjectName("qzroot")
        rl = QVBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        self.stack = QStackedWidget()
        rl.addWidget(self.stack)
        self.shell = QWidget()
        sl = QVBoxLayout(self.shell)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(0)
        sl.addWidget(self._build_top())
        sl.addWidget(self._build_toolbar())
        sl.addWidget(self._build_tabrow())
        self.findbar = self._build_findbar()
        sl.addWidget(self.findbar)
        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(10, 4, 10, 10)
        card = QFrame()
        card.setObjectName("qzedcard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(4, 4, 4, 4)
        cl.addWidget(self.estack)
        wl.addWidget(card)
        sl.addWidget(wrap, 1)
        self.status = self._build_status()
        self.status.setVisible(c.get("status", True))
        sl.addWidget(self.status)
        self.stack.addWidget(self.shell)
        self.setCentralWidget(root)

        self._counts_timer = QTimer(self)
        self._counts_timer.setSingleShot(True)
        self._counts_timer.timeout.connect(self.update_counts)
        self._auto = QTimer(self)
        self._auto.timeout.connect(self.autosave)
        self._auto.start(15000)

        self.rpc = E.DiscordRPC()
        self.rpc.start()
        self._rpc_timer = QTimer(self)
        self._rpc_timer.timeout.connect(self._rpc_tick)
        self._rpc_timer.start(4000)

        self.apply_theme(self.theme_name, save=False, animate=False)
        self.add_doc()
        self.restore_geometry()
        self.refresh_account()
        self.update_title()
        self.setAcceptDrops(True)
        QShortcut(QKeySequence("F11"), self).activated.connect(self.toggle_focus)
        self.watch_system_theme()
        self.follow_system_theme()

    # ---------- ayarlar ----------
    def default_family(self):
        fams = {f.lower(): f for f in QFontDatabase.families()}
        for f in ("Segoe UI", "Calibri", "Arial", "Helvetica", "DejaVu Sans"):
            if f.lower() in fams:
                return fams[f.lower()]
        return "Segoe UI"

    def save_settings(self):
        if self.testing:
            return
        c = self.cfg
        c.update(theme=self.theme_name, family=self.base_family, size=self.base_size,
                 wrap=c.get("wrap", True), status=c.get("status", True),
                 zoom=self.zoom, show_home=self.home_on, discord_on=self.discord_on,
                 discord_file=self.discord_file, account_id=self.acct.aid, version=2)
        if not getattr(self, "signed_out", False):
            self.acct.remember_into(c)
        if self.filename:
            c["last_file"] = self.filename
        if not self.isMaximized() and self.isVisible():
            g = self.geometry()
            c["geometry"] = f"{g.width()}x{g.height()}+{g.x()}+{g.y()}"
        c["zoomed"] = self.isMaximized()
        data = E.read_json(E.CONFIG)
        data.update(c)
        if data.get("license_enc"):
            data.pop("license", None)  # düz metin anahtar kalmasın
        E.write_json(E.CONFIG, data)

    def restore_geometry(self):
        m = re.fullmatch(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", str(self.cfg.get("geometry", "")))
        scr = QApplication.primaryScreen().availableGeometry()
        if m:
            w, h, x, y = (int(v) for v in m.groups())
            w, h = min(max(w, 560), scr.width()), min(max(h, 360), scr.height())
            x, y = min(max(x, scr.left()), scr.right() - w), min(max(y, scr.top()), scr.bottom() - h)
            self.setGeometry(x, y, w, h)
        else:
            self.resize(1040, 700)
        if self.cfg.get("zoomed"):
            self.setWindowState(Qt.WindowState.WindowMaximized)

    # ---------- tema ----------
    def theme_ok(self, name):
        t = self.acct.ed["themes"]
        return t is None or name in t

    def apply_theme(self, name, save=True, animate=True):
        self.theme_name = name
        self.T = E.THEMES[name]
        set_theme(self.T)
        self.setStyleSheet(qss(self.T, self.ui_fam))
        for ed in self.all_editors():
            ed.match_color = self.T["match"]
            ed.setStyleSheet(f"QTextEdit#qzedit {{ color: {self.T['fg']}; background: {self.T['bg']}; }}")
        for d in self.docs:
            b = self.tabbar.tabButton(self.doc_index(d), QTabBar.ButtonPosition.RightSide)
            if b is not None:
                b.setIcon(qz_icon("close", self.T["muted"], 16))
        self.refresh_icons()
        set_titlebar(self, self.T)
        if self.home is not None:
            self.home.build(False)
        if animate:
            fade_in(self.shell, 260)
        self.on_find_type() if self.findbar.isVisible() else None
        if save:
            self.save_settings()

    def open_theme_popup(self):
        ThemePopup(self, self.theme_name, self.theme_ok, self.set_theme,
                   lambda: self.toast("Bu tema Enterprise ve Professional sürümlerinde")).show_below(self.b_theme, "right")

    def set_theme(self, name):
        if self.theme_ok(name):
            self.apply_theme(name)

    def next_theme(self):
        names = [t["name"] for t in E.THEME_LIST if self.theme_ok(t["name"])]
        i = names.index(self.theme_name) if self.theme_name in names else -1
        self.set_theme(names[(i + 1) % len(names)])

    # ---------- biçim komutları ----------
    def families(self):
        allowed = self.acct.ed.get("fonts")
        fams = sorted(set(QFontDatabase.families()), key=str.lower)
        if allowed:
            low = {a.lower() for a in allowed}
            fams = [f for f in fams if f.lower() in low] or [self.ui_fam]
        return fams

    def on_toggle(self, prop):
        self.editor.toggle(prop)
        self.editor.setFocus()

    def on_align(self, a):
        self.editor.set_align(a)
        self.editor.setFocus()

    def clear_format(self):
        self.editor.clear_format()
        self.editor.setFocus()

    def step_size(self, d):
        cur = float(self.editor.style()["size"])
        bigger = [s for s in E.SIZES if s > cur]
        smaller = [s for s in E.SIZES if s < cur]
        if d > 0:
            nxt = bigger[0] if bigger else min(400, cur + 8)
        else:
            nxt = smaller[-1] if smaller else max(1, cur - 1)
        self.editor.set_size(nxt)
        self.editor.setFocus()

    def on_size_enter(self):
        try:
            v = float(self.size_edit.text().replace(",", "."))
        except ValueError:
            self.sync_toolbar()
            return
        self.editor.set_size(int(max(1, min(400, v))))
        self.editor.setFocus()

    def open_font_picker(self):
        rec = self.cfg.get("recent", [])
        FontPicker(self, self.families(), rec, self.editor.style()["family"], self.pick_family,
                   core_note=bool(self.acct.ed.get("fonts"))).show_below(self.font_btn)

    def pick_family(self, fam):
        self.editor.set_family(fam)
        self.cfg["recent"] = ([fam] + [f for f in self.cfg.get("recent", []) if f != fam])[:6]
        self.save_settings()
        self.editor.setFocus()

    def open_fg_popup(self):
        ColorPopup(self, "Yazı Rengi", self.editor.style()["fg"], lambda c: self._pick_color("fg", c), "Otomatik",
                   self.T["border"]).show_below(self.b_fg)

    def open_bg_popup(self):
        ColorPopup(self, "Vurgu Rengi", self.editor.style()["bg"], lambda c: self._pick_color("bg", c), "Vurgu yok",
                   self.T["border"]).show_below(self.b_bg)

    def _pick_color(self, which, color):
        self.editor.set_color(which, color)
        if color:
            self.cfg["last_fg" if which == "fg" else "last_bg"] = color
            self.save_settings()
        self.editor.setFocus()

    def set_default_font(self):
        st = self.editor.style()
        self.base_family, self.base_size = st["family"], int(st["size"])
        for ed in self.all_editors():
            ed.apply_base(self.base_family, self.base_size)
        self.save_settings()
        self.toast(f"Varsayılan yazı tipi: {st['family']} {int(st['size'])}")
        self.sync_toolbar()

    def toggle_wrap(self, on):
        self.cfg["wrap"] = bool(on)
        for ed in self.all_editors():
            ed.setLineWrapMode(Editor.LineWrapMode.WidgetWidth if on else Editor.LineWrapMode.NoWrap)
        self.save_settings()

    def toggle_status(self, on):
        self.status.setVisible(on)
        self.cfg["status"] = bool(on)
        self.save_settings()

    def change_zoom(self, delta, reset=False):
        self.zoom = max(10, min(500, 100 if reset else self.zoom + delta))
        for ed in self.all_editors():
            ed.set_zoom(self.zoom)
        self.save_settings()

    def apply_zoom_ui(self):
        self.lbl_zoom.setText(f"%{self.zoom}")

    def insert_datetime(self):
        self.editor.insertPlainText(datetime.now().strftime("%H:%M %d.%m.%Y"))

    def goto_line(self):
        n, ok = QInputDialog.getInt(self, "Satıra Git", "Satır numarası:", 1, 1, max(1, self.editor.document().blockCount()))
        if ok:
            self.editor.goto_line(n)

    # ---------- bul / değiştir ----------
    def show_find(self, replace=False):
        if self.stack.currentWidget() is not self.shell:
            return
        self.findbar.show()
        c = self.editor.textCursor()
        if c.hasSelection() and "\u2029" not in c.selectedText():
            self.f_entry.setText(c.selectedText())
        self.r2.setVisible(replace or self.r2.isVisible())
        self.f_entry.setFocus()
        self.f_entry.selectAll()
        self.on_find_type()

    def toggle_replace(self):
        self.r2.setVisible(not self.r2.isVisible())

    def hide_find(self):
        self.findbar.hide()
        self.editor.clear_highlight()
        self.editor.setFocus()

    def find_opts(self):
        return dict(case=self.f_case.isChecked(), whole=self.f_word.isChecked(), regex=self.f_regex.isChecked())

    def on_find_type(self):
        term, o = self.f_entry.text(), self.find_opts()
        n = self.editor.highlight_all(term, o["case"], o["whole"], o["regex"])
        if term and n:
            self.editor.find_step(term, o["case"], stay=True, whole=o["whole"], regex=o["regex"])
        self.update_find_count(term, n)

    def update_find_count(self, term=None, n=None):
        term = self.f_entry.text() if term is None else term
        n = len(self.editor._matches) if n is None else n
        if not term:
            self.f_count.setText("")
        elif self.editor.find_error:
            self.f_count.setText("Geçersiz ifade")
        elif not n:
            self.f_count.setText("Sonuç yok")
        else:
            cur = self.editor.current_match_index()
            self.f_count.setText(f"{cur if cur else '–'} / {n}")

    def find_go(self, backward):
        if not self.findbar.isVisible():
            self.show_find(False)
            return
        o = self.find_opts()
        self.editor.find_step(self.f_entry.text(), o["case"], backward, whole=o["whole"], regex=o["regex"])
        self.update_find_count()

    def replace_one(self):
        o = self.find_opts()
        self.editor.replace_one(self.f_entry.text(), self.r_entry.text(), o["case"], o["whole"], o["regex"])
        self.on_find_type()

    def replace_all(self):
        o = self.find_opts()
        n = self.editor.replace_all(self.f_entry.text(), self.r_entry.text(), o["case"], o["whole"], o["regex"])
        self.on_find_type()
        self.toast(f"{n} değiştirildi")

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            if self.focus_on:
                self.toggle_focus(False)
                return
            if self.findbar.isVisible():
                self.hide_find()
                return
            if self.stack.currentWidget() is self.home:
                self.hide_home()
                return
        super().keyPressEvent(e)

    # ---------- durum çubuğu / başlık ----------
    def schedule_counts(self):
        self._counts_timer.start(180)

    def update_pos(self):
        w, ch, sel, ln, col = self.editor.stats()
        self.lbl_pos.setText(f"Satır {ln}, Sütun {col}")
        self.update_counts_sel(w, ch, sel)

    def update_counts(self):
        self.update_pos()

    def update_counts_sel(self, w, ch, sel):
        self.lbl_count.setText(f"{w} kelime · {ch} karakter" + (f" · {sel} seçili" if sel else ""))
        gt, reached = self.goal_text(w)
        self.lbl_goal.setText(gt)
        self.lbl_goal.setStyleSheet(f"color: {self.T['accent']}; font-weight: 600;" if reached else "")
        rich = self.fmt == "qaz" or self.editor.has_formatting()
        self.lbl_kind.setText("Zengin metin" if rich else E.ENC_LABELS.get(self.encoding, self.encoding))

    def findbar_refresh(self):
        if self.findbar.isVisible():
            self.on_find_type()

    def update_title(self):
        name = os.path.basename(self.filename) if self.filename else "Adsız"
        self.setWindowTitle(f"{'● ' if self.dirty else ''}{name} — {APP}")
        if self.cur_doc is not None:
            self.refresh_tab(self.cur_doc)
        sig = ""
        if self.sig_ok:
            sig = f"   ✓ İmzalı: {self.sig_raw.get('name', '')}"
        elif self.sig_ok is False:
            sig = "   ⚠ İmza geçersiz"
        self.doc_label.setText(f"{'● ' if self.dirty else ''}{name}{sig}")

    def autosave(self):
        try:
            self.write_draft()
            self.save_settings()
        except Exception:  # noqa: BLE001
            pass

    # ---------- başlangıç ekranı ----------
    def home_visible(self):
        return self.home is not None and self.stack.currentWidget() is self.home

    def show_home(self, animate=True):
        self.findbar.hide()
        if self.home is None:
            self.home = HomeScreen(self)
            self.stack.addWidget(self.home)
        else:
            self.home.build(False)
        self.stack.setCurrentWidget(self.home)
        if animate:
            slide_in(self.home, 0, 70, 420)
            fade_in(self.home, 340)
        self.home.search.setFocus()

    def hide_home(self):
        if not self.home_visible():
            return
        self.stack.setCurrentWidget(self.shell)
        fade_in(self.shell, 260)
        self.editor.setFocus()

    def home_new(self):
        self.new_file()
        self.hide_home()

    def home_browse(self):
        before = self.open_count
        self.open_dialog()
        if self.open_count > before:
            self.hide_home()

    def home_open(self, path):
        if self.open_file(path):
            self.hide_home()

    def refresh_home(self):
        if self.home is not None and self.home_visible():
            self.home.build(False)

    TEXT_EXT = {".qaz", ".txt", ".md", ".log", ".csv", ".json", ".xml", ".ini", ".py", ".js", ".html", ".css", ""}

    def _drop_paths(self, e):
        out = []
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            if p and os.path.isfile(p) and os.path.splitext(p)[1].lower() in (self.TEXT_EXT | set(IMG_EXT)):
                out.append(p)
        return out

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and self._drop_paths(e):
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls() and self._drop_paths(e):
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = self._drop_paths(e)
        for p in paths:
            if os.path.splitext(p)[1].lower() in IMG_EXT:
                self.hide_home()
                self.insert_image_file(p)
            else:
                self.open_file(p)
        if paths:
            self.hide_home()
            self.bring_to_front()
            e.acceptProposedAction()

    def bring_to_front(self):
        self.setWindowState((self.windowState() & ~Qt.WindowState.WindowMinimized) | Qt.WindowState.WindowActive)
        self.show()
        self.raise_()
        self.activateWindow()

    def toggle_assoc(self, on):
        import qz_assoc
        ok = qz_assoc.register() if on else qz_assoc.unregister()
        self.toast(".qaz dosyaları artık qaZNot ile açılacak" if on and ok else
                   ".qaz ilişkilendirmesi kaldırıldı" if ok else "İşlem başarısız")

    def new_window(self):
        script = os.path.abspath(sys.argv[0])
        cmd = ([sys.executable] if getattr(sys, "frozen", False) else [sys.executable, script]) + ["--multi"]
        try:
            subprocess.Popen(cmd, creationflags=0x00000008 if os.name == "nt" else 0)
        except OSError as e:
            self.error(f"Yeni pencere açılamadı:\n{e}")

    # ---------- qAnvas (aynı süreçte, PySide6) ----------
    def open_qanvas(self):
        import qanvas as QV
        w = self.qv_win
        if w is not None and w.isVisible():
            w.bring_to_front()
            return
        self.toast("qAnvas açılıyor…")
        w = QV.MainWindow(self.acct)
        w.notepad = self
        w.show()
        QTimer.singleShot(250, w.new_doc_dialog)
        self.qv_win = w

    # ---------- hesap ----------
    def refresh_account(self):
        a = self.acct
        self.acc_btn.setText(f"{a.name}  ·  {a.ed['label']}")
        self.acc_btn.setFixedWidth(max(120, self.acc_btn.fontMetrics().horizontalAdvance(self.acc_btn.text()) + 28))

    def need_feature(self, feature, msg):
        if self.acct.ed.get(feature):
            return True
        self.toast(msg)
        return False

    def open_account(self):
        dlg = AccountDialog(self.acct)
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        dlg.exec()
        if dlg.signout:
            QTimer.singleShot(30, self.sign_out_flow)
        else:
            self.refresh_account()
            self.refresh_home()

    def confirm_all(self):
        """Tüm sekmelerdeki kaydedilmemiş değişiklikleri sorar. True: devam edilebilir."""
        for d in list(self.docs):
            if d.dirty:
                self.switch_to(d)
                if not self.confirm_save():
                    return False
        return True

    def sign_out_flow(self):
        if not self.confirm_all():
            return
        self.drop_draft()
        self.hide_home()
        Account.forget()
        self.signed_out = True
        self.cfg.pop("license_enc", None)
        self.cfg.pop("license", None)
        self.hide()
        dlg = AccountDialog(None, required=True)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.acct:
            self.signed_out = False
            self.acct = dlg.acct
            if not self.theme_ok(self.theme_name):
                self.apply_theme("Siyah" if self.T["dark"] else "Beyaz")
            self.refresh_account()
            self.show()
            self.show_home()
        else:
            for d in self.docs:
                d.dirty = False
            self.close()

    def about(self):
        self.info(f"qaZNot {CODENAME}\nTemalı, zengin metin destekli Not Defteri.\nSürüm: {VERSION}\nLisans: {self.acct.ed['label']}\n"
                  f"Derleme: {BUILD_DATE}\nPython / PySide6 ile yazıldı.")

    def show_versions(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(f"{APP} - Sürüm Geçmişi")
        dlg.resize(560, 520)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(18, 16, 18, 14)
        t = QLabel(f"qaZNot {CODENAME}")
        t.setObjectName("qzbig")
        s = QLabel(f"Sürüm {VERSION} · {self.acct.ed['label']} sürümü · Derleme: {BUILD_DATE}")
        s.setObjectName("qzmuted")
        lay.addWidget(t)
        lay.addWidget(s)
        lay.addSpacing(6)
        view = QTextBrowser()
        view.setFrameShape(QFrame.Shape.NoFrame)
        view.setStyleSheet(f"QTextBrowser {{ background: {self.T['bg']}; border: 1px solid {self.T['border']}; "
                           f"border-radius: 10px; padding: 8px; }}")
        view.setHtml(history_html(self.T))
        lay.addWidget(view, 1)
        ok = AButton("Tamam")
        ok.setObjectName("qzprimary")
        ok.setFixedHeight(36)
        ok.clicked.connect(dlg.accept)
        lay.addWidget(ok)
        dlg.exec()

    # ---------- Discord ----------
    def discord_activity(self):
        ed = f"{self.acct.ed['label']} sürümü"
        if self.home_visible():
            return dict(details="Başlangıç ekranında", state=ed)
        if self.discord_file:
            name = os.path.basename(self.filename) if self.filename else "Adsız belge"
            return dict(details="Belge düzenliyor" + (" ●" if self.dirty else ""), state=name[:100])
        return dict(details="Belge düzenliyor", state=ed)

    def _rpc_payload(self):
        a = self.discord_activity()
        act = {"type": 0, "details": a["details"], "timestamps": {"start": self.rpc.start_ts},
               "assets": {"large_image": E.DISCORD_ASSET, "large_text": f"{APP} {self.acct.ed['label']}"}}
        if a["state"] and len(a["state"]) >= 2:
            act["state"] = a["state"]
        return act

    def _rpc_tick(self):
        self.rpc.update(self.discord_on, self._rpc_payload() if self.discord_on else None)

    def set_discord(self, on=None, file=None, quiet=False):
        if on is not None:
            self.discord_on = bool(on)
        if file is not None:
            self.discord_file = bool(file)
        for a, v in ((self.a_dv, self.discord_on), (self.a_df, self.discord_file)):
            a.blockSignals(True)
            a.setChecked(v)
            a.blockSignals(False)
        self.save_settings()
        self.rpc.update(self.discord_on, self._rpc_payload() if self.discord_on else None)
        if not quiet:
            self.toast("Discord durumu kapatıldı" if not self.discord_on else
                       "Discord'da gösteriliyor (dosya adı görünür)" if self.discord_file else
                       "Discord'da gösteriliyor (dosya adı gizli)")

    # ---------- başlangıç / kapanış ----------
    def after_login(self, welcome=True):
        if welcome:
            self.toast(f"Hoş geldin, {self.acct.name}")
        files = [f for f in (self.start_files or ([self.start_file] if self.start_file else [])) if os.path.isfile(f)]
        if files:
            for f in files:
                self.open_file(f)
        elif not self.testing and self.restore_draft():
            pass
        elif self.home_on:
            self.show_home()
        elif self.cfg.get("last_file") and os.path.isfile(self.cfg["last_file"]):
            self.open_file(self.cfg["last_file"])

    def closeEvent(self, e):
        if not self.confirm_all():
            e.ignore()
            return
        self.drop_draft()
        self.save_settings()
        self.rpc.stop()
        if self.qv_win is not None:
            self.qv_win.close()
        e.accept()
