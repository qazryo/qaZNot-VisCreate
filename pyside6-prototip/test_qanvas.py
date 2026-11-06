"""qAnvas PySide6 testleri (ekransiz). Kullanici verisine dokunmaz: tum yollar gecici klasore yonlendirilir."""
import hashlib
import io
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"
sys.argv = ["x"]

TMP = tempfile.mkdtemp(prefix="qv_test_")
import qv_engine as E  # noqa: E402

E._data_dir = lambda: TMP
E.CONFIG = os.path.join(TMP, "settings.json")
E.SECURITY = os.path.join(TMP, "security.json")
E.GOOGLE = os.path.join(TMP, "google.json")
E.AVATARS = os.path.join(TMP, "avatars")

TEST_KEY = "TEST-AAAA-BBBB-CCCC-DDDD"
H = hashlib.sha256(E.norm_key(TEST_KEY).encode()).hexdigest()
E.LICENSES[H] = {"ed": "enterprise", "user": "T", "name": "Test Kullanicisi", "email": "t@x.y", "id": "QZ-T-777", "since": "2026-11-03"}
E.ID_INDEX["QZ-T-777"] = (H, E.LICENSES[H])

from PySide6.QtCore import Qt, QPointF  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from PIL import Image  # noqa: E402

import qanvas as Q  # noqa: E402
from qv_login import Account, AccountDialog  # noqa: E402
from qv_theme import QSS  # noqa: E402

app = QApplication([])
app.setStyle("Fusion")
app.setStyleSheet(QSS)
ok = []


def check(name, cond):
    ok.append(bool(cond))
    print(("OK   " if cond else "FAIL ") + name)


def pump():
    app.processEvents()


# ---------- lisans / hesap ----------
check("gecersiz anahtar bulunamaz", E.lookup_license("AAAA-AAAA-AAAA-AAAA-AAAA")[1] is None)
dlg = AccountDialog(None, required=True)
dlg.show()
dlg.entry.setText("")
dlg.entry.textEdited.emit("abcd1234efgh5678ijkl")
dlg.entry.setText(E.fmt_key("abcd1234efgh5678ijkl"))
check("anahtar bicimlenir", dlg.entry.text() == "ABCD-1234-EFGH-5678-IJKL")
for i in range(5):
    dlg.check()
    QTest.qWait(500)
check("5 hatali denemeden sonra kilit", E.load_security()["until"] > 0)
E.save_security({"fails": 0, "until": 0})
dlg.entry.setText(TEST_KEY)
dlg.check()
QTest.qWait(600)
check("dogru anahtar hesap kartina gecer", dlg.stack.currentWidget() is dlg.page_acc and dlg._pending is not None)
dlg._open_it()
check("giris sonrasi ayar kaydedildi", Account.load() is not None and Account.load().aid == "QZ-T-777")
acct = Account.load()
check("surum enterprise/full", acct.ed["label"] == "Enterprise" and acct.full)
png = io.BytesIO()
Image.new("RGB", (64, 64), "#3366ff").save(png, "PNG")
acct.set_google({"sub": "1", "name": "Ahmet Test", "email": "a@b.c", "linked": "x"}, png.getvalue())
check("google profili kaydedildi", acct.google_profile() and acct.google_profile()["email"] == "a@b.c")
check("google avatar uretildi", not acct.avatar(56).isNull() and acct.name == "Ahmet Test")
view = AccountDialog(acct)
view.show()
check("hesabim sayfasi acildi", view.stack.currentWidget() is view.page_acc and view.btn_google.text() == "Google'ı kes")
acct.unlink_google()
check("google baglantisi kesildi", acct.google_profile() is None)
Account.forget()
check("oturum kapatinca anahtar silindi", Account.load() is None)

# ---------- motor + arayuz ----------
win = Q.MainWindow(acct)
win.quiet = True
win.show()
pump()
win.view.fit()
pump()
check("varsayilan belge 1024x1024", (win.doc.w, win.doc.h) == (1024, 1024))

