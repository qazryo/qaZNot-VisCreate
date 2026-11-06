import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"
sys.argv = ["x"]
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QTextCursor  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from qz_editor import Editor  # noqa: E402

app = QApplication([])
ok = []


def check(name, cond):
    ok.append(bool(cond))
    print(("OK   " if cond else "FAIL ") + name)


ed = Editor()
ed.resize(600, 300)
ed.show()
QTest.qWait(50)

# Tk sürümünün yazdığı biçimde bir .qaz (satır.sütun aralıkları)
tk_doc = {"v": 1, "app": "qaZNot", "text": "Merhaba dünya\nİkinci satır burada\nÜçüncü",
          "base": {"family": "Segoe UI", "size": 12},
          "runs": [{"k": "font", "v": ["Arial", 20, True, False], "r": ["1.0", "1.7"]},
                   {"k": "u", "v": None, "r": ["1.8", "1.13"]},
                   {"k": "fg", "v": "#e03131", "r": ["2.0", "2.6"]},
                   {"k": "bg", "v": "#ffe066", "r": ["2.7", "2.12"]},
                   {"k": "o", "v": None, "r": ["3.0", "3.6"]},
                   {"k": "al", "v": "center", "r": ["2.0", "3.0"]}]}
ed.from_qaz(tk_doc)
check("metin yüklendi", ed.toPlainText() == tk_doc["text"])
out = ed.to_qaz()
check("text aynı", out["text"] == tk_doc["text"] and out["base"] == tk_doc["base"])
by = {(r["k"], json_v if (json_v := (tuple(r["v"]) if isinstance(r["v"], list) else r["v"])) else None): r["r"] for r in out["runs"]}
check("font aralığı geri yazıldı", by.get(("font", ("Arial", 20, True, False))) == ["1.0", "1.7"])
check("altı çizili aralığı", by.get(("u", None)) == ["1.8", "1.13"])
check("yazı rengi", by.get(("fg", "#e03131")) == ["2.0", "2.6"])
check("vurgu rengi", by.get(("bg", "#ffe066")) == ["2.7", "2.12"])
check("üstü çizili", by.get(("o", None)) == ["3.0", "3.6"])
check("hizalama (satır 2)", by.get(("al", "center")) and by[("al", "center")][0] == "2.0")

# gidiş-dönüş: yazılan veriyi tekrar yükleyince aynı çıktı
ed2 = Editor()
ed2.from_qaz(out)
check("gidiş-dönüş aynı", ed2.to_qaz() == out)

# biçim uygulama
ed.load_plain("Bir iki üç dört")
c = ed.textCursor()
c.setPosition(4)
c.setPosition(7, QTextCursor.MoveMode.KeepAnchor)
ed.setTextCursor(c)
ed.toggle("bold")
check("kalın uygulandı", ed.style()["bold"])
ed.set_family("Courier New")
ed.set_size(30)
ed.set_color("fg", "#2b8a3e")
ed.set_color("bg", "#fff3bf")
st = ed.style()
check("aile/boyut/renk", st["family"] == "Courier New" and st["size"] == 30 and st["fg"] == "#2b8a3e" and st["bg"] == "#fff3bf")
ed.set_color("fg", None)
check("yazı rengi kaldırıldı", ed.style()["fg"] is None)
ed.clear_format()
check("biçim temizlendi", not ed.has_formatting())

# imleçte (seçimsiz) biçim: sonraki yazılan harfe uygulanır
ed.load_plain("")
ed.toggle("italic")
QTest.keyClicks(ed, "abc")
check("bekleyen biçim yazılan harfe uygulandı", ed.has_formatting() and ed.style()["italic"])

# hizalama
ed.load_plain("a\nb\nc")
c = ed.textCursor()
c.setPosition(2)
ed.setTextCursor(c)
ed.set_align("right")
q = ed.to_qaz()
check("hizalama kaydedildi", any(r["k"] == "al" and r["v"] == "right" for r in q["runs"]))

# yakınlaştırma
ed.load_plain("Büyütme denemesi " * 30)
QTest.qWait(30)
h100 = ed.document().size().height()
ed.set_zoom(200)
QTest.qWait(50)
h200 = ed.document().size().height()
check(f"zoom %200 belgeyi büyütür ({h100:.0f} -> {h200:.0f})", h200 > h100 * 1.5)
check("zoom biçim verisini değiştirmez", not ed.has_formatting())
ed.set_zoom(100)

