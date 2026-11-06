"""qaZNot zengin metin düzenleyicisi (PySide6). .qaz biçimi eski Tk sürümüyle birebir uyumludur."""
import base64
import re
import uuid

from PySide6.QtCore import Qt, Signal, QByteArray, QBuffer, QIODevice, QUrl
from PySide6.QtGui import (QTextCharFormat, QTextCursor, QTextFormat, QFont, QColor, QBrush, QImage, QTextBlockFormat,
                           QTextDocument, QTextListFormat, QTextImageFormat)
from PySide6.QtWidgets import QTextEdit, QMenu

P = QTextFormat.Property
ALIGN = {"left": Qt.AlignmentFlag.AlignLeft, "center": Qt.AlignmentFlag.AlignHCenter,
         "right": Qt.AlignmentFlag.AlignRight}
MAX_MATCHES = 20000


def _family(f):
    if f.hasProperty(P.FontFamilies):
        v = f.property(P.FontFamilies)
        if isinstance(v, (list, tuple)) and v:
            return str(v[0])
        if isinstance(v, str) and v:
            return v
    if f.hasProperty(P.FontFamily):
        return str(f.property(P.FontFamily))
    return None


class Editor(QTextEdit):
    style_changed = Signal()
    zoom_changed = Signal(int)

    def __init__(self):
        super().__init__()
        self.setObjectName("qzedit")
        self.setAcceptRichText(False)
        self.setFrameShape(QTextEdit.Shape.NoFrame)
        self.base_family, self.base_size, self.zoom = "Segoe UI", 12, 100
        self.match_color = "#ffe58f"
        self.fg_default = "#1d1d1f"
        self._dev = None
        self._matches = []
        self.find_error = False
        self.document().setDocumentMargin(26)
        self.apply_base()
        self.cursorPositionChanged.connect(self.style_changed)
        self.currentCharFormatChanged.connect(lambda _f: self.style_changed.emit())

    # ---------- taban yazı tipi ve yakınlaştırma ----------
    def apply_base(self, family=None, size=None):
        if family:
            self.base_family = family
        if size:
            self.base_size = size
        f = QFont(self.base_family)
        f.setPointSizeF(float(self.base_size))
        m = self.document().isModified()
        self.document().setDefaultFont(f)
        self.document().setModified(m)  # yazı tipi tabanını değiştirmek belgeyi "değişti" yapmaz

    def set_zoom(self, z):
        z = max(10, min(500, int(z)))
        self.zoom = z
        mod = self.document().isModified()
        if z == 100:
            self.document().documentLayout().setPaintDevice(self.viewport())
            self._dev = None
        else:
            img = QImage(8, 8, QImage.Format.Format_ARGB32)
            dpm = int(self.logicalDpiX() * z / 100 / 0.0254)
            img.setDotsPerMeterX(dpm)
            img.setDotsPerMeterY(dpm)
            self._dev = img
            self.document().documentLayout().setPaintDevice(img)
        self.document().markContentsDirty(0, max(1, self.document().characterCount()))
        self.document().setModified(mod)
        self.viewport().update()
        self.zoom_changed.emit(z)

    def wheelEvent(self, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.set_zoom(self.zoom + (10 if e.angleDelta().y() > 0 else -10))
            e.accept()
            return
        super().wheelEvent(e)

    def insertFromMimeData(self, source):
        if source.hasImage():
            img = source.imageData()
            if isinstance(img, QImage) and self.insert_image(img):
                return
        if source.hasText():
            self.insertPlainText(source.text())

    def contextMenuEvent(self, e):
        m = QMenu(self)
        m.addAction("Geri Al", self.undo).setEnabled(self.document().isUndoAvailable())
        m.addSeparator()
        c = self.textCursor().hasSelection()
        m.addAction("Kes", self.cut).setEnabled(c)
        m.addAction("Kopyala", self.copy).setEnabled(c)
        m.addAction("Yapıştır", self.paste)
        m.addAction("Sil", self.delete_selection).setEnabled(c)
        m.addSeparator()
        m.addAction("Tümünü Seç", self.selectAll)
        m.exec(e.globalPos())

    def delete_selection(self):
        self.textCursor().removeSelectedText()

    # ---------- biçim okuma ----------
    def style(self):
        f = self.currentCharFormat()
        sz = f.fontPointSize() if f.hasProperty(P.FontPointSize) else 0
        al = self.alignment()
        return dict(
            family=_family(f) or self.base_family,
            size=sz if sz > 0 else self.base_size,
            bold=f.hasProperty(P.FontWeight) and f.fontWeight() >= 600,
            italic=f.fontItalic(), underline=f.fontUnderline(), overstrike=f.fontStrikeOut(),
            fg=f.foreground().color().name() if f.hasProperty(P.ForegroundBrush) else None,
            bg=f.background().color().name() if f.hasProperty(P.BackgroundBrush) else None,
            align="center" if al & Qt.AlignmentFlag.AlignHCenter else "right" if al & Qt.AlignmentFlag.AlignRight else "left",
            list=self.list_style())

    # ---------- biçim uygulama ----------
    def modify(self, fn):
        """Seçim varsa seçimin parçalarına, yoksa bir sonraki yazılacak karaktere uygular."""
        c = self.textCursor()
        if not c.hasSelection():
            f = self.currentCharFormat()
            fn(f)
            self.setCurrentCharFormat(f)
            return
        a, b = c.selectionStart(), c.selectionEnd()
        doc = self.document()
        frags = []
        blk = doc.findBlock(a)
        while blk.isValid() and blk.position() < b:
            it = blk.begin()
            while not it.atEnd():
                fr = it.fragment()
                s, e = max(fr.position(), a), min(fr.position() + fr.length(), b)
                if s < e:
                    frags.append((s, e, fr.charFormat()))
                it += 1
            blk = blk.next()
        edit = QTextCursor(doc)
        edit.beginEditBlock()
        for s, e, f in frags:
            nf = QTextCharFormat(f)
            fn(nf)
            edit.setPosition(s)
            edit.setPosition(e, QTextCursor.MoveMode.KeepAnchor)
            edit.setCharFormat(nf)
        edit.endEditBlock()
        self.style_changed.emit()

    def set_family(self, name):
        self.modify(lambda f: f.setFontFamilies([name]))

    def set_size(self, pt):
        pt = max(1.0, min(400.0, float(pt)))
        self.modify(lambda f: f.setFontPointSize(pt))

    def toggle(self, prop):
        on = not self.style()[prop]
        if prop == "bold":
            self.modify(lambda f: f.setFontWeight(700 if on else 400))
        elif prop == "italic":
            self.modify(lambda f: f.setFontItalic(on))
        elif prop == "underline":
            self.modify(lambda f: f.setFontUnderline(on))
        elif prop == "overstrike":
            self.modify(lambda f: f.setFontStrikeOut(on))

    def set_color(self, which, color):
        def fn(f):
            if which == "fg":
                if color:
                    f.setForeground(QBrush(QColor(color)))
                else:
                    f.clearForeground()
            else:
                if color:
                    f.setBackground(QBrush(QColor(color)))
                else:
                    f.clearBackground()
        self.modify(fn)

    def set_align(self, a):
        self.setAlignment(ALIGN[a])
        self.style_changed.emit()

    def clear_format(self):
        c = self.textCursor()
        if c.hasSelection():
            c.beginEditBlock()
            c.setCharFormat(QTextCharFormat())
            c.endEditBlock()
            self.setAlignment(ALIGN["left"])
        else:
            self.setCurrentCharFormat(QTextCharFormat())
        self.style_changed.emit()

    # ---------- paragraf biçimi: liste, girinti, satır aralığı ----------
    LIST_NAMES = {QTextListFormat.Style.ListDisc: "disc", QTextListFormat.Style.ListDecimal: "decimal"}
    LIST_STYLES = {"disc": QTextListFormat.Style.ListDisc, "decimal": QTextListFormat.Style.ListDecimal}

    def _selected_blocks(self):
        c = self.textCursor()
        doc = self.document()
        a, b = c.selectionStart(), c.selectionEnd()
        blk = doc.findBlock(a)
        last = doc.findBlock(b if b == a else b - 1).blockNumber()
        out = []
        while blk.isValid():
            out.append(blk)
            if blk.blockNumber() >= last:
                break
            blk = blk.next()
        return out

    def list_style(self):
        lst = self.textCursor().currentList()
        return self.LIST_NAMES.get(lst.format().style()) if lst else None

    def toggle_list(self, name):
        """name: 'disc' (madde işaretli) ya da 'decimal' (numaralı). Aynı listedeyse listeden çıkarır."""
        c = self.textCursor()
        c.beginEditBlock()
        if self.list_style() == name:
            for blk in self._selected_blocks():
                lst = blk.textList()
                if lst:
                    lst.remove(blk)
                    cc = QTextCursor(blk)
                    bf = cc.blockFormat()
                    bf.setIndent(0)
                    cc.setBlockFormat(bf)
        else:
            lf = QTextListFormat()
            lf.setStyle(self.LIST_STYLES[name])
            lf.setIndent(1)
            c.createList(lf)
        c.endEditBlock()
        self.style_changed.emit()

    def change_indent(self, d):
        c = self.textCursor()
        c.beginEditBlock()
        for blk in self._selected_blocks():
            cc = QTextCursor(blk)
            lst = blk.textList()
            if lst:
                lf = lst.format()
                lf.setIndent(max(1, min(8, lf.indent() + d)))
                lst.setFormat(lf)
            else:
                bf = cc.blockFormat()
                bf.setIndent(max(0, min(12, bf.indent() + d)))
                cc.setBlockFormat(bf)
        c.endEditBlock()
        self.style_changed.emit()

    def set_line_spacing(self, pct):
        """pct: 100 = tek satır, 115, 150, 200 ..."""
        c = self.textCursor()
        c.beginEditBlock()
        for blk in self._selected_blocks():
            cc = QTextCursor(blk)
            bf = cc.blockFormat()
            bf.setLineHeight(float(pct), QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
            cc.setBlockFormat(bf)
        c.endEditBlock()
        self.style_changed.emit()

    def block_entries(self):
        out = []
        blk = self.document().begin()
        while blk.isValid():
            bf = blk.blockFormat()
            e = {}
            if bf.indent():
                e["i"] = bf.indent()
            if bf.lineHeightType() == QTextBlockFormat.LineHeightTypes.ProportionalHeight.value and abs(bf.lineHeight() - 100) > 0.5 \
                    and bf.lineHeight() > 0:
                e["ls"] = round(bf.lineHeight())
            lst = blk.textList()
            if lst:
                name = self.LIST_NAMES.get(lst.format().style())
                if name:
                    e["list"] = name
                    e["li"] = lst.format().indent()
            if e:
                e["l"] = blk.blockNumber() + 1
                out.append(e)
            blk = blk.next()
        return out

    def _apply_blocks(self, entries):
        doc = self.document()
        group, prev = None, None
        for e in sorted((x for x in entries if isinstance(x, dict) and "l" in x), key=lambda x: x["l"]):
            blk = doc.findBlockByNumber(int(e["l"]) - 1)
            if not blk.isValid():
                continue
            cc = QTextCursor(blk)
            bf = cc.blockFormat()
            if e.get("i"):
                bf.setIndent(int(e["i"]))
            if e.get("ls"):
                bf.setLineHeight(float(e["ls"]), QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
            cc.setBlockFormat(bf)
            name = e.get("list")
            if name in self.LIST_STYLES:
                key = (name, int(e.get("li", 1)))
                if group is not None and prev == (key, int(e["l"]) - 1):
                    group.add(blk)
                else:
                    lf = QTextListFormat()
                    lf.setStyle(self.LIST_STYLES[name])
                    lf.setIndent(key[1])
                    group = cc.createList(lf)
                prev = (key, int(e["l"]))
            else:
                group, prev = None, None

    # ---------- resimler ----------
    def insert_image(self, img):
        if img.isNull():
            return False
        if img.width() > 1280:
            img = img.scaledToWidth(1280, Qt.TransformationMode.SmoothTransformation)
        name = f"qzimg{uuid.uuid4().hex[:10]}.png"
        self.document().addResource(QTextDocument.ResourceType.ImageResource, QUrl(name), img)
        w = min(img.width(), 640)
        h = round(img.height() * w / img.width())
        f = QTextImageFormat()
        f.setName(name)
        f.setWidth(w)
        f.setHeight(h)
        self.textCursor().insertImage(f)
        return True

    def image_entries(self):
        out = []
        doc = self.document()
        blk = doc.begin()
        while blk.isValid():
            it = blk.begin()
            while not it.atEnd():
                fr = it.fragment()
                cf = fr.charFormat()
                if cf.isImageFormat():
                    imf = cf.toImageFormat()
                    img = doc.resource(QTextDocument.ResourceType.ImageResource, QUrl(imf.name()))
                    if isinstance(img, QImage) and not img.isNull():
                        ba = QByteArray()
                        buf = QBuffer(ba)
                        buf.open(QIODevice.OpenModeFlag.WriteOnly)
                        img.save(buf, "PNG")
                        out.append({"r": self._idx(fr.position()), "w": int(imf.width()), "h": int(imf.height()),
                                    "png": base64.b64encode(bytes(ba)).decode("ascii")})
                it += 1
            blk = blk.next()
        return out

    def _apply_images(self, entries):
        doc = self.document()
        items = []
        for e in entries:
            try:
                items.append((self._pos(e["r"]), e))
            except (KeyError, ValueError):
                continue
        for pos, e in sorted(items, key=lambda x: -x[0]):
            if pos >= doc.characterCount() - 1 or doc.characterAt(pos) != "\ufffc":
                continue
            img = QImage.fromData(base64.b64decode(e.get("png", "")))
            if img.isNull():
                continue
            name = f"qzimg{uuid.uuid4().hex[:10]}.png"
            doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl(name), img)
            f = QTextImageFormat()
            f.setName(name)
            f.setWidth(float(e.get("w") or min(img.width(), 640)))
            f.setHeight(float(e.get("h") or img.height()))
            c = QTextCursor(doc)
            c.setPosition(pos)
            c.setPosition(pos + 1, QTextCursor.MoveMode.KeepAnchor)
            c.insertImage(f)

    # ---------- .qaz ----------
    def _idx(self, pos):
        b = self.document().findBlock(pos)
        return f"{b.blockNumber() + 1}.{pos - b.position()}"

    def _pos(self, idx):
        l, c = (int(x) for x in str(idx).split("."))
        doc = self.document()
        b = doc.findBlockByNumber(max(0, l - 1))
        if not b.isValid():
            return doc.characterCount() - 1
        return b.position() + min(max(c, 0), b.length() - 1)

    def runs(self):
        """(tür, değer, [(başlangıç, bitiş)...]) listesi; Tk sürümüyle aynı anlamlar."""
        spec0 = (self.base_family, float(self.base_size), False, False)
        acc = {}

        def add(key, a, b):
            lst = acc.setdefault(key, [])
            if lst and a <= lst[-1][1] + 1:
                lst[-1] = (lst[-1][0], max(lst[-1][1], b))
            else:
                lst.append((a, b))
        blk = self.document().begin()
        while blk.isValid():
            it = blk.begin()
            while not it.atEnd():
                fr = it.fragment()
                f, a, b = fr.charFormat(), fr.position(), fr.position() + fr.length()
                sz = f.fontPointSize() if f.hasProperty(P.FontPointSize) and f.fontPointSize() > 0 else self.base_size
                spec = (_family(f) or self.base_family, float(sz), f.hasProperty(P.FontWeight) and f.fontWeight() >= 600,
                        f.fontItalic())
                if spec != spec0:
                    sz_out = int(spec[1]) if spec[1] == int(spec[1]) else spec[1]
                    add(("font", (spec[0], sz_out, spec[2], spec[3])), a, b)
                if f.fontUnderline():
                    add(("u", None), a, b)
                if f.fontStrikeOut():
                    add(("o", None), a, b)
                if f.hasProperty(P.ForegroundBrush):
                    add(("fg", f.foreground().color().name()), a, b)
                if f.hasProperty(P.BackgroundBrush):
                    add(("bg", f.background().color().name()), a, b)
                it += 1
            al = blk.blockFormat().alignment()
            kind = "center" if al & Qt.AlignmentFlag.AlignHCenter else "right" if al & Qt.AlignmentFlag.AlignRight else None
            if kind:
                add(("al", kind), blk.position(), blk.position() + blk.length())
            blk = blk.next()
        return acc

    def has_formatting(self):
        return bool(self.runs() or self.block_entries() or self.image_entries())

    def to_qaz(self):
        end = self.document().characterCount() - 1
        runs = []
        for (k, v), ranges in self.runs().items():
            rs = []
            for a, b in ranges:
                rs += [self._idx(min(a, end)), self._idx(min(b, end))]
            runs.append({"k": k, "v": list(v) if k == "font" else v, "r": rs})
        out = {"v": 1, "app": "qaZNot", "text": self.toPlainText(),
               "base": {"family": self.base_family, "size": self.base_size}, "runs": runs}
        blocks, images = self.block_entries(), self.image_entries()
        if blocks:
            out["blocks"] = blocks
        if images:
            out["images"] = images
        return out

    def from_qaz(self, data):
        self.blockSignals(True)
        self.clear()
        self.setCurrentCharFormat(QTextCharFormat())
        base = data.get("base")
        if base:
            self.apply_base(str(base["family"]), int(base["size"]))
        self.setPlainText(str(data["text"]))
        doc = self.document()
        for run in data.get("runs", []):
            k, v, rs = run["k"], run.get("v"), run["r"]
            f = QTextCharFormat()
            if k == "font":
                fam, size, bold, italic = v
                f.setFontFamilies([str(fam)])
                f.setFontPointSize(float(size))
                f.setFontWeight(700 if bold else 400)
                f.setFontItalic(bool(italic))
            elif k == "u":
                f.setFontUnderline(True)
            elif k == "o":
                f.setFontStrikeOut(True)
            elif k == "fg":
                f.setForeground(QBrush(QColor(v)))
            elif k == "bg":
                f.setBackground(QBrush(QColor(v)))
            for i in range(0, len(rs) - 1, 2):
                a, b = self._pos(rs[i]), self._pos(rs[i + 1])
                if b <= a:
                    continue
                c = QTextCursor(doc)
                c.setPosition(a)
                c.setPosition(b, QTextCursor.MoveMode.KeepAnchor)
                if k == "al":
                    bf = QTextBlockFormat()
                    bf.setAlignment(ALIGN.get(str(v), ALIGN["left"]))
                    c.setPosition(a)
                    c.setPosition(max(a, b - 1), QTextCursor.MoveMode.KeepAnchor)
                    c.mergeBlockFormat(bf)
                else:
                    c.mergeCharFormat(f)
        if isinstance(data.get("blocks"), list):
            self._apply_blocks(data["blocks"])
        if isinstance(data.get("images"), list):
            self._apply_images(data["images"])
        self.blockSignals(False)
        self.reset_state()

    def load_plain(self, text):
        self.blockSignals(True)
        self.clear()
        self.setCurrentCharFormat(QTextCharFormat())
        self.setPlainText(text)
        self.blockSignals(False)
        self.reset_state()

    def reset_state(self):
        c = self.textCursor()
        c.setPosition(0)
        self.setTextCursor(c)
        self.document().clearUndoRedoStacks()
        self.document().setModified(False)
        self.style_changed.emit()

    # ---------- bul / değiştir (Python re: tam sözcük, regex, başa sarma) ----------
    def _compile(self, term, case, whole=False, regex=False):
        if not term:
            return None
        try:
            pat = term if regex else re.escape(term)
            if whole:
                pat = r"(?<!\w)(?:" + pat + r")(?!\w)"
            fl = re.UNICODE | (re.MULTILINE if regex else 0) | (0 if case else re.IGNORECASE)
            return re.compile(pat, fl)
        except re.error:
            return None

    def _find_all(self, term, case, whole=False, regex=False):
        """[(başlangıç, bitiş, eşleşme)] listesi (boş eşleşmeler atlanır, en çok MAX_MATCHES)."""
        rx = self._compile(term, case, whole, regex)
        self.find_error = bool(term) and rx is None
        if rx is None:
            return []
        out = []
        for m in rx.finditer(self.toPlainText()):
            if m.end() > m.start():
                out.append((m.start(), m.end(), m))
                if len(out) >= MAX_MATCHES:
                    break
        return out

    def highlight_all(self, term, case, whole=False, regex=False):
        found = self._find_all(term, case, whole, regex)
        sels = []
        for a, b, _m in found:
            s = QTextEdit.ExtraSelection()
            c = QTextCursor(self.document())
            c.setPosition(a)
            c.setPosition(b, QTextCursor.MoveMode.KeepAnchor)
            s.cursor = c
            s.format.setBackground(QBrush(QColor(self.match_color)))
            sels.append(s)
        self.setExtraSelections(sels)
        self._matches = [(a, b) for a, b, _m in found]
        return len(found)

    def clear_highlight(self):
        self.setExtraSelections([])
        self._matches = []
        self.find_error = False

    def current_match_index(self):
        c = self.textCursor()
        if not c.hasSelection():
            return 0
        key = (c.selectionStart(), c.selectionEnd())
        return self._matches.index(key) + 1 if key in self._matches else 0

    def _select(self, a, b):
        c = self.textCursor()
        c.setPosition(a)
        c.setPosition(b, QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(c)
        self.ensureCursorVisible()

    def find_step(self, term, case, backward=False, stay=False, whole=False, regex=False, wrap=True):
        found = self._find_all(term, case, whole, regex)
        if not found:
            return False
        c = self.textCursor()
        s0, s1 = c.selectionStart(), c.selectionEnd()
        pick = None
        if stay:
            pick = next((f for f in found if f[0] >= s0), None)
        elif backward:
            pick = next((f for f in reversed(found) if f[1] <= s0 and not (f[0] == s0 and f[1] == s1)), None)
        else:
            lim = s1 if c.hasSelection() else c.position()
            pick = next((f for f in found if f[0] >= lim), None)
        if pick is None and wrap:
            pick = found[-1] if backward else found[0]
        if pick is None:
            return False
        self._select(pick[0], pick[1])
        return True

    def replace_one(self, term, repl, case, whole=False, regex=False):
        c = self.textCursor()
        if c.hasSelection():
            key = (c.selectionStart(), c.selectionEnd())
            for a, b, m in self._find_all(term, case, whole, regex):
                if (a, b) == key:
                    try:
                        text = m.expand(repl) if regex else repl
                    except (re.error, IndexError):
                        text = repl
                    c.insertText(text)
                    break
        return self.find_step(term, case, whole=whole, regex=regex)

    def replace_all(self, term, repl, case, whole=False, regex=False):
        found = self._find_all(term, case, whole, regex)
        if not found:
            return 0
        c = QTextCursor(self.document())
        c.beginEditBlock()
        for a, b, m in reversed(found):
            try:
                text = m.expand(repl) if regex else repl
            except (re.error, IndexError):
                text = repl
            c.setPosition(a)
            c.setPosition(b, QTextCursor.MoveMode.KeepAnchor)
            c.insertText(text)
        c.endEditBlock()
        return len(found)

    # ---------- istatistik ----------
    def stats(self):
        t = self.toPlainText()
        c = self.textCursor()
        sel = len(c.selectedText()) if c.hasSelection() else 0
        return len(re.findall(r"\S+", t)), len(t), sel, c.blockNumber() + 1, c.positionInBlock() + 1

    def goto_line(self, n):
        b = self.document().findBlockByNumber(max(0, n - 1))
        if b.isValid():
            c = self.textCursor()
            c.setPosition(b.position())
            self.setTextCursor(c)
            self.ensureCursorVisible()