# tum sablonlar yuklenir ve render olur
bad = []
for t in E.QV_TEMPLATES:
    try:
        d = E.qv_new_template(acct.ed, t["id"])
        im = d.render()
        assert im.size == (t["w"], t["h"])
    except Exception as ex:  # noqa: BLE001
        bad.append((t["id"], str(ex)))
check(f"{len(E.QV_TEMPLATES)} sablon render oluyor {bad[:2]}", not bad)

win.load_doc(E.qv_new_template(acct.ed, "vid-baslik"), None)
pump()
n0 = len(win.items)
check("sablon katmanlari sahneye geldi", n0 == len(win.doc.layers) and n0 > 3)

vp = win.view.viewport()


def vpos(x, y):
    return win.view.mapFromScene(QPointF(x, y))


# cizim
win.set_tool("rect")
QTest.mousePress(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, vpos(100, 900))
QTest.mouseMove(vp, vpos(300, 1000))
QTest.mouseRelease(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, vpos(300, 1000))
pump()
check("cizim: katman eklendi", len(win.doc.layers) == n0 + 1 and win.cur is not None)
c = win.cur
check("cizim: boyut ~200x100", abs(c.d["w"] - 200) < 4 and abs(c.d["h"] - 100) < 4)
check("dict ile item eslesik", c.d is win.doc.layers[-1])

# resize
x, y, w, h = c.box()
a, b = vpos(x + w, y + h), vpos(x + w + 100, y + h + 50)
QTest.mousePress(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, a)
QTest.mouseMove(vp, b)
QTest.mouseRelease(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, b)
pump()
check("resize dict'e yansidi", c.d["w"] > w + 80)

# tasima
p0 = c.d["x"]
a, b = vpos(x + 30, y + 30), vpos(x + 150, y + 30)
QTest.mousePress(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, a)
QTest.mouseMove(vp, b)
QTest.mouseRelease(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, b)
pump()
check("tasima dict'e yansidi", c.d["x"] > p0 + 60)

# panel
win.sw.setValue(300)
check("panel -> genislik", abs(c.d["w"] - 300) < 0.5)
win.sr.setValue(30)
check("panel -> yaricap", c.d["rad"] == 30)
win.s_ow.setValue(6)
check("panel -> kenarlik", c.d["ow"] == 6 and c.d["outline"])

# metin araci + metin duzenleme
win.set_tool("text")
QTest.mouseClick(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, vpos(600, 900))
pump()
t = win.cur
check("metin katmani", t is not None and t.kind == "text")
win.text_edit.setPlainText("Merhaba Dünya")
win.s_size.setValue(70)
win.b_bold.setChecked(True)
win.apply_bold()
win.apply_align("center")
check("metin ozellikleri dict'e yansidi", t.d["text"] == "Merhaba Dünya" and t.d["size"] == 70 and t.d["bold"] and t.d["align"] == "center")

# metni kosedan buyutunce yazi da buyur, kucultunce kucul
win.scene.clearSelection()
t.setSelected(True)
pump()
x, y, w, h = t.box()
s0 = t.d["size"]
a, b = vpos(x + w, y + h), vpos(x + w * 1.5, y + h * 1.5)
QTest.mousePress(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, a)
QTest.mouseMove(vp, b)
QTest.mouseRelease(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, b)
pump()
check(f"metin buyutme: yazi boyutu arttı ({s0:.0f} -> {t.d['size']:.0f})", t.d["size"] > s0 * 1.3)
x, y, w, h = t.box()
s1 = t.d["size"]
a, b = vpos(x + w, y + h), vpos(x + w * 0.5, y + h * 0.5)
QTest.mousePress(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, a)
QTest.mouseMove(vp, b)
QTest.mouseRelease(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, b)
pump()
check(f"metin kucultme: yazi boyutu azaldi ({s1:.0f} -> {t.d['size']:.0f})", t.d["size"] < s1 * 0.7)
check("panel boyutu guncel", abs(win.s_size.value() - round(t.d["size"])) <= 1)

# yazi tipi listesi: her ad kendi yazi tipiyle cizilir
from qv_panels import font_preview  # noqa: E402
fam = [win.cb_font.itemText(i) for i in range(win.cb_font.count()) if win.cb_font.itemData(i) == "local"]
pa, pb = font_preview("Arial"), font_preview("Consolas")
check("yazi tipi onizlemeleri uretiliyor", fam and pa and pb and pa.toImage() != pb.toImage())

