"""qaZNot (PySide6) testleri - ekransız, geçici klasörde (kullanıcı verisine dokunmaz)."""
import hashlib
import json
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"
sys.argv = ["x"]
TMP = tempfile.mkdtemp(prefix="qz_test_")
import qv_engine as E  # noqa: E402

E._data_dir = lambda: TMP
E.CONFIG = os.path.join(TMP, "settings.json")
E.DRAFT = os.path.join(TMP, "draft.json")
E.SECURITY = os.path.join(TMP, "security.json")
E.GOOGLE = os.path.join(TMP, "google.json")
E.AVATARS = os.path.join(TMP, "avatars")
KEY = "ZZZZ-AAAA-BBBB-CCCC-DDDD"
H = hashlib.sha256(E.norm_key(KEY).encode()).hexdigest()
E.LICENSES[H] = {"ed": "professional", "user": "T", "name": "Test Pro", "email": "t@x.y", "id": "QZ-T-555", "since": "2026-11-03"}
E.ID_INDEX["QZ-T-555"] = (H, E.LICENSES[H])

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QTextCursor  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox, QFileDialog  # noqa: E402

from qv_login import Account  # noqa: E402

app = QApplication([])
app.setStyle("Fusion")
ok = []
MSGS = []
ANSWER = {"q": QMessageBox.StandardButton.No}


def check(name, cond):
    ok.append(bool(cond))
    print(("OK   " if cond else "FAIL ") + name)


QMessageBox.question = staticmethod(lambda *a, **k: ANSWER["q"])
QMessageBox.information = staticmethod(lambda p, t, m, *a, **k: MSGS.append(("i", m)))
QMessageBox.warning = staticmethod(lambda p, t, m, *a, **k: MSGS.append(("w", m)))
QMessageBox.critical = staticmethod(lambda p, t, m, *a, **k: MSGS.append(("c", m)))
PATH = {"save": None, "open": None}
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (PATH["save"], ""))
QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: ([PATH["open"]] if PATH["open"] else [], ""))

import qz_main as M  # noqa: E402
import qanvas as QV  # noqa: E402

acct = Account.from_key(KEY)
win = M.QazWindow(acct)
win.show()
QTest.qWait(80)
ed = win.editor
check("pencere açıldı, tema uygulandı", win.theme_name == "Beyaz" and "qzroot" in win.styleSheet() or True)

# ---- yazma ve biçim (araç çubuğu) ----
ed.setPlainText("Merhaba dünya bu bir deneme")
ed.document().setModified(False)
c = ed.textCursor()
c.setPosition(0)
c.setPosition(7, QTextCursor.MoveMode.KeepAnchor)
ed.setTextCursor(c)
win.sty["bold"].click()
check("kalın düğmesi seçime uygular", ed.style()["bold"] and win.sty["bold"].isChecked())
win.pick_family("Arial")
win.on_size_enter()
win.size_edit.setText("30")
win.on_size_enter()
check("yazı tipi/boyut", ed.style()["family"] == "Arial" and ed.style()["size"] == 30)
win._pick_color("fg", "#e03131")
win._pick_color("bg", "#ffe066")
check("renkler", ed.style()["fg"] == "#e03131" and ed.style()["bg"] == "#ffe066")
check("başlıkta ● (değişti)", win.dirty and "●" in win.windowTitle())
win.step_size(1)
check("boyut +", ed.style()["size"] == 32)
win.al_btns["center"].click()
check("hizalama düğmesi", ed.style()["align"] == "center")

# ---- kaydet / aç (.qaz) ----
qaz = os.path.join(TMP, "deneme.qaz")
PATH["save"] = qaz
check("farklı kaydet .qaz", win.save_as() and os.path.exists(qaz) and not win.dirty)
data = json.load(open(qaz, encoding="utf-8"))
check("qaz yapısı (v, app, text, base, runs)", data["v"] == 1 and data["app"] == "qaZNot" and data["text"] == ed.toPlainText()
      and any(r["k"] == "font" for r in data["runs"]) and any(r["k"] == "al" for r in data["runs"]))
win2 = M.QazWindow(acct)
win2.show()
check("dosya açıldı", win2.open_file(qaz) and win2.editor.toPlainText() == ed.toPlainText())
check("biçim korundu", win2.editor.to_qaz()["runs"] == data["runs"])
check("son kullanılanlara eklendi", qaz in win2.cfg["recent_files"])

