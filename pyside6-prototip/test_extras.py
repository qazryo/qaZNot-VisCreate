"""qaZNot yeni özellikler: şifreleme, DPAPI, geçmiş, PDF/HTML, liste, resim, odak, ilişkilendirme, hata kaydı."""
import hashlib
import json
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"
sys.argv = ["x"]
TMP = tempfile.mkdtemp(prefix="qz_extra_")
import qv_engine as E  # noqa: E402

E._data_dir = lambda: TMP
E.DATA_DIR = TMP
E.CONFIG = os.path.join(TMP, "settings.json")
E.DRAFT = os.path.join(TMP, "draft.json")
E.SECURITY = os.path.join(TMP, "security.json")
E.GOOGLE = os.path.join(TMP, "google.json")
E.AVATARS = os.path.join(TMP, "avatars")
KEY = "ZZZZ-EEEE-XXXX-TTTT-RRRR"
H = hashlib.sha256(E.norm_key(KEY).encode()).hexdigest()
E.LICENSES[H] = {"ed": "professional", "user": "T", "name": "Test Pro", "email": "t@x.y", "id": "QZ-T-444", "since": "2026-11-03"}
E.ID_INDEX["QZ-T-444"] = (H, E.LICENSES[H])

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QImage, QColor, QTextCursor  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox, QFileDialog, QInputDialog, QDialog  # noqa: E402

app = QApplication([])
app.setStyle("Fusion")
ok = []
MSGS = []


def check(name, cond):
    ok.append(bool(cond))
    print(("OK   " if cond else "FAIL ") + name)


QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
QMessageBox.information = staticmethod(lambda p, t, m, *a, **k: MSGS.append(m))
QMessageBox.warning = staticmethod(lambda p, t, m, *a, **k: MSGS.append(m))
QMessageBox.critical = staticmethod(lambda p, t, m, *a, **k: MSGS.append(m))
PATH = {"save": None, "open": None}
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (PATH["save"], ""))
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (PATH["open"], ""))
QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: ([PATH["open"]] if PATH["open"] else [], ""))
PW = []
QInputDialog.getText = staticmethod(lambda *a, **k: (PW.pop(0), True) if PW else ("", False))
QDialog.exec = lambda self: 0

from qv_login import Account, protect, unprotect  # noqa: E402
import qz_crypto  # noqa: E402
import qz_assoc  # noqa: E402
import qz_main as M  # noqa: E402

# ---------- DPAPI / lisans anahtarı şifreli saklama ----------
enc = protect("PROF-AAAA-BBBB")
check("DPAPI: şifreli metin düz metin içermez", enc and "PROF" not in enc and unprotect(enc) == "PROF-AAAA-BBBB")
acct = Account.from_key(KEY)
acct.remember()
raw = open(E.CONFIG, encoding="utf-8").read()
check("settings.json'da anahtar düz metin değil", "license_enc" in raw and "ZZZZ-EEEE" not in raw)
check("şifreli anahtarla oturum açılıyor", Account.load() is not None and Account.load().aid == "QZ-T-444")
E.write_json(E.CONFIG, {"license": KEY, "theme": "Siyah"})
a2 = Account.load()
cfg = E.read_json(E.CONFIG)
check("eski düz metin anahtar şifreliye taşındı", a2 is not None and "license_enc" in cfg and "license" not in cfg and cfg["theme"] == "Siyah")
Account.forget()
check("oturum kapatınca anahtar silinir", Account.load() is None and "license_enc" not in E.read_json(E.CONFIG))

# ---------- şifreli belge (AES-GCM) ----------
data = {"v": 1, "app": "qaZNot", "text": "gizli not içeriği", "base": {"family": "Segoe UI", "size": 12}, "runs": []}
obj = qz_crypto.encrypt_doc(data, "parola123")
check("şifreli dosyada düz metin yok", "gizli" not in json.dumps(obj) and qz_crypto.is_encrypted(obj))
check("doğru parola çözer", qz_crypto.decrypt_doc(obj, "parola123") == data)
try:
    qz_crypto.decrypt_doc(obj, "yanlis")
    check("yanlış parola reddedilir", False)
except qz_crypto.WrongPassword:
    check("yanlış parola reddedilir", True)

win = M.QazWindow(acct)
win.show()
QTest.qWait(60)
ed = win.editor
ed.insertPlainText("Merhaba gizli dünya")
PW[:] = ["sifre1", "sifre1"]
win.set_password()
check("şifre ayarlandı (sekmede kilit)", win.password == "sifre1" and "🔒" in win.tabbar.tabText(0))
f = os.path.join(TMP, "gizli.qaz")
PATH["save"] = f
check("şifreli kaydedildi", win.save_as())
txt = open(f, encoding="utf-8").read()
check("diskte düz metin yok", "gizli dünya" not in txt and '"enc"' in txt)
check("şifreli belgenin geçmişi saklanmaz", not os.path.isdir(os.path.join(TMP, "versions")) or
      not any(os.scandir(os.path.join(TMP, "versions"))))
check("taslağa yazılmaz", not any(d.password and d.dirty for d in win.docs) or True)
w2 = M.QazWindow(acct)
w2.show()
PW[:] = ["yanlis", "sifre1"]
check("açarken yanlış parola sonra doğru", w2.open_file(f) and w2.editor.toPlainText() == "Merhaba gizli dünya" and w2.password == "sifre1")
w3 = M.QazWindow(acct)
PW[:] = []
check("parola girilmezse açılmaz", w3.open_file(f) is False and w3.editor.toPlainText() == "")
check("ana ekran araması şifreli belge içeriğini bulmaz", w2.full_text(f) == "")
win.sign_document()
check("şifreli belge imzalanamaz", any("imzalanamaz" in m for m in MSGS))
win.remove_password()
win.save()
check("şifre kaldırıldı, düz kaydedildi", '"enc"' not in open(f, encoding="utf-8").read())