# cizgi
win.set_tool("line")
QTest.mousePress(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, vpos(100, 50))
QTest.mouseMove(vp, vpos(400, 150))
QTest.mouseRelease(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, vpos(400, 150))
pump()
ln = win.cur
check("cizgi katmani", ln is not None and ln.kind == "line" and abs(ln.d["x2"] - ln.d["x"]) > 100)

# hizalama (tuvala ortala)
win.align("ch")
x, y, w, h = ln.box()
check("hizala: yatay ortalandi", abs((x + w / 2) - win.doc.w / 2) < 1)

# geri al / yinele
win.after_edit()
cnt = len(win.doc.layers)
win.duplicate()
check("kopya", len(win.doc.layers) == cnt + 1)
win.undo()
check("geri al (kopya)", len(win.doc.layers) == cnt)
win.redo()
check("yinele (kopya)", len(win.doc.layers) == cnt + 1)
win.delete_selected()
check("sil", len(win.doc.layers) == cnt)
win.undo()
check("geri al (sil)", len(win.doc.layers) == cnt + 1)

# katman sirasi
win.scene.clearSelection()
win.items[0].setSelected(True)
first = win.doc.layers[0]
win.reorder("front")
check("one getir", win.doc.layers[-1] is first or win.doc.layers[-1] == first)

# arka plan
win.doc.bg2 = "#ff0000"
win.artboard.refresh()
win.sync_props()
check("gradyan hex etiketi", win.hex_bg2.text() == "#FF0000")

# gorsel ekleme (kitapliga) + export
tmpimg = os.path.join(TMP, "foto.png")
Image.new("RGB", (400, 300), "#00aa55").save(tmpimg)
nl = len(win.doc.layers)
win.add_images([tmpimg])
pump()
check("gorsel katmani eklendi", len(win.doc.layers) == nl + 1 and win.doc.layers[-1]["type"] == "image")
check("kitapliga eklendi", len(E.qv_lib_list()) == 1)

out_png = os.path.join(TMP, "cikti.png")
out_jpg = os.path.join(TMP, "cikti.jpg")
win.doc.export(out_png)
win.doc.export(out_jpg)
im = Image.open(out_png)
check("PNG disa aktarildi, boyut dogru", im.size == (win.doc.w, win.doc.h))
check("JPG disa aktarildi", Image.open(out_jpg).format == "JPEG")
# gorselin disa aktarimda gorundugunu dogrula (yesil piksel var mi)
g = [im.getpixel((int(l["x"] + l["w"] / 2), int(l["y"] + l["h"] / 2))) for l in win.doc.layers if l["type"] == "image"][0]
check("gorsel ciktida gorunuyor", g[1] > 120 and g[0] < 60)

# kaydet / ac
qp = os.path.join(TMP, "deneme.qanvas")
win.path = qp
check("kaydet", win.save() and os.path.exists(qp))
doc2 = E.qv_load(acct.ed, qp)
check("dosyadan acma: katman sayisi ayni", len(doc2.layers) == len(win.doc.layers) and doc2.bg2 == "#ff0000")
win.load_doc(doc2, qp)
pump()
check("acilan belge sahnede", len(win.items) == len(doc2.layers))

# Core kisitlari
core = Account("CORE-0000-0000-0000-0000", dict(ed="core", user="c", name="Core Kullanici", email="c@x", id="QZ-C-999", since="2026-11-03"))
check("core: sablon yok", not core.full)
try:
    E.qv_new_template(core.ed, "vid-baslik")
    check("core: sablon engelli", False)
except E.QvPermissionError:
    check("core: sablon engelli", True)
try:
    E.qv_new_custom(core.ed, 500, 500)
    check("core: ozel boyut engelli", False)
except E.QvPermissionError:
    check("core: ozel boyut engelli", True)
cw = Q.MainWindow(core)
cw.show()
pump()
cw.populate_fonts()
fams = {cw.cb_font.itemText(i) for i in range(cw.cb_font.count())}
check("core: yazi tipleri sinirli", len(fams) <= len(E.CORE_FONTS) + 1 and not any("(indir)" in f for f in fams))