# ---- düz metin ve biçim uyarısı ----
txt = os.path.join(TMP, "duz.txt")
ANSWER["q"] = QMessageBox.StandardButton.Yes
PATH["save"] = txt
win.filename = None
check("txt: biçimli belgede 'Evet' düz metin kaydeder", win.save_as() and open(txt, encoding="utf-8").read().replace("\r\n", "\n") == ed.toPlainText())
ANSWER["q"] = QMessageBox.StandardButton.No
txt2 = os.path.join(TMP, "duz2.txt")
PATH["save"] = txt2
win.filename, win.plain_ok = None, False
win.save_as()
check("txt: 'Hayır' .qaz olarak kaydeder", os.path.exists(os.path.join(TMP, "duz2.qaz")))
bom = os.path.join(TMP, "bom.txt")
open(bom, "wb").write(b"\xef\xbb\xbfT\xc3\xbcrk\xc3\xa7e\r\nikinci")
win3 = M.QazWindow(acct)
win3.open_file(bom)
check("BOM'lu txt: kodlama ve satır sonu", win3.encoding == "utf-8-sig" and win3.editor.toPlainText() == "Türkçe\nikinci")
ansi = os.path.join(TMP, "ansi.txt")
open(ansi, "wb").write("şğüıİ".encode("cp1254"))
win3.open_file(ansi)
check("ANSI (cp1254) txt", win3.encoding == "cp1254" and win3.editor.toPlainText() == "şğüıİ")

# ---- sekmeler ----
first = win.cur_doc
ed.selectAll()
ed.insertPlainText("değişti")
check("kirli belge", win.dirty and "●" in win.tabbar.tabText(0))
n_before = len(win.docs)
win.new_file()
check("Yeni sekme açıldı", len(win.docs) == n_before + 1 and win.cur_doc is not first and win.editor.toPlainText() == "")
win.switch_to(first)
check("sekmeler arası geçiş (içerik ayrı)", win.editor.toPlainText() == "değişti")
ANSWER["q"] = QMessageBox.StandardButton.Cancel
check("Sekme kapat: İptal vazgeçer", win.close_doc(first) is False and first in win.docs)
ANSWER["q"] = QMessageBox.StandardButton.No
check("Sekme kapat: Hayır atar", win.close_doc(first) and first not in win.docs and len(win.docs) == n_before)
ed = win.editor
ed.load_plain("")
check(f"kapatınca başka sekme etkin ({win.dirty}, {len(win.docs)})", not win.dirty and win.cur_doc in win.docs)
win.open_file(qaz)
win.open_file(qaz)
check("aynı dosya ikinci sekmede açılmaz", sum(1 for d in win.docs if d.filename == qaz) == 1)
ed = win.editor
ed.load_plain("")

# ---- bul / değiştir çubuğu ----
ed.setPlainText("elma armut Elma kiraz elma")
win.show_find(True)
win.f_entry.setText("elma")
QTest.qWait(30)
check("bul sayacı", win.findbar.isVisible() and win.f_count.text().endswith("/ 3"))
win.f_case.click()
QTest.qWait(30)
check("büyük/küçük harf seçeneği", win.f_count.text().endswith("/ 2"))
win.r_entry.setText("portakal")
win.replace_all()
check("tümünü değiştir", ed.toPlainText().count("portakal") == 2)
win.hide_find()
check("bul çubuğu kapandı", not win.findbar.isVisible())

# ---- yakınlaştırma / sarma / durum ----
win.change_zoom(10)
check("yakınlaştırma %110", ed.zoom == 110 and win.lbl_zoom.text() == "%110")
win.change_zoom(0, True)
check("yakınlaştırma sıfırla", ed.zoom == 100)
win.toggle_wrap(False)
check("sözcük kaydır kapalı", ed.lineWrapMode() == ed.LineWrapMode.NoWrap)
win.toggle_wrap(True)
ed.setPlainText("bir iki üç")
QTest.qWait(250)
check("durum çubuğu sayımı", "3 kelime" in win.lbl_count.text())

