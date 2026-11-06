"""qaZNot ek özellikler: liste/girinti/satır aralığı komutları, resim ekleme, odak modu, kelime hedefi, ayarlar,
kısayol listesi, sistem temasını izleme, güncelleme denetimi, hata kaydı."""
import json
import os
import sys
import threading
import traceback
import urllib.request
import webbrowser
from datetime import datetime

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QImage, QGuiApplication, QFont
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QComboBox, QSpinBox, QFileDialog,
                               QInputDialog, QMenu, QTextBrowser, QFrame, QGridLayout, QFontComboBox)

import qv_engine as E
from qv_widgets import AButton
from qz_version import VERSION, CODENAME, version_number

APP = "qaZNot"
IMG_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")

SHORTCUTS = [
    ("Dosya", [("Yeni sekme", "Ctrl+N"), ("Yeni pencere", "Ctrl+Shift+N"), ("Aç", "Ctrl+O"), ("Kaydet", "Ctrl+S"),
               ("Farklı kaydet", "Ctrl+Shift+S"), ("Sekmeyi kapat", "Ctrl+W"), ("Sonraki / önceki sekme", "Ctrl+Tab / Ctrl+Shift+Tab"),
               ("Yazdır", "Ctrl+P"), ("Başlangıç ekranı", "Ctrl+Shift+H")]),
    ("Düzenle", [("Geri al / yinele", "Ctrl+Z / Ctrl+Y"), ("Bul", "Ctrl+F"), ("Değiştir", "Ctrl+H"),
                 ("Sonrakini / öncekini bul", "F3 / Shift+F3"), ("Satıra git", "Ctrl+G"), ("Saat/tarih", "F5"),
                 ("Resim ekle", "Ctrl+Shift+I")]),
    ("Biçim", [("Kalın / italik / altı çizili", "Ctrl+B / Ctrl+I / Ctrl+U"), ("Üstü çizili", "Ctrl+Shift+X"),
               ("Yazı tipi", "Ctrl+D"), ("Sola / ortaya / sağa hizala", "Ctrl+L / Ctrl+E / Ctrl+R"),
               ("Madde işaretli / numaralı liste", "Ctrl+Shift+8 / Ctrl+Shift+7"), ("Girinti artır / azalt", "Ctrl+] / Ctrl+[")]),
    ("Görünüm", [("Tema galerisi", "Ctrl+T"), ("Sonraki tema", "F6"), ("Yakınlaştır / uzaklaştır / sıfırla", "Ctrl+Artı / Ctrl+Eksi / Ctrl+0"),
                 ("Odak modu", "F11 (çıkış: Esc)")]),
]


