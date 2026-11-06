"""qaZNot yedekleme testi: belge + geçmiş + ayar yedeği, lisans dışarıda, geri yükleme, çakışma."""
import json
import os
import sys
import tempfile

sys.argv = ["x"]
TMP = tempfile.mkdtemp(prefix="qz_backup_")
import qv_engine as E  # noqa: E402

E.DATA_DIR = TMP
E.CONFIG = os.path.join(TMP, "settings.json")
import qz_backup  # noqa: E402

ok = []


def check(name, cond):
    ok.append(bool(cond))
    print(("OK   " if cond else "FAIL ") + name)


src = os.path.join(TMP, "kaynak")
os.makedirs(src)
a = os.path.join(src, "not.txt")
open(a, "w", encoding="utf-8").write("birinci")
b = os.path.join(src, "sifreli.qaz")
json.dump({"v": 1, "enc": {"alg": "AES-256-GCM"}}, open(b, "w", encoding="utf-8"))
ver = os.path.join(TMP, "versions", "abc")
os.makedirs(ver)
json.dump({"text": "eski"}, open(os.path.join(ver, "20260101-100000.json"), "w", encoding="utf-8"))
E.write_json(E.CONFIG, {"theme": "Siyah", "license_enc": "SECRET", "license": "PROF-XXXX", "wrap": False})

zp = os.path.join(TMP, "yedek.zip")
n, skipped = qz_backup.make_backup(zp, [a, b, os.path.join(src, "yok.txt")], os.path.join(TMP, "versions"))
check("iki belge yedeklendi", n == 2)
check("eksik belge atlandı", skipped == 1)
man = qz_backup.read_manifest(zp)
check("manifest doğru", man and man["app"] == "qaZNot" and man["docs"] == 2)
import zipfile  # noqa: E402

with zipfile.ZipFile(zp) as z:
    names = z.namelist()
    cfg_in_zip = json.loads(z.read("ayarlar.json"))
check("zip içinde belgeler ve geçmiş var", "belgeler/not.txt" in names and "surumler/abc/20260101-100000.json" in names)
check("lisans yedeğe girmedi", "license" not in cfg_in_zip and "license_enc" not in cfg_in_zip and cfg_in_zip.get("theme") == "Siyah")
check("zip içinde düz anahtar metni yok", b"PROF-XXXX" not in open(zp, "rb").read())

dst = os.path.join(TMP, "geri")
E.write_json(E.CONFIG, {"license_enc": "YENI", "theme": "Beyaz"})
k = qz_backup.restore_backup(zp, dst, os.path.join(TMP, "versions2"))
check("iki belge geri geldi", k == 2 and open(os.path.join(dst, "not.txt"), encoding="utf-8").read() == "birinci")
check("geçmiş geri geldi", os.path.exists(os.path.join(TMP, "versions2", "abc", "20260101-100000.json")))
cfg = E.read_json(E.CONFIG)
check("mevcut lisans korundu, tema değişmedi", cfg.get("license_enc") == "YENI" and cfg.get("theme") == "Beyaz")
check("yeni ayar alanı eklendi", cfg.get("wrap") is False)

qz_backup.restore_backup(zp, dst, os.path.join(TMP, "versions2"))
check("çakışan adlar üzerine yazılmadı", os.path.exists(os.path.join(dst, "not (1).txt")))

bad = os.path.join(TMP, "bozuk.zip")
open(bad, "wb").write(b"bu zip degil")
check("bozuk yedek reddedilir", qz_backup.read_manifest(bad) is None)
try:
    qz_backup.restore_backup(bad, dst, TMP)
    check("bozuk yedek hata verir", False)
except ValueError:
    check("bozuk yedek hata verir", True)

print("SONUC:", sum(ok), "/", len(ok))
sys.stdout.flush()
os._exit(0 if all(ok) else 1)