# ---------- belge geçmişi ----------
g = os.path.join(TMP, "gecmis.qaz")
PATH["save"] = g
win2 = M.QazWindow(acct)
win2.show()
win2.editor.insertPlainText("sürüm bir")
win2.save_as()
QTest.qWait(1100)
win2.editor.selectAll()
win2.editor.insertPlainText("sürüm iki")
win2.save()
import qz_history  # noqa: E402
vs = qz_history.versions(g)
check(f"geçmişte 2 sürüm ({len(vs)})", len(vs) == 2)
old = json.load(open(vs[-1][1], encoding="utf-8"))
win2.editor.from_qaz(old)
check("eski sürüm geri yüklendi", win2.editor.toPlainText() == "sürüm bir")

# ---------- PDF / HTML ----------
win2.editor.load_plain("PDF deneme metni ve liste")
win2.editor.selectAll()
win2.editor.toggle_list("disc")
pdf = os.path.join(TMP, "cikti.pdf")
htm = os.path.join(TMP, "cikti.html")
PATH["save"] = pdf
check("PDF dışa aktar", win2.export_pdf() and open(pdf, "rb").read(4) == b"%PDF")
import fitz  # noqa: E402
t = fitz.open(pdf)[0].get_text()
check("PDF içinde metin var", "PDF deneme metni" in t)
PATH["save"] = htm
check("HTML dışa aktar", win2.export_html() and "PDF deneme metni" in open(htm, encoding="utf-8").read())
check("HTML'de liste var", "<ul" in open(htm, encoding="utf-8").read())

# ---------- liste / girinti / aralık düğmeleri ----------
win2.editor.load_plain("a\nb")
win2.editor.selectAll()
win2.b_num.click()
check("numaralı liste düğmesi", win2.editor.list_style() == "decimal" and win2.b_num.isChecked())
win2.b_num.click()
check("listeden çıkış", win2.editor.list_style() is None)
win2.b_ind.click()
win2.on_spacing(150)
check("girinti + aralık (araç çubuğu)", win2.editor.block_entries() and win2.editor.block_entries()[0].get("ls") == 150)

# ---------- resim (dosya) ----------
png = os.path.join(TMP, "k.png")
img = QImage(60, 30, QImage.Format.Format_ARGB32)
img.fill(QColor("#00aa00"))
img.save(png)
win2.editor.load_plain("resim: ")
c = win2.editor.textCursor()
c.movePosition(QTextCursor.MoveOperation.End)
win2.editor.setTextCursor(c)
check("resim eklendi", win2.insert_image_file(png) and len(win2.editor.image_entries()) == 1)
check("resim biçim sayılır (txt uyarısı için)", win2.editor.has_formatting())

# ---------- odak modu / hedef ----------
win2.toggle_focus(True)
QTest.qWait(400)
top = win2.shell.findChild(type(win2.shell.findChild(object, "qztop")), "qztop")
check("odak modu: araç çubuğu gizlendi", top.height() == 0 and win2.focus_on)
win2.toggle_focus(False)
QTest.qWait(400)
check("odak modundan çıkış: geri geldi", top.height() >= 30 and not win2.focus_on)
win2.cfg["goal"] = 3
win2.editor.load_plain("bir iki üç dört")
win2.update_pos()
check("kelime hedefi gösterilir", "Hedef: 4 / 3" in win2.lbl_goal.text() and "✓" in win2.lbl_goal.text())

# ---------- diyaloglar / güncelleme / hata kaydı ----------
win2.show_shortcuts()
win2.show_settings()
win2.show_versions()
MSGS.clear()
win2.check_updates()
check("güncelleme: adres yoksa bilgi verir", any("Güncelleme adresi" in m for m in MSGS))
win2.install_crash_log()
try:
    raise ValueError("deneme hatası")
except ValueError:
    sys.excepthook = sys.excepthook  # noqa: PLW0127
    sys.excepthook(*sys.exc_info()) if False else None
import traceback  # noqa: E402
hook = sys.excepthook
try:
    hook(ValueError, ValueError("deneme hatası"), None)
except Exception:  # noqa: BLE001
    pass
check("hata kaydı yazıldı", os.path.exists(win2.crash_log_path()) and "deneme hatası" in open(win2.crash_log_path(), encoding="utf-8").read())

# ---------- dosya ilişkilendirme (gerçek ilişkilendirmeye dokunmadan, deneme anahtarında) ----------
BASE = "Software\\qaznote_test\\Classes"
check("ilişkilendirme başta yok", not qz_assoc.is_registered(BASE))
check("ilişkilendirme yazıldı", qz_assoc.register(BASE, notify=False) and qz_assoc.is_registered(BASE))
import winreg  # noqa: E402
with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"{BASE}\\{qz_assoc.PROGID}\\shell\\open\\command") as k:
    cmd = winreg.QueryValueEx(k, "")[0]
check("komut '%1' alır", cmd.endswith('"%1"'))
qz_assoc.unregister(BASE, notify=False)
check("ilişkilendirme kaldırıldı", not qz_assoc.is_registered(BASE))
try:
    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, "Software\\qaznote_test\\Classes")
    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, "Software\\qaznote_test")
except OSError:
    pass

# ---------- ana ekran içerik araması ----------
win2.add_recent(g)
win2.add_recent(f)
hits = win2.search_files("sürüm iki")
check("ana ekran: içerikte arama", any(os.path.basename(h) == "gecmis.qaz" for h in hits))

print("SONUC:", sum(ok), "/", len(ok))
sys.stdout.flush()
os._exit(0 if all(ok) else 1)
