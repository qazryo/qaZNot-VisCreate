"""qaZNot ana pencere arayüzü: menüler, araç çubuğu, bul/değiştir çubuğu, durum çubuğu, bildirim."""
import os

from PySide6.QtCore import Qt, QSize, QTimer, QPoint, QPropertyAnimation, QEasingCurve, QEvent
from PySide6.QtGui import QAction, QKeySequence, QIcon, QPixmap, QPainter, QColor, QFont, QPen
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QMenuBar, QMenu, QWidget,
                               QButtonGroup, QGraphicsOpacityEffect, QInputDialog)

import qv_engine as E
import qz_assoc as assoc
from qv_widgets import AButton, ATool
from qz_style import qz_icon
from qz_popups import FontPicker, ColorPopup, ThemePopup

SIZES = E.SIZES


def text_icon(txt, color, bar=None, size=22, bold=True, italic=False):
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    f = QFont("Segoe UI")
    f.setPixelSize(14)
    f.setBold(bold)
    f.setItalic(italic)
    p.setFont(f)
    p.setPen(QColor(color))
    p.drawText(pm.rect().adjusted(0, -2, 0, -3), Qt.AlignmentFlag.AlignCenter, txt)
    if bar:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(bar))
        p.drawRoundedRect(4, size - 6, size - 8, 3, 1.5, 1.5)
    p.end()
    return QIcon(pm)