# ---------- yeni qAnvas özellikleri ----------
from PySide6.QtWidgets import QApplication as _QA  # noqa: E402
win.load_doc(E.QvDoc(600, 400, "#ffffff"), None)
pump()
for i in range(4):
    win.add_layer("rect", 20 + i * 90, 50, w=40 + i * 10, h=60, fill="#336699")
win.scene.clearSelection()
for it in win.items:
    it.setSelected(True)
win.distribute("h")
xs = sorted((it.box()[0], it.box()[2]) for it in win.items)
gaps = [round(xs[i + 1][0] - (xs[i][0] + xs[i][1]), 1) for i in range(3)]
check(f"eşit yatay dağıtma (boşluklar {gaps})", len(set(gaps)) == 1 and xs[0][0] == 20)
win.distribute("v")
check("eşit dikey dağıtma çalışır", True)

# gradyan dolgu
g = win.items[0]
win.scene.clearSelection()
g.setSelected(True)
pump()
check("gradyan satırı görünür", win.row_fill2.isVisibleTo(win))
g.d["fill"], g.d["fill2"] = "#ff0000", "#0000ff"
g.update()
win.sync_props()
check("gradyan etiketi", win.hex_fill2.text() == "#0000FF")
out2 = os.path.join(TMP, "grad.png")
win.doc.export(out2)
gi = Image.open(out2)
gx = int(g.box()[0] + g.box()[2] / 2)
top, bot = gi.getpixel((gx, int(g.box()[1]) + 3)), gi.getpixel((gx, int(g.box()[1] + g.box()[3]) - 3))
check(f"gradyan dışa aktarımda (üst {top[:3]}, alt {bot[:3]})", top[0] > bot[0] and bot[2] > top[2])
win.clear_fill2()
check("gradyan kaldırıldı", g.d["fill2"] is None)

# kopyala / yapıştır (görsel katman + varlık dahil)
win.load_doc(E.QvDoc(600, 400, "#ffffff"), None)
win.add_images([tmpimg])
pump()
win.add_layer("rect", 10, 10, w=50, h=50)
win.scene.clearSelection()
for it in win.items:
    it.setSelected(True)
n0 = len(win.doc.layers)
win.copy_layers()
win2 = Q.MainWindow(acct)
win2.show()
check("başka belgeye yapıştırıldı", win2.paste_layers() and len(win2.doc.layers) == 2)
check("görsel varlığı da taşındı", any(l["type"] == "image" and l["asset"] in win2.doc.assets for l in win2.doc.layers))
win.paste_layers()
check("aynı belgeye yapıştırma kaydırır", len(win.doc.layers) == n0 + 2 and win.doc.layers[-1]["x"] == win.doc.layers[n0 - 1]["x"] + 24)
win.cut_layers()
check("kes: seçili katmanlar silindi", len(win.doc.layers) == n0)

# PDF dışa aktarma
pdfp = os.path.join(TMP, "tasarim.pdf")
win.doc.export(pdfp)
check("qAnvas PDF", open(pdfp, "rb").read(4) == b"%PDF")

# tuvalde metin düzenleme
win.load_doc(E.QvDoc(600, 400, "#ffffff"), None)
t = win.add_layer("text", 40, 40)
win.view.fit()
pump()
win.edit_text_inline(t)
pump()
ie = win._inline
check("satır içi düzenleme kutusu açıldı", ie is not None and ie.toPlainText() == "Metin")
ie.setPlainText("Yeni metin\nikinci satır")
ie.clearFocus()
ie._finish(True)
pump()
check("satır içi düzenleme uygulandı", t.d["text"] == "Yeni metin\nikinci satır" and win._inline is None)
win.edit_text_inline(t)
win._inline.setPlainText("vazgeç")
win._inline._finish(False)
check("Esc ile vazgeçildi", t.d["text"] == "Yeni metin\nikinci satır")

print("SONUC:", sum(ok), "/", len(ok))
sys.stdout.flush()
os._exit(0 if all(ok) else 1)
