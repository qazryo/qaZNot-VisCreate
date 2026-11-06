"""Arayuz parcalari (ust cubuk, arac cubugu, yukleme paneli, sag panel). MainWindow'a karisir."""
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (QApplication, QFrame, QLabel, QHBoxLayout, QVBoxLayout, QButtonGroup,
                               QDoubleSpinBox, QPushButton, QListWidget, QGridLayout, QPlainTextEdit, QComboBox,
                               QWidget, QStyledItemDelegate, QStyle, QStyleOptionViewItem, QStyleOptionComboBox,
                               QStylePainter)

import qv_engine as E
from qv_widgets import AButton, ATool
from qv_items import pil_to_qimage
from qv_theme import make_icon


_PREVIEWS = {}


def font_preview(family, h=22, color="#E6E6E6"):
    """Yazı tipi adını o yazı tipinin kendisiyle çizilmiş küçük resim olarak döndürür (motorun çizimiyle aynı)."""
    key = (family, color)
    pm = _PREVIEWS.get(key)
    if pm is None:
        try:
            from PIL import Image, ImageDraw
            f, fake = E.qv_font2(family, 17)
            ma, mb = f.getmask("Aa"), f.getmask("\U0010ffff\U0010ffff")
            if ma.size == mb.size and bytes(ma) == bytes(mb):
                raise ValueError("Latin harf yok")  # yalnızca başka alfabeyi destekleyen yazı tipi
            col = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
            w = int(f.getlength(family)) + 6
            im = Image.new("RGBA", (max(w, 8), h), col + (0,))
            kw = dict(stroke_width=1, stroke_fill=color) if fake else {}
            ImageDraw.Draw(im).text((2, h // 2), family, font=f, fill=color, anchor="lm", **kw)
            pm = QPixmap.fromImage(pil_to_qimage(im))
        except Exception:  # noqa: BLE001
            pm = False
        if len(_PREVIEWS) > 600:
            _PREVIEWS.clear()
        _PREVIEWS[key] = pm
    return pm


class FontDelegate(QStyledItemDelegate):
    def sizeHint(self, opt, idx):
        s = super().sizeHint(opt, idx)
        return QSize(s.width(), 30)

    def paint(self, p, opt, idx):
        o = QStyleOptionViewItem(opt)
        self.initStyleOption(o, idx)
        name = idx.data(Qt.ItemDataRole.DisplayRole)
        o.text = ""
        QApplication.style().drawControl(QStyle.ControlElement.CE_ItemViewItem, o, p, o.widget)
        pm = font_preview(name) if idx.data(Qt.ItemDataRole.UserRole) == "local" else None
        if pm:
            p.drawPixmap(o.rect.left() + 8, o.rect.center().y() - pm.height() // 2 + 1, pm)
        else:
            p.setPen(QColor("#8C8C8C"))
            p.drawText(o.rect.adjusted(8, 0, -4, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, name)


class FontCombo(QComboBox):
    """Kapalıyken de seçili yazı tipini kendi görünüşüyle gösterir."""

    def __init__(self):
        super().__init__()
        self.setItemDelegate(FontDelegate(self))

    def paintEvent(self, e):
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        name = opt.currentText
        opt.currentText = ""
        p = QStylePainter(self)
        p.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, opt)
        r = self.style().subControlRect(QStyle.ComplexControl.CC_ComboBox, opt,
                                        QStyle.SubControl.SC_ComboBoxEditField, self)
        pm = font_preview(name) if self.currentData() == "local" else None
        if pm:
            p.drawPixmap(r.left() + 4, r.center().y() - pm.height() // 2 + 1, pm)
        else:
            p.drawText(r.adjusted(4, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, name)


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


def section(text):
    s = QLabel(text)
    s.setObjectName("sec")
    return s


def sep():
    f = QFrame()
    f.setObjectName("sep")
    return f


def icon_btn(icon, tip, size=28, checkable=False):
    b = ATool()
    b.setIcon(make_icon(icon))
    b.setIconSize(QSize(20, 20))
    b.setFixedSize(size, size)
    b.setToolTip(tip)
    b.setCheckable(checkable)
    return b


def swatch():
    b = QPushButton()
    b.setObjectName("swatch")
    return b


class PanelsMixin:
    def _build_topbar(self):
        bar = QFrame()
        bar.setObjectName("topbar")
        bar.setFixedHeight(46)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 0, 12, 0)
        lay.setSpacing(4)
        logo = QLabel("qAnvas")
        logo.setObjectName("logo")
        lay.addWidget(logo)
        lay.addSpacing(6)
        nb = AButton("qaZNot")
        nb.setObjectName("flat")
        nb.setToolTip("Not defterini (qaZNot) aç")
        nb.clicked.connect(self.open_notepad)
        lay.addWidget(nb)
        lay.addSpacing(6)
        for txt, fn in (("Yeni", self.new_doc_dialog), ("Aç", self.open_file), ("Kaydet", self.save)):
            b = AButton(txt)
            b.setObjectName("flat")
            b.clicked.connect(fn)
            lay.addWidget(b)
        lay.addSpacing(8)
        self.btn_undo = icon_btn("undo", "Geri al (Ctrl+Z)")
        self.btn_undo.clicked.connect(self.undo)
        self.btn_redo = icon_btn("redo", "Yinele (Ctrl+Y)")
        self.btn_redo.clicked.connect(self.redo)
        lay.addWidget(self.btn_undo)
        lay.addWidget(self.btn_redo)
        lay.addSpacing(10)
        self.title_btn = AButton("Adsız tasarım")
        self.title_btn.setObjectName("flat")
        self.title_btn.setToolTip("Adı değiştir")
        self.title_btn.clicked.connect(self.rename_doc)
        lay.addWidget(self.title_btn)
        lay.addStretch(1)
        self.toast_lbl = QLabel("")
        self.toast_lbl.setObjectName("toast")
        lay.addWidget(self.toast_lbl)
        lay.addSpacing(10)
        b = ATool()
        b.setText("−")
        b.setFixedSize(28, 28)
        b.clicked.connect(lambda: self.view.zoom_by(1 / 1.25, False))
        lay.addWidget(b)
        self.zoom_lbl = QLabel("100%")
        self.zoom_lbl.setFixedWidth(46)
        self.zoom_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.zoom_lbl)
        b = ATool()
        b.setText("+")
        b.setFixedSize(28, 28)
        b.clicked.connect(lambda: self.view.zoom_by(1.25, False))
        lay.addWidget(b)
        fit = AButton("Sığdır")
        fit.clicked.connect(lambda: self.view.fit())
        lay.addWidget(fit)
        lay.addSpacing(10)
        exp = AButton("Dışa aktar")
        exp.setObjectName("accent")
        exp.setToolTip("Tasarımı PNG / JPEG fotoğraf olarak kaydet (Ctrl+E)")
        exp.clicked.connect(self.export_image)
        lay.addWidget(exp)
        self.acc_btn = AButton("")
        self.acc_btn.setObjectName("account")
        self.acc_btn.setIconSize(QSize(28, 28))
        self.acc_btn.clicked.connect(self.open_account)
        lay.addWidget(self.acc_btn)
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
        for key, tip in (("select", "Seç (V)"), ("rect", "Dikdörtgen (R)"), ("ellipse", "Elips (O)"),
                         ("line", "Çizgi (L)"), ("text", "Metin (T)")):
            b = icon_btn(key, tip, 36, True)
            b.setIconSize(QSize(22, 22))
            b.clicked.connect(lambda _=False, k=key: self.set_tool(k))
            self.tool_group.addButton(b)
            self.tool_btns[key] = b
            lay.addWidget(b)
        self.tool_btns["select"].setChecked(True)
        lay.addSpacing(6)
        self.btn_uploads = icon_btn("image", "Yüklemeler (I)", 36, True)
        self.btn_uploads.setIconSize(QSize(22, 22))
        self.btn_uploads.clicked.connect(self.toggle_uploads)
        lay.addWidget(self.btn_uploads)
        lay.addStretch(1)
        return bar

    def _build_flyout(self):
        fl = QFrame()
        fl.setObjectName("flyout")
        fl.setMinimumWidth(0)
        fl.setMaximumWidth(270)
        lay = QVBoxLayout(fl)
        lay.setContentsMargins(12, 14, 12, 10)
        lay.setSpacing(8)
        lay.addWidget(section("YÜKLEMELER"))
        b = AButton("Görsel yükle…")
        b.setObjectName("accent")
        b.clicked.connect(self.upload_files)
        lay.addWidget(b)
        b2 = AButton("Panodan yapıştır (Ctrl+Shift+V)")
        b2.clicked.connect(self.paste_image)
        lay.addWidget(b2)
        self.up_list = QListWidget()
        self.up_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.up_list.setIconSize(QSize(100, 100))
        self.up_list.setGridSize(QSize(116, 128))
        self.up_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.up_list.setMovement(QListWidget.Movement.Static)
        self.up_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.up_list.itemDoubleClicked.connect(self.add_upload_item)
        self.up_list.customContextMenuRequested.connect(self.upload_menu)
        lay.addWidget(self.up_list, 1)
        h = QLabel("Çift tıkla: tuvale ekle · Dosyayı tuvale sürükleyebilirsin")
        h.setObjectName("hint")
        h.setWordWrap(True)
        lay.addWidget(h)
        fl.hide()
        return fl

    def _color_row(self, with_clear=True):
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        sw = swatch()
        hx = QLabel("")
        row.addWidget(sw)
        row.addWidget(hx, 1)
        clear = None
        if with_clear:
            clear = ATool()
            clear.setText("✕")
            clear.setToolTip("Kaldır")
            clear.setFixedSize(24, 24)
            row.addWidget(clear)
        return w, sw, hx, clear

    def _build_side(self):
        side = QFrame()
        side.setObjectName("side")
        side.setFixedWidth(272)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(14, 14, 14, 10)
        lay.setSpacing(8)

        lay.addWidget(section("TASARIM"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        f, self.sx = make_field("X")
        grid.addWidget(f, 0, 0)
        f, self.sy = make_field("Y")
        grid.addWidget(f, 0, 1)
        f, self.sw = make_field("W", 1)
        grid.addWidget(f, 1, 0)
        f, self.sh = make_field("H", 1)
        grid.addWidget(f, 1, 1)
        f, self.sr = make_field("R", 0, 10000)
        grid.addWidget(f, 2, 0)
        f, self.so = make_field("%", 0, 100)
        grid.addWidget(f, 2, 1)
        lay.addLayout(grid)
        for sp in (self.sx, self.sy, self.sw, self.sh):
            sp.valueChanged.connect(self.apply_geo)
        self.sr.valueChanged.connect(self.apply_radius)
        self.so.valueChanged.connect(self.apply_opacity)

        self.g_align = QWidget()
        al = QHBoxLayout(self.g_align)
        al.setContentsMargins(0, 2, 0, 0)
        al.setSpacing(2)
        for mode, ic, tip in (("l", "al_l", "Sola hizala"), ("ch", "al_ch", "Yatay ortala"), ("r", "al_r", "Sağa hizala"),
                              ("t", "al_t", "Üste hizala"), ("cv", "al_cv", "Dikey ortala"), ("b", "al_b", "Alta hizala")):
            b = icon_btn(ic, tip)
            b.clicked.connect(lambda _=False, m=mode: self.align(m))
            al.addWidget(b)
        self.b_disth = icon_btn("dist_h", "Yatay eşit dağıt (3+ nesne)")
        self.b_disth.clicked.connect(lambda: self.distribute("h"))
        self.b_distv = icon_btn("dist_v", "Dikey eşit dağıt (3+ nesne)")
        self.b_distv.clicked.connect(lambda: self.distribute("v"))
        al.addSpacing(6)
        al.addWidget(self.b_disth)
        al.addWidget(self.b_distv)
        al.addStretch(1)
        lay.addWidget(self.g_align)

        # dolgu / renk
        self.g_fill = QWidget()
        gl = QVBoxLayout(self.g_fill)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.setSpacing(6)
        gl.addWidget(sep())
        self.lbl_fill = section("DOLGU")
        gl.addWidget(self.lbl_fill)
        w, self.sw_fill, self.hex_fill, self.clr_fill = self._color_row(True)
        self.sw_fill.clicked.connect(self.pick_fill)
        self.clr_fill.clicked.connect(self.clear_fill)
        gl.addWidget(w)
        self.row_fill2, self.sw_fill2, self.hex_fill2, self.clr_fill2 = self._color_row(True)
        self.sw_fill2.clicked.connect(self.pick_fill2)
        self.clr_fill2.clicked.connect(self.clear_fill2)
        gl.addWidget(self.row_fill2)
        lay.addWidget(self.g_fill)

        # kenarlik / cizgi kalinligi
        self.g_stroke = QWidget()
        sl = QVBoxLayout(self.g_stroke)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(6)
        self.lbl_stroke = section("KENARLIK")
        sl.addWidget(self.lbl_stroke)
        w, self.sw_str, self.hex_str, self.clr_str = self._color_row(True)
        self.row_str_color = w
        self.sw_str.clicked.connect(self.pick_stroke)
        self.clr_str.clicked.connect(self.clear_stroke)
        sl.addWidget(w)
        f, self.s_ow = make_field("━", 0, 500)
        self.s_ow.valueChanged.connect(self.apply_ow)
        sl.addWidget(f)
        lay.addWidget(self.g_stroke)

        # metin
        self.g_text = QWidget()
        tl = QVBoxLayout(self.g_text)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(6)
        tl.addWidget(section("METİN"))
        self.text_edit = QPlainTextEdit()
        self.text_edit.setObjectName("bare")
        self.text_edit.setFixedHeight(66)
        self.text_edit.textChanged.connect(self.apply_text)
        tl.addWidget(self.text_edit)
        self.cb_font = FontCombo()
        self.cb_font.setMaxVisibleItems(18)
        self.cb_font.activated.connect(self.pick_font)
        tl.addWidget(self.cb_font)
        r2 = QHBoxLayout()
        f, self.s_size = make_field("Aa", 4, 4000)
        self.s_size.valueChanged.connect(self.apply_size)
        r2.addWidget(f, 1)
        self.b_bold = ATool()
        self.b_bold.setText("K")
        fb = self.b_bold.font()
        fb.setBold(True)
        self.b_bold.setFont(fb)
        self.b_italic = ATool()
        self.b_italic.setText("İ")
        fi = self.b_italic.font()
        fi.setItalic(True)
        self.b_italic.setFont(fi)
        for b in (self.b_bold, self.b_italic):
            b.setCheckable(True)
            b.setFixedSize(28, 28)
            r2.addWidget(b)
        self.b_bold.clicked.connect(self.apply_bold)
        self.b_italic.clicked.connect(self.apply_italic)
        tl.addLayout(r2)
        r3 = QHBoxLayout()
        r3.setSpacing(2)
        self.al_group = QButtonGroup(self)
        self.al_btns = {}
        for a, ic, tip in (("left", "tx_l", "Sola yasla"), ("center", "tx_c", "Ortala"), ("right", "tx_r", "Sağa yasla")):
            b = icon_btn(ic, tip, 28, True)
            b.clicked.connect(lambda _=False, a=a: self.apply_align(a))
            self.al_group.addButton(b)
            self.al_btns[a] = b
            r3.addWidget(b)
        r3.addStretch(1)
        tl.addLayout(r3)
        lay.addWidget(self.g_text)

        # tuval (secim yokken)
        self.g_canvas = QWidget()
        cl = QVBoxLayout(self.g_canvas)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(6)
        cl.addWidget(sep())
        cl.addWidget(section("TUVAL"))
        self.lbl_size = QLabel("")
        self.lbl_size.setObjectName("sub")
        cl.addWidget(self.lbl_size)
        w, self.sw_bg, self.hex_bg, _ = self._color_row(False)
        self.sw_bg.clicked.connect(self.pick_bg)
        cl.addWidget(w)
        w, self.sw_bg2, self.hex_bg2, self.clr_bg2 = self._color_row(True)
        self.sw_bg2.clicked.connect(self.pick_bg2)
        self.clr_bg2.clicked.connect(self.clear_bg2)
        cl.addWidget(w)
        lay.addWidget(self.g_canvas)

        lay.addWidget(sep())
        lay.addWidget(section("KATMANLAR"))
        self.layers = QListWidget()
        self.layers.setIconSize(QSize(16, 16))
        self.layers.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.layers.setMinimumHeight(110)
        self.layers.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.layers.itemSelectionChanged.connect(self.on_list_selection)
        self.layers.customContextMenuRequested.connect(self.list_menu)
        lay.addWidget(self.layers, 1)
        hint = QLabel("V R O L T I araçlar · Ctrl+tekerlek yakınlaştır · Boşluk+sürükle kaydır")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        return side