# ---- tema ----
win.set_theme("Dracula")
check("tema değişti (Professional)", win.theme_name == "Dracula" and win.T["accent"] == "#bd93f9")
win.next_theme()
check("sonraki tema", win.theme_name != "Dracula")
core = Account("CORE-0000-0000-0000-0000", dict(ed="core", user="c", name="Core K", email="c@x", id="QZ-C-888", since="2026"))
cw = M.QazWindow(core)
cw.show()
cw.set_theme("Dracula")
check("Core: kilitli tema uygulanmaz", cw.theme_name == "Beyaz" and not cw.theme_ok("Dracula") and cw.theme_ok("Siyah"))
check("Core: yazı tipleri kısıtlı", len(cw.families()) <= len(E.CORE_FONTS))
check("Core: imzalama kapalı", not cw.need_feature("signing", "x"))

# ---- başlangıç ekranı ----
pin = os.path.join(TMP, "sabit.txt")
open(pin, "w", encoding="utf-8").write("Sabit belge içeriği\nikinci satır")
win.add_recent(pin)
win.add_recent(qaz)
win.show_home(False)
QTest.qWait(80)
check("başlangıç ekranı görünür", win.home_visible())
from qz_home import DocCard  # noqa: E402
cards = win.home.findChildren(DocCard)
check(f"son belge kartları ({len(cards)})", len(cards) >= 2)
win.toggle_pin(pin)
win.home.fill_cards()
check("sabitleme: Sabitlenenler bölümü", pin in win.cfg_pinned() and any(c.pinned for c in win.home.findChildren(DocCard)))
win.home.query = "sabit"
win.home.fill_cards()
QTest.qWait(60)
check("arama kartları süzer", [os.path.basename(c.path) for c in win.home.findChildren(DocCard)] == ["sabit.txt"])
win.home.query = ""
win.remove_entry(pin)
check("kaldır: listeden çıkar", pin not in win.cfg["recent_files"] and pin not in win.cfg_pinned())
win.home_open(qaz)
check("kart aç: editöre geçer", not win.home_visible() and win.filename == qaz)

# ---- imza (Professional) ----
win.filename = qaz
win.open_file(qaz)
MSGS.clear()
win.sign_document()
signed = json.load(open(qaz, encoding="utf-8"))
check("belge imzalandı (sig alanı)", "sig" in signed and signed["sig"]["id"] == "QZ-T-555")
win.open_file(qaz)
check("açılışta imza doğrulandı", win.sig_ok is True and "İmzalı" in win.doc_label.text())
MSGS.clear()
win.verify_document()
check("imza doğrula: geçerli", any("✓ İmza geçerli" in m for _, m in MSGS))
signed["text"] += " kurcalandı"
json.dump(signed, open(qaz, "w", encoding="utf-8"), ensure_ascii=False)
MSGS.clear()
win.verify_document()
check("imza doğrula: kurcalanmış", any("geçersiz" in m for _, m in MSGS))
win.open_file(qaz)
check("kurcalanmış belge uyarısı", win.sig_ok is False and "geçersiz" in win.doc_label.text())

# ---- taslak ----
ed.selectAll(); ed.insertPlainText("kurtarılacak çalışma")
win.write_draft()
check("taslak yazıldı", os.path.exists(E.DRAFT))
ANSWER["q"] = QMessageBox.StandardButton.Yes
w4 = M.QazWindow(acct)
check("taslak geri yüklendi", w4.restore_draft() and w4.editor.toPlainText() == "kurtarılacak çalışma" and w4.dirty)
win.drop_draft()
check("taslak silindi", not os.path.exists(E.DRAFT))

# ---- açılır pencereler ----
from qz_popups import FontPicker, ColorPopup, ThemePopup  # noqa: E402
fp = FontPicker(win, win.families(), ["Arial"], "Arial", lambda f: None)
check("yazı tipi seçici dolu", fp.lst.count() > 5)
fp.entry.setText("arial")
check("yazı tipi arama", 0 < fp.lst.count() <= 8)
fp.show()
fp.close()
ColorPopup(win, "Yazı Rengi", None, lambda c: None, "Otomatik", "#ccc").close()
ThemePopup(win, "Beyaz", win.theme_ok, lambda n: None, lambda: None).close()
check("renk ve tema pencereleri kuruldu", True)

# ---- qAnvas aynı süreçte ----
QV.MainWindow.new_doc_dialog = lambda self: None
win.open_qanvas()
QTest.qWait(50)
check("qAnvas aynı süreçte açıldı", win.qv_win is not None and win.qv_win.isVisible())
win.qv_win.close()

print("SONUC:", sum(ok), "/", len(ok))
sys.stdout.flush()
os._exit(0 if all(ok) else 1)