# bul / değiştir
ed.load_plain("elma armut Elma kiraz elma")
check("tümünü vurgula (büyük/küçük duyarsız)", ed.highlight_all("elma", False) == 3)
check("büyük/küçük duyarlı", ed.highlight_all("elma", True) == 2)
check("ilk eşleşme bulundu", ed.find_step("elma", False) and ed.textCursor().selectedText().lower() == "elma")
check("ikinci eşleşme", ed.find_step("elma", False) and ed.textCursor().selectionStart() == 11)
n = ed.replace_all("elma", "portakal", False)
check("tümünü değiştir", n == 3 and ed.toPlainText() == "portakal armut portakal kiraz portakal")
ed.document().undo()
check("tümünü değiştir tek geri alma", ed.toPlainText() == "elma armut Elma kiraz elma")

# tam sözcük / regex / başa sarma
ed.load_plain("kar karpuz kara kar")
check("tam sözcük: 2 eşleşme", ed.highlight_all("kar", False, whole=True) == 2)
check("tam sözcük kapalı: 4 eşleşme", ed.highlight_all("kar", False) == 4)
check("regex: kar\\w+ 2 eşleşme", ed.highlight_all(r"kar\w+", False, regex=True) == 2)
check("geçersiz regex bildirilir", ed.highlight_all("(", False, regex=True) == 0 and ed.find_error)
c = ed.textCursor()
c.setPosition(ed.document().characterCount() - 1)
ed.setTextCursor(c)
check("başa sarma", ed.find_step("kar", False, whole=True) and ed.textCursor().selectionStart() == 0)
check("geri arama sona sarar", ed.find_step("kar", False, backward=True, whole=True)
      and ed.textCursor().selectionStart() == 16)
ed.load_plain("tarih 2026-11-03")
n = ed.replace_all(r"(\d+)-(\d+)-(\d+)", r"\3.\2.\1", False, regex=True)
check("regex değiştir (grup)", n == 1 and ed.toPlainText() == "tarih 03.11.2026")
ed.load_plain("Kar kar KAR")
check("tümünü değiştir (büyük/küçük duyarsız, tek geri alma)", ed.replace_all("kar", "x", False) == 3
      and ed.toPlainText() == "x x x")
ed.document().undo()
check("geri alındı", ed.toPlainText() == "Kar kar KAR")

# liste / girinti / satır aralığı / resim
from PySide6.QtGui import QImage, QColor  # noqa: E402
ed.load_plain("bir\niki\nüç\ndört")
ed.selectAll()
ed.toggle_list("disc")
check("madde işaretli liste", ed.list_style() == "disc" and all(b.textList() for b in ed._selected_blocks()))
q = ed.to_qaz()
check("liste .qaz'a yazıldı (blocks)", [b.get("list") for b in q["blocks"]] == ["disc"] * 4)
ed2 = Editor()
ed2.from_qaz(q)
ed2.selectAll()
check("liste geri yüklendi (tek liste)", ed2.list_style() == "disc"
      and len({id(b.textList().objectIndex()) if False else b.textList().format().style() for b in ed2._selected_blocks()}) == 1)
ed.toggle_list("disc")
check("listeden çıkarma", ed.list_style() is None and not ed.block_entries())
c = ed.textCursor()
c.setPosition(0)
ed.setTextCursor(c)
ed.change_indent(1)
ed.set_line_spacing(150)
be = ed.block_entries()
check("girinti + satır aralığı", be and be[0].get("i") == 1 and be[0].get("ls") == 150)
ed3 = Editor()
ed3.from_qaz(ed.to_qaz())
check("girinti/aralık geri yüklendi", ed3.block_entries() == be)
img = QImage(40, 20, QImage.Format.Format_ARGB32)
img.fill(QColor("#ff0000"))
ed.load_plain("öncesi sonrası")
c = ed.textCursor()
c.setPosition(7)
ed.setTextCursor(c)
check("resim eklendi", ed.insert_image(img) and len(ed.image_entries()) == 1)
q = ed.to_qaz()
check("resim .qaz'a yazıldı", len(q["images"]) == 1 and "\ufffc" in q["text"] and q["images"][0]["r"] == "1.7")
ed4 = Editor()
ed4.from_qaz(q)
check("resim geri yüklendi", len(ed4.image_entries()) == 1 and ed4.toPlainText() == q["text"])
check("biçim sayılır (resim/liste)", ed4.has_formatting())

# istatistik / satıra git
ed.load_plain("bir iki\nüç dört beş")
w, ch, sel, ln, col = ed.stats()
check(f"kelime/karakter sayımı ({w}, {ch})", w == 5 and ch == 19)
ed.goto_line(2)
check("satıra git", ed.textCursor().blockNumber() == 1)

print("SONUC:", sum(ok), "/", len(ok))
sys.stdout.flush()
os._exit(0 if all(ok) else 1)