class ExtraMixin:
    # ---------- paragraf komutları ----------
    def on_list(self, name):
        self.editor.toggle_list(name)
        self.editor.setFocus()

    def on_indent(self, d):
        self.editor.change_indent(d)
        self.editor.setFocus()

    def on_spacing(self, pct):
        self.editor.set_line_spacing(pct)
        self.editor.setFocus()

    def open_spacing_menu(self):
        m = QMenu(self)
        for pct, label in ((100, "1,0"), (115, "1,15"), (150, "1,5"), (200, "2,0")):
            m.addAction(f"Satır aralığı {label}", lambda p=pct: self.on_spacing(p))
        m.exec(self.b_ls.mapToGlobal(self.b_ls.rect().bottomLeft()))

    # ---------- resim ----------
    def insert_image_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Resim ekle", "", "Resimler (*.png *.jpg *.jpeg *.bmp *.gif *.webp)")
        if path:
            self.insert_image_file(path)

    def insert_image_file(self, path):
        img = QImage(path)
        if img.isNull() or not self.editor.insert_image(img):
            self.toast("Resim açılamadı")
            return False
        self.editor.setFocus()
        return True

    # ---------- odak modu ----------
    FOCUS_FRAMES = ("qztop", "qztool", "qztabrow", "qzstatus")

    def toggle_focus(self, force=None):
        on = (not self.focus_on) if force is None else force
        if on == self.focus_on:
            return
        self.focus_on = on
        if on:
            self._focus_was_max = self.isMaximized()
            self.findbar.hide()
        anims = []
        for name in self.FOCUS_FRAMES:
            f = self.shell.findChild(QFrame, name)
            if f is None:
                continue
            if on:
                self._focus_h = getattr(self, "_focus_h", {})
                self._focus_h[name] = f.height() or f.maximumHeight()
                f.setMinimumHeight(0)
            a = QPropertyAnimation(f, b"maximumHeight", f)
            a.setDuration(220)
            a.setEasingCurve(QEasingCurve.Type.OutCubic)
            a.setStartValue(f.height())
            a.setEndValue(0 if on else self._focus_h.get(name, 40))
            if not on:
                a.finished.connect(lambda f=f, h=self._focus_h.get(name, 40): f.setFixedHeight(h))
            a.start()
            anims.append(a)
        self._focus_anims = anims
        if on:
            self.showFullScreen()
            self.toast("Odak modu: çıkmak için Esc ya da F11")
        else:
            self.showMaximized() if getattr(self, "_focus_was_max", False) else self.showNormal()
        self.editor.setFocus()

    # ---------- kelime hedefi ----------
    def set_goal(self):
        n, ok = QInputDialog.getInt(self, "Kelime Hedefi", "Hedef kelime sayısı (0: kapalı):", int(self.cfg.get("goal", 0)), 0, 1_000_000)
        if ok:
            self.cfg["goal"] = n
            self.save_settings()
            self.update_pos()

    def goal_text(self, words):
        g = int(self.cfg.get("goal", 0))
        if g <= 0:
            return "", False
        return f"Hedef: {words} / {g}" + ("  ✓" if words >= g else ""), words >= g

    # ---------- klavye kısayolları ----------
    def show_shortcuts(self):
        T = self.T
        html = [f"<body style='color:{T['fg']};'>"]
        for sec, rows in SHORTCUTS:
            html.append(f"<h3 style='margin-bottom:2px;'>{sec}</h3><table cellspacing='0' cellpadding='3'>")
            for a, k in rows:
                html.append(f"<tr><td width='260'>{a}</td><td style='color:{T['accent']};'><b>{k}</b></td></tr>")
            html.append("</table>")
        html.append("</body>")
        self._text_dialog("Klavye Kısayolları", "".join(html))

    def _text_dialog(self, title, html, size=(520, 560)):
        dlg = QDialog(self)
        dlg.setWindowTitle(f"{APP} - {title}")
        dlg.resize(*size)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(18, 16, 18, 14)
        view = QTextBrowser()
        view.setFrameShape(QFrame.Shape.NoFrame)
        view.setStyleSheet(f"QTextBrowser {{ background: {self.T['bg']}; border: 1px solid {self.T['border']}; "
                           f"border-radius: 10px; padding: 8px; }}")
        view.setHtml(html)
        lay.addWidget(view, 1)
        ok = AButton("Tamam")
        ok.setObjectName("qzprimary")
        ok.setFixedHeight(36)
        ok.clicked.connect(dlg.accept)
        lay.addWidget(ok)
        dlg.exec()

    # ---------- ayarlar ----------
    def show_settings(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(f"{APP} - Ayarlar")
        dlg.resize(440, 420)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 18, 20, 16)
        lay.setSpacing(10)
        t = QLabel("Ayarlar")
        t.setObjectName("qzbig")
        lay.addWidget(t)
        g = QGridLayout()
        g.setVerticalSpacing(10)
        theme = QComboBox()
        for th in E.THEME_LIST:
            if self.theme_ok(th["name"]):
                theme.addItem(th["name"])
        theme.setCurrentText(self.theme_name)
        font = QFontComboBox()
        font.setCurrentFont(QFont(self.base_family))
        size = QSpinBox()
        size.setRange(6, 72)
        size.setValue(self.base_size)
        goal = QSpinBox()
        goal.setRange(0, 1_000_000)
        goal.setValue(int(self.cfg.get("goal", 0)))
        for i, (lab, w) in enumerate((("Tema", theme), ("Varsayılan yazı tipi", font), ("Varsayılan boyut", size),
                                      ("Kelime hedefi (0: kapalı)", goal))):
            g.addWidget(QLabel(lab), i, 0)
            g.addWidget(w, i, 1)
        lay.addLayout(g)
        follow = QCheckBox("Sistemin açık/koyu temasını takip et")
        follow.setChecked(bool(self.cfg.get("theme_follow", False)))
        home = QCheckBox("Açılışta başlangıç ekranını göster")
        home.setChecked(self.home_on)
        wrap = QCheckBox("Sözcük kaydır")
        wrap.setChecked(self.cfg.get("wrap", True))
        status = QCheckBox("Durum çubuğunu göster")
        status.setChecked(self.cfg.get("status", True))
        for c in (follow, home, wrap, status):
            lay.addWidget(c)
        lay.addStretch(1)
        row = QHBoxLayout()
        row.addStretch(1)
        ok = AButton("Kaydet")
        ok.setObjectName("qzprimary")
        ok.setFixedHeight(34)
        cancel = AButton("Vazgeç")
        cancel.setObjectName("qzfield")
        cancel.setFixedHeight(34)
        ok.clicked.connect(dlg.accept)
        cancel.clicked.connect(dlg.reject)
        row.addWidget(ok)
        row.addWidget(cancel)
        lay.addLayout(row)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self.cfg["theme_follow"] = follow.isChecked()
        self.cfg["goal"] = goal.value()
        self.home_on = home.isChecked()
        self.toggle_status(status.isChecked())
        self.toggle_wrap(wrap.isChecked())
        self.base_family, self.base_size = font.currentFont().family(), size.value()
        for ed in self.all_editors():
            ed.apply_base(self.base_family, self.base_size)
        if theme.currentText() != self.theme_name:
            self.apply_theme(theme.currentText(), save=False)
        self.save_settings()
        self.sync_toolbar()
        self.update_pos()
        if follow.isChecked():
            self.follow_system_theme()

    # ---------- sistem teması ----------
    def follow_system_theme(self, *_):
        if not self.cfg.get("theme_follow"):
            return
        try:
            dark = QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
        except AttributeError:
            return
        name = "Siyah" if dark else "Beyaz"
        if name != self.theme_name and self.theme_ok(name):
            self.apply_theme(name)

    def watch_system_theme(self):
        try:
            QGuiApplication.styleHints().colorSchemeChanged.connect(self.follow_system_theme)
        except AttributeError:
            pass

    # ---------- güncelleme denetimi ----------
    def check_updates(self):
        url = self.cfg.get("update_url", "")
        if not url:
            self.info(f"Güncelleme adresi ayarlı değil.\n\nSürüm {VERSION}. Adres vermek için settings.json içine "
                      "\"update_url\" ekleyin (JSON: version, url, notes).")
            return
        self.toast("Güncellemeler denetleniyor…")
        res = {}

        def work():
            try:
                req = urllib.request.Request(url, headers={"User-Agent": f"qaZNot/{VERSION}"})
                with urllib.request.urlopen(req, timeout=10) as r:
                    res["data"] = json.loads(r.read(200_000).decode("utf-8"))
            except Exception as e:  # noqa: BLE001
                res["err"] = str(e)
        th = threading.Thread(target=work, daemon=True)
        th.start()
        t = QTimer(self)

        def poll():
            if th.is_alive():
                return
            t.stop()
            if "err" in res:
                self.error(f"Güncelleme denetlenemedi:\n{res['err']}")
                return
            d = res.get("data", {})
            newer = version_number(str(d.get("version", "0"))) > version_number()
            if newer:
                from PySide6.QtWidgets import QMessageBox
                r = QMessageBox.question(self, APP, f"Yeni sürüm var: {d.get('version')}\n{d.get('notes', '')}\n\nİndirme sayfası açılsın mı?")
                if r == QMessageBox.StandardButton.Yes and d.get("url"):
                    webbrowser.open(d["url"])
            else:
                self.info(f"Güncelsiniz (sürüm {VERSION}).")
        t.timeout.connect(poll)
        t.start(200)

    # ---------- yedekleme ----------
    def backup_dialog(self):
        import qz_backup
        from datetime import datetime as _dt
        default = os.path.join(self.default_dir(), f"qaZNot-yedek-{_dt.now():%Y%m%d-%H%M}.zip")
        path, _ = QFileDialog.getSaveFileName(self, "Yedek oluştur", default, "qaZNot yedeği (*.zip)")
        if not path:
            return False
        if not path.lower().endswith(".zip"):
            path += ".zip"
        pins, rec = self.home_entries()
        docs = list(dict.fromkeys(pins + rec))
        try:
            n, skipped = qz_backup.make_backup(path, docs, os.path.join(E.DATA_DIR, "versions"))
        except OSError as e:
            self.error(f"Yedek oluşturulamadı:\n{e}")
            return False
        msg = f"Yedek oluşturuldu: {n} belge"
        if skipped:
            msg += f" ({skipped} belge bulunamadığı için atlandı)"
        self.toast(msg)
        return True

    def restore_backup_dialog(self):
        import qz_backup
        path, _ = QFileDialog.getOpenFileName(self, "Yedekten geri yükle", "", "qaZNot yedeği (*.zip)")
        if not path:
            return False
        if qz_backup.read_manifest(path) is None:
            self.error("Bu dosya bir qaZNot yedeği değil.")
            return False
        docs_dir = os.path.join(self.default_dir(), "qaZNot Geri Yüklenen")
        try:
            n = qz_backup.restore_backup(path, docs_dir, os.path.join(E.DATA_DIR, "versions"))
        except (OSError, ValueError) as e:
            self.error(f"Geri yüklenemedi:\n{e}")
            return False
        self.toast(f"{n} belge çıkarıldı: qaZNot Geri Yüklenen klasörü")
        return True

    # ---------- hata kaydı ----------
    @staticmethod
    def crash_log_path():
        return os.path.join(E.DATA_DIR, "crash.log")

    def install_crash_log(self):
        old = sys.excepthook

        def hook(et, ev, tb):
            try:
                with open(self.crash_log_path(), "a", encoding="utf-8") as f:
                    f.write(f"\n=== {datetime.now().isoformat(timespec='seconds')} · qaZNot {VERSION} ===\n")
                    f.write("".join(traceback.format_exception(et, ev, tb)))
                self.toast("Beklenmeyen bir hata oluştu ve kaydedildi (Yardım > Hata Kaydını Aç)")
            except Exception:  # noqa: BLE001
                pass
            old(et, ev, tb)
        sys.excepthook = hook

    def open_crash_log(self):
        p = self.crash_log_path()
        if not os.path.exists(p):
            self.info("Hata kaydı yok. Her şey yolunda görünüyor.")
            return
        try:
            os.startfile(p)  # noqa: S606
        except (OSError, AttributeError):
            self.info(p)