class UIMixin:
    # ---------- menü yardımcıları ----------
    def act(self, menu, text, fn, shortcut=None, accel=None, checkable=False, checked=False):
        a = QAction(text + (f"\t{accel}" if accel else ""), self)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
            a.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        a.setCheckable(checkable)
        if checkable:
            a.setChecked(checked)
            a.toggled.connect(lambda c: fn(c))
        else:
            a.triggered.connect(lambda *_: fn())
        menu.addAction(a)
        return a

    def _build_menus(self, mb):
        m = mb.addMenu("Dosya")
        self.act(m, "Başlangıç Ekranı", self.show_home, "Ctrl+Shift+H", "Ctrl+Shift+H")
        m.addSeparator()
        self.act(m, "Yeni Sekme", self.new_file, "Ctrl+N", "Ctrl+N")
        self.act(m, "Yeni Pencere", self.new_window, "Ctrl+Shift+N", "Ctrl+Shift+N")
        self.act(m, "Sekmeyi Kapat", self.close_current_tab, "Ctrl+W", "Ctrl+W")
        self.act(m, "Sonraki Sekme", lambda: self.next_tab(1), "Ctrl+Tab", "Ctrl+Tab")
        self.act(m, "Önceki Sekme", lambda: self.next_tab(-1), "Ctrl+Shift+Tab", "Ctrl+Shift+Tab")
        self.act(m, "Aç...", self.open_dialog, "Ctrl+O", "Ctrl+O")
        self.act(m, "Kaydet", self.save, "Ctrl+S", "Ctrl+S")
        self.act(m, "Farklı Kaydet...", self.save_as, "Ctrl+Shift+S", "Ctrl+Shift+S")
        m.addSeparator()
        self.act(m, "qAnvas (tasarım)...", self.open_qanvas)
        m.addSeparator()
        self.act(m, "Belgeyi İmzala... (Professional)", self.sign_document)
        self.act(m, "İmzayı Doğrula...", self.verify_document)
        m.addSeparator()
        self.recent_menu = m.addMenu("Son Kullanılanlar")
        m.aboutToShow.connect(self.fill_recent)
        self.act(m, "Şifre Ayarla / Değiştir...", self.set_password)
        self.act(m, "Şifreyi Kaldır", self.remove_password)
        self.act(m, "Belge Geçmişi...", self.show_history)
        self.act(m, "Yedek Oluştur...", self.backup_dialog)
        self.act(m, "Yedekten Geri Yükle...", self.restore_backup_dialog)
        m.addSeparator()
        self.act(m, "PDF Olarak Dışa Aktar...", self.export_pdf)
        self.act(m, "HTML Olarak Dışa Aktar...", self.export_html)
        self.act(m, "Yazdır...", self.print_file, "Ctrl+P", "Ctrl+P")
        m.addSeparator()
        self.act(m, "Çıkış", self.close)

        m = mb.addMenu("Düzenle")
        self.act(m, "Geri Al", lambda: self.editor.undo(), accel="Ctrl+Z")
        self.act(m, "Yinele", lambda: self.editor.redo(), accel="Ctrl+Y")
        m.addSeparator()
        self.act(m, "Kes", lambda: self.editor.cut(), accel="Ctrl+X")
        self.act(m, "Kopyala", lambda: self.editor.copy(), accel="Ctrl+C")
        self.act(m, "Yapıştır", lambda: self.editor.paste(), accel="Ctrl+V")
        self.act(m, "Sil", lambda: self.editor.delete_selection(), accel="Del")
        m.addSeparator()
        self.act(m, "Bul...", lambda: self.show_find(False), "Ctrl+F", "Ctrl+F")
        self.act(m, "Sonrakini Bul", lambda: self.find_go(False), "F3", "F3")
        self.act(m, "Öncekini Bul", lambda: self.find_go(True), "Shift+F3", "Shift+F3")
        self.act(m, "Değiştir...", lambda: self.show_find(True), "Ctrl+H", "Ctrl+H")
        m.addSeparator()
        self.act(m, "Satıra Git...", self.goto_line, "Ctrl+G", "Ctrl+G")
        self.act(m, "Tümünü Seç", lambda: self.editor.selectAll(), accel="Ctrl+A")
        self.act(m, "Saat/Tarih", self.insert_datetime, "F5", "F5")
        self.act(m, "Resim Ekle...", self.insert_image_dialog, "Ctrl+Shift+I", "Ctrl+Shift+I")

        m = mb.addMenu("Biçim")
        self.act(m, "Kalın", lambda: self.on_toggle("bold"), "Ctrl+B", "Ctrl+B")
        self.act(m, "İtalik", lambda: self.on_toggle("italic"), "Ctrl+I", "Ctrl+I")
        self.act(m, "Altı Çizili", lambda: self.on_toggle("underline"), "Ctrl+U", "Ctrl+U")
        self.act(m, "Üstü Çizili", lambda: self.on_toggle("overstrike"), "Ctrl+Shift+X", "Ctrl+Shift+X")
        m.addSeparator()
        self.act(m, "Yazı Tipi...", self.open_font_picker, "Ctrl+D", "Ctrl+D")
        self.act(m, "Yazı Rengi...", self.open_fg_popup)
        self.act(m, "Vurgu Rengi...", self.open_bg_popup)
        self.act(m, "Bu yazı tipini varsayılan yap", self.set_default_font)
        m.addSeparator()
        self.act(m, "Sola Hizala", lambda: self.on_align("left"), "Ctrl+L", "Ctrl+L")
        self.act(m, "Ortala", lambda: self.on_align("center"), "Ctrl+E", "Ctrl+E")
        self.act(m, "Sağa Hizala", lambda: self.on_align("right"), "Ctrl+R", "Ctrl+R")
        m.addSeparator()
        self.act(m, "Madde İşaretli Liste", lambda: self.on_list("disc"), "Ctrl+Shift+8", "Ctrl+Shift+8")
        self.act(m, "Numaralı Liste", lambda: self.on_list("decimal"), "Ctrl+Shift+7", "Ctrl+Shift+7")
        self.act(m, "Girintiyi Artır", lambda: self.on_indent(1), "Ctrl+]", "Ctrl+]")
        self.act(m, "Girintiyi Azalt", lambda: self.on_indent(-1), "Ctrl+[", "Ctrl+[")
        sm = m.addMenu("Satır Aralığı")
        for pct, label in ((100, "1,0"), (115, "1,15"), (150, "1,5"), (200, "2,0")):
            self.act(sm, label, lambda p=pct: self.on_spacing(p))
        m.addSeparator()
        self.act(m, "Biçimi Temizle", self.clear_format)
        m.addSeparator()
        self.act(m, "Sözcük Kaydır", self.toggle_wrap, checkable=True, checked=self.cfg.get("wrap", True))

        m = mb.addMenu("Görünüm")
        self.act(m, "Tema Seç...", self.open_theme_popup, "Ctrl+T", "Ctrl+T")
        self.act(m, "Sonraki Tema", self.next_theme, "F6", "F6")
        m.addSeparator()
        zm = m.addMenu("Yakınlaştır")
        self.act(zm, "Yakınlaştır", lambda: self.change_zoom(10), "Ctrl++", "Ctrl+Artı")
        self.act(zm, "Yakınlaştır (=)", lambda: self.change_zoom(10), "Ctrl+=")
        self.act(zm, "Uzaklaştır", lambda: self.change_zoom(-10), "Ctrl+-", "Ctrl+Eksi")
        self.act(zm, "Varsayılan", lambda: self.change_zoom(0, True), "Ctrl+0", "Ctrl+0")
        self.act(m, "Durum Çubuğu", self.toggle_status, checkable=True, checked=self.cfg.get("status", True))
        self.act(m, "Odak Modu", self.toggle_focus, "F11", "F11")
        self.act(m, "Ayarlar...", self.show_settings, "Ctrl+,", "Ctrl+,")
        self.act(m, "Kelime Hedefi...", self.set_goal)

        m = mb.addMenu("Yardım")
        self.act(m, "Hesabım...", self.open_account)
        m.addSeparator()
        self.a_dv = self.act(m, "Discord'da göster", lambda c: self.set_discord(on=c), checkable=True, checked=self.discord_on)
        self.a_df = self.act(m, "Discord'da dosya adını göster", lambda c: self.set_discord(file=c), checkable=True,
                             checked=self.discord_file)
        m.addSeparator()
        self.a_assoc = self.act(m, ".qaz dosyalarını qaZNot ile aç", self.toggle_assoc, checkable=True,
                                checked=assoc.is_registered())
        m.addSeparator()
        self.act(m, "Klavye Kısayolları...", self.show_shortcuts)
        self.act(m, "Güncellemeleri Denetle...", self.check_updates)
        self.act(m, "Hata Kaydını Aç", self.open_crash_log)
        m.addSeparator()
        self.act(m, "Sürüm Geçmişi...", self.show_versions)
        self.act(m, "Hakkında", self.about)

    def fill_recent(self):
        m = self.recent_menu
        m.clear()
        files = [p for p in self.cfg.get("recent_files", []) if os.path.isfile(p)][:10]
        if not files:
            m.addAction("(boş)").setEnabled(False)
        for p in files:
            m.addAction(f"{os.path.basename(p)}   —   {os.path.dirname(p)[-40:]}", lambda p=p: self.open_recent(p))

    # ---------- üst çubuk ----------
    def _build_top(self):
        bar = QFrame()
        bar.setObjectName("qztop")
        bar.setFixedHeight(40)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(8, 0, 10, 0)
        mb = QMenuBar()
        self._build_menus(mb)
        lay.addWidget(mb)
        lay.addStretch(1)
        self.doc_label = QLabel("")
        self.doc_label.setObjectName("qzdoc")
        lay.addWidget(self.doc_label)
        lay.addSpacing(8)
        self.acc_btn = AButton("")
        self.acc_btn.setObjectName("qzfield")
        self.acc_btn.setFixedHeight(28)
        self.acc_btn.setToolTip("Hesabım")
        self.acc_btn.clicked.connect(lambda: self.open_account())
        lay.addWidget(self.acc_btn)
        self.menubar = mb
        return bar

    # ---------- araç çubuğu ----------
    def _tb(self, tip, fn, checkable=False, w=32):
        b = ATool()
        b.setObjectName("qz")
        b.setToolTip(tip)
        b.setFixedSize(w, 30)
        b.setIconSize(QSize(22, 22))
        b.setCheckable(checkable)
        b.clicked.connect(lambda *_: fn())
        return b

    def _sep(self, lay):
        s = QFrame()
        s.setObjectName("qzsep")
        s.setFixedHeight(20)
        lay.addSpacing(4)
        lay.addWidget(s)
        lay.addSpacing(4)

    def _build_toolbar(self):
        bar = QFrame()
        bar.setObjectName("qztool")
        bar.setFixedHeight(44)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.setSpacing(2)
        self.font_btn = AButton("")
        self.font_btn.setObjectName("qzfield")
        self.font_btn.setFixedSize(190, 30)
        self.font_btn.setToolTip("Yazı tipi (Ctrl+D)")
        self.font_btn.clicked.connect(lambda: self.open_font_picker())
        lay.addWidget(self.font_btn)
        lay.addSpacing(6)
        self.b_minus = self._tb("Küçült", lambda: self.step_size(-1))
        self.b_minus.setIcon(qz_icon("minus", "#888"))
        lay.addWidget(self.b_minus)
        self.size_edit = QLineEdit()
        self.size_edit.setObjectName("qzentry")
        self.size_edit.setFixedSize(46, 28)
        self.size_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.size_edit.returnPressed.connect(self.on_size_enter)
        self.size_edit.installEventFilter(self)
        lay.addWidget(self.size_edit)
        self.b_plus = self._tb("Büyüt", lambda: self.step_size(1))
        lay.addWidget(self.b_plus)
        self._sep(lay)
        self.sty = {}
        for key, ttl, tip, kw in (("bold", "B", "Kalın (Ctrl+B)", {}), ("italic", "I", "İtalik (Ctrl+I)", dict(italic=True)),
                                  ("underline", "U", "Altı çizili (Ctrl+U)", {}), ("overstrike", "S", "Üstü çizili (Ctrl+Shift+X)", {})):
            b = self._tb(tip, lambda k=key: self.on_toggle(k), True)
            b.setProperty("ttl", ttl)
            b.setProperty("kw", kw)
            self.sty[key] = b
            lay.addWidget(b)
        self._sep(lay)
        self.b_fg = self._tb("Yazı rengi", lambda: self.open_fg_popup())
        self.b_bg = self._tb("Vurgu rengi", lambda: self.open_bg_popup())
        lay.addWidget(self.b_fg)
        lay.addWidget(self.b_bg)
        self._sep(lay)
        self.al_group = QButtonGroup(self)
        self.al_btns = {}
        for a, ic, tip in (("left", "tx_l", "Sola hizala (Ctrl+L)"), ("center", "tx_c", "Ortala (Ctrl+E)"),
                           ("right", "tx_r", "Sağa hizala (Ctrl+R)")):
            b = self._tb(tip, lambda a=a: self.on_align(a), True)
            b.setProperty("ic", ic)
            self.al_btns[a] = b
            lay.addWidget(b)
        self._sep(lay)
        self.b_bul = self._tb("Madde işaretli liste (Ctrl+Shift+8)", lambda: self.on_list("disc"), True)
        self.b_num = self._tb("Numaralı liste (Ctrl+Shift+7)", lambda: self.on_list("decimal"), True)
        self.b_ind = self._tb("Girintiyi artır (Ctrl+])", lambda: self.on_indent(1))
        self.b_out = self._tb("Girintiyi azalt (Ctrl+[)", lambda: self.on_indent(-1))
        self.b_ls = self._tb("Satır aralığı", lambda: self.open_spacing_menu())
        for b in (self.b_bul, self.b_num, self.b_ind, self.b_out, self.b_ls):
            lay.addWidget(b)
        self._sep(lay)
        self.b_img = self._tb("Resim ekle", lambda: self.insert_image_dialog())
        lay.addWidget(self.b_img)
        self.b_clear = self._tb("Seçili metnin biçimini temizle", lambda: self.clear_format())
        lay.addWidget(self.b_clear)
        lay.addStretch(1)
        self.b_theme = self._tb("Tema (Ctrl+T)", lambda: self.open_theme_popup())
        lay.addWidget(self.b_theme)
        return bar

    def refresh_icons(self):
        T = self.T
        fg, mu = T["fg"], T["muted"]
        self.b_minus.setIcon(qz_icon("minus", fg))
        self.b_plus.setIcon(qz_icon("plus", fg))
        for key, b in self.sty.items():
            kw = b.property("kw") or {}
            b.setIcon(text_icon(b.property("ttl"), fg, italic=bool(kw.get("italic"))))
        for a, b in self.al_btns.items():
            b.setIcon(qz_icon(b.property("ic"), fg))
        self.b_clear.setIcon(qz_icon("clearfmt", fg))
        for b, k in ((self.b_bul, "bullets"), (self.b_num, "numbers"), (self.b_ind, "indent"), (self.b_out, "outdent"),
                     (self.b_ls, "linespace"), (self.b_img, "image")):
            b.setIcon(qz_icon(k, fg))
        self.b_theme.setIcon(qz_icon("palette", fg))
        self.b_newtab.setIcon(qz_icon("plus", fg))
        self.f_toggle.setIcon(qz_icon("chev_r", fg))
        self.f_prev.setIcon(qz_icon("up", fg))
        self.f_next.setIcon(qz_icon("chev", fg))
        self.f_close.setIcon(qz_icon("close", fg))
        self.sync_toolbar()

    def sync_toolbar(self):
        if self.cur_doc is None:
            return
        st = self.editor.style()
        fam = st["family"]
        self.font_btn.setText(f"{fam}  ▾")
        sz = st["size"]
        if not self.size_edit.hasFocus():
            self.size_edit.setText(str(int(sz)) if float(sz) == int(sz) else f"{sz:g}")
        for k, b in self.sty.items():
            b.setChecked(bool(st[k]))
        for a, b in self.al_btns.items():
            b.setChecked(st["align"] == a)
        self.b_bul.setChecked(st["list"] == "disc")
        self.b_num.setChecked(st["list"] == "decimal")
        T = self.T
        self.b_fg.setIcon(text_icon("A", T["fg"], bar=st["fg"] or T["fg"]))
        self.b_bg.setIcon(text_icon("ab", T["fg"], bar=st["bg"] or T["border"], bold=False))

    def eventFilter(self, obj, ev):
        if obj is getattr(self, "size_edit", None) and ev.type() == QEvent.Type.KeyPress:
            if ev.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                self.step_size(1 if ev.key() == Qt.Key.Key_Up else -1)
                return True
        return super().eventFilter(obj, ev)

    def _build_tabrow(self):
        bar = QFrame()
        bar.setObjectName("qztabrow")
        bar.setFixedHeight(38)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.setSpacing(2)
        lay.addWidget(self._build_tabbar())
        self.b_newtab = self._tb("Yeni sekme (Ctrl+N)", lambda: self.new_file(), w=28)
        lay.addWidget(self.b_newtab)
        lay.addStretch(1)
        return bar

    # ---------- bul / değiştir çubuğu ----------
    def _build_findbar(self):
        bar = QFrame()
        bar.setObjectName("qzfind")
        v = QVBoxLayout(bar)
        v.setContentsMargins(12, 6, 12, 6)
        v.setSpacing(6)
        r1 = QHBoxLayout()
        r1.setSpacing(4)
        self.f_toggle = self._tb("Değiştir satırını aç/kapat", lambda: self.toggle_replace(), w=28)
        r1.addWidget(self.f_toggle)
        self.f_entry = QLineEdit()
        self.f_entry.setObjectName("qzentry")
        self.f_entry.setPlaceholderText("Bul…")
        self.f_entry.setMinimumWidth(240)
        self.f_entry.textChanged.connect(self.on_find_type)
        self.f_entry.returnPressed.connect(lambda: self.find_go(False))
        r1.addWidget(self.f_entry)
        self.f_case = self._tb("Büyük/küçük harf eşleştir", lambda: self.on_find_type(), True, 34)
        self.f_case.setText("Aa")
        r1.addWidget(self.f_case)
        self.f_word = self._tb("Tam sözcük", lambda: self.on_find_type(), True, 34)
        self.f_word.setText("Söz")
        r1.addWidget(self.f_word)
        self.f_regex = self._tb("Düzenli ifade (regex)", lambda: self.on_find_type(), True, 34)
        self.f_regex.setText(".*")
        r1.addWidget(self.f_regex)
        self.f_prev = self._tb("Önceki (Shift+F3)", lambda: self.find_go(True), w=28)
        self.f_next = self._tb("Sonraki (F3)", lambda: self.find_go(False), w=28)
        r1.addWidget(self.f_prev)
        r1.addWidget(self.f_next)
        self.f_count = QLabel("")
        self.f_count.setObjectName("qzmuted")
        self.f_count.setMinimumWidth(80)
        r1.addWidget(self.f_count)
        r1.addStretch(1)
        self.f_close = self._tb("Kapat (Esc)", lambda: self.hide_find(), w=28)
        r1.addWidget(self.f_close)
        v.addLayout(r1)
        self.r2 = QWidget()
        r2 = QHBoxLayout(self.r2)
        r2.setContentsMargins(32, 0, 0, 0)
        r2.setSpacing(6)
        self.r_entry = QLineEdit()
        self.r_entry.setObjectName("qzentry")
        self.r_entry.setPlaceholderText("Şununla değiştir…")
        self.r_entry.setMinimumWidth(240)
        r2.addWidget(self.r_entry)
        b1 = AButton("Değiştir")
        b1.setObjectName("qzfield")
        b1.setFixedHeight(28)
        b1.clicked.connect(lambda: self.replace_one())
        b2 = AButton("Tümünü Değiştir")
        b2.setObjectName("qzfield")
        b2.setFixedHeight(28)
        b2.clicked.connect(lambda: self.replace_all())
        r2.addWidget(b1)
        r2.addWidget(b2)
        r2.addStretch(1)
        v.addWidget(self.r2)
        self.r2.hide()
        bar.hide()
        return bar

    # ---------- durum çubuğu ----------
    def _build_status(self):
        bar = QFrame()
        bar.setObjectName("qzstatus")
        bar.setFixedHeight(26)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 0, 14, 0)
        self.lbl_pos = QLabel("Satır 1, Sütun 1")
        self.lbl_count = QLabel("0 kelime · 0 karakter")
        self.lbl_goal = QLabel("")
        self.lbl_kind = QLabel("UTF-8")
        self.lbl_zoom = QLabel("%100")
        self.lbl_zoom.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_zoom.mouseReleaseEvent = lambda e: self.change_zoom(0, True)
        for w in (self.lbl_pos, self.lbl_count, self.lbl_goal, self.lbl_kind, self.lbl_zoom):
            w.setObjectName("qzstat")
        lay.addWidget(self.lbl_pos)
        lay.addSpacing(16)
        lay.addWidget(self.lbl_count)
        lay.addSpacing(16)
        lay.addWidget(self.lbl_goal)
        lay.addStretch(1)
        lay.addWidget(self.lbl_zoom)
        lay.addSpacing(16)
        lay.addWidget(self.lbl_kind)
        return bar

    # ---------- bildirim ----------
    def toast(self, msg):
        t = getattr(self, "_toast", None)
        if t is None:
            t = QLabel(self.centralWidget())
            t.setObjectName("qztoast")
            t.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._toast = t
            self._toast_timer = QTimer(self)
            self._toast_timer.setSingleShot(True)
            self._toast_timer.timeout.connect(self._toast_out)
            self._toast_anims = []
        t.setText(msg)
        t.adjustSize()
        t.resize(t.width() + 4, 34)
        cw = self.centralWidget()
        x, y = (cw.width() - t.width()) // 2, cw.height() - 90
        eff = QGraphicsOpacityEffect(t)
        t.setGraphicsEffect(eff)
        t.move(x, y + 30)
        t.show()
        t.raise_()
        a1 = QPropertyAnimation(t, b"pos", t)
        a1.setDuration(260)
        a1.setStartValue(QPoint(x, y + 30))
        a1.setEndValue(QPoint(x, y))
        a1.setEasingCurve(QEasingCurve.Type.OutCubic)
        a2 = QPropertyAnimation(eff, b"opacity", t)
        a2.setDuration(260)
        a2.setStartValue(0.0)
        a2.setEndValue(1.0)
        self._toast_anims = [a1, a2]
        a1.start()
        a2.start()
        self._toast_timer.start(2300)

    def _toast_out(self):
        t = self._toast
        eff = t.graphicsEffect()
        if eff is None:
            return
        a = QPropertyAnimation(eff, b"opacity", t)
        a.setDuration(260)
        a.setStartValue(1.0)
        a.setEndValue(0.0)
        a.finished.connect(t.hide)
        self._toast_anims = [a]
        a.start()
