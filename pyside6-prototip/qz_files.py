"""qaZNot dosya işlemleri: aç / kaydet (.qaz ve .txt), taslak, son/sabitlenen dosyalar, imza, yazdırma."""
import json
import os
import tempfile
from datetime import datetime

from PySide6.QtWidgets import QFileDialog, QMessageBox, QInputDialog, QLineEdit

import qv_engine as E
import qz_crypto
import qz_history

APP = "qaZNot"


class FilesMixin:
    # ---------- ortak ----------
    def info(self, text):
        QMessageBox.information(self, APP, text)

    def error(self, text):
        QMessageBox.critical(self, APP, text)

    def confirm_save(self):
        """Kaydedilmemiş değişiklik varsa sorar. True: devam edilebilir."""
        if not self.dirty:
            return True
        name = os.path.basename(self.filename) if self.filename else "Adsız"
        r = QMessageBox.question(self, APP, f"Değişiklikleri {name} dosyasına kaydetmek istiyor musunuz?",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No |
                                 QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Yes:
            return bool(self.save())
        return r == QMessageBox.StandardButton.No

    def set_clean(self):
        self.editor.document().setModified(False)
        self.dirty = False
        self.update_title()

    # ---------- yeni / aç ----------
    def new_file(self):
        """Yeni boş sekme açar."""
        self.add_doc()
        return True

    def open_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Aç", "", "Tüm desteklenenler (*.qaz *.txt);;qaZNot Belgesi (*.qaz);;Metin Belgeleri (*.txt);;Tüm Dosyalar (*.*)")
        if isinstance(paths, str):
            paths = [paths] if paths else []
        ok = False
        for p in paths:
            ok = self.open_file(p) or ok
        return ok

    def open_recent(self, path):
        self.open_file(path)

    def open_file(self, path):
        """Dosyayı sekmede açar: zaten açıksa o sekmeye geçer, boş sekme varsa onu kullanır, yoksa yeni sekme açar."""
        path = os.path.abspath(path)
        d = self.find_doc(path)
        if d is not None:
            self.switch_to(d)
            self.open_count += 1
            if not d.dirty:  # değişiklik yoksa diskteki güncel hâlini yükle
                return self._load_file(path)
            return True
        reuse = self.cur_doc.is_blank()
        d = self.cur_doc if reuse else self.add_doc()
        self.switch_to(d)
        if not self._load_file(path):
            if not reuse:
                self.close_doc(d)
            return False
        return True

    def _load_file(self, path):
        try:
            if path.lower().endswith(".qaz"):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                pw = None
                if qz_crypto.is_encrypted(data):
                    data, pw = self._ask_decrypt(data, path)
                    if data is None:
                        return False
                if not isinstance(data, dict) or "text" not in data:
                    raise ValueError("Geçerli bir qaZNot belgesi değil")
                self.editor.from_qaz(data)
                self.password = pw
                if data.get("base"):
                    self.save_settings()
                self.fmt, self.encoding = "qaz", "utf-8"
                ok, sig = E.verify_signature(data)
                self.sig_raw, self.sig_ok = (sig, ok) if ok is not None else (None, None)
            else:
                with open(path, "rb") as f:
                    raw = f.read()
                if raw.startswith(b"\xef\xbb\xbf"):
                    text, enc = raw.decode("utf-8-sig"), "utf-8-sig"
                else:
                    try:
                        text, enc = raw.decode("utf-8"), "utf-8"
                    except UnicodeDecodeError:
                        text, enc = raw.decode("cp1254", errors="replace"), "cp1254"
                self.editor.load_plain(text.replace("\r\n", "\n").replace("\r", "\n"))
                self.fmt, self.encoding, self.sig_raw, self.sig_ok = "txt", enc, None, None
                self.password = None
        except (OSError, ValueError) as e:
            self.error(f"Dosya açılamadı:\n{e}")
            return False
        self.filename, self.plain_ok = path, False
        self.add_recent(path)
        self.set_clean()
        self.open_count += 1
        self.apply_zoom_ui()
        return True

    # ---------- kaydet ----------
    def save(self):
        if not self.filename:
            return self.save_as()
        return self._write(self.filename)

    def save_as(self):
        rich = self.fmt == "qaz" or self.editor.has_formatting()
        q, t = "qaZNot Belgesi (*.qaz)", "Düz Metin (*.txt)"
        flt = ";;".join(([q, t] if rich else [t, q]) + ["Tüm Dosyalar (*.*)"])
        init = os.path.splitext(os.path.basename(self.filename))[0] if self.filename else ""
        path, _ = QFileDialog.getSaveFileName(self, "Farklı Kaydet", init, flt)
        if not path:
            return False
        if not os.path.splitext(path)[1]:
            path += ".qaz" if rich else ".txt"
        self.plain_ok = False
        return self._write(path)

    def _write(self, path):
        try:
            if self.password and not path.lower().endswith(".qaz"):
                path = os.path.splitext(path)[0] + ".qaz"  # şifre yalnızca .qaz belgelerinde
            if path.lower().endswith(".qaz"):
                data = self.editor.to_qaz()
                out = qz_crypto.encrypt_doc(data, self.password) if self.password else data
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(out, f, ensure_ascii=False)
                self.fmt, self.sig_raw, self.sig_ok = "qaz", None, None
                if not self.password:
                    qz_history.snapshot(path, data)
            else:
                if self.editor.has_formatting() and not self.plain_ok:
                    r = QMessageBox.question(
                        self, APP, "Biçimlendirme (yazı tipleri, renkler vb.) düz metin dosyasında saklanamaz.\n\n"
                                   "Evet: Yine de düz metin olarak kaydet\nHayır: .qaz olarak kaydet\nİptal: Vazgeç",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
                    if r == QMessageBox.StandardButton.Cancel:
                        return False
                    if r == QMessageBox.StandardButton.No:
                        return self._write(os.path.splitext(path)[0] + ".qaz")
                    self.plain_ok = True
                with open(path, "w", encoding=self.encoding, errors="replace") as f:
                    f.write(self.editor.toPlainText())
                self.fmt = "txt"
                qz_history.snapshot(path, self.editor.to_qaz())
        except OSError as e:
            self.error(f"Dosya kaydedilemedi:\n{e}")
            return False
        self.filename = path
        self.add_recent(path)
        self.set_clean()
        self.write_draft()
        self.toast("Kaydedildi")
        return True

    # ---------- taslak ----------
    def write_draft(self):
        """Kaydedilmemiş tüm sekmeleri taslağa yazar (şifreli belgeler düz metin olarak yazılmaz)."""
        if self.testing:
            return
        now = datetime.now().isoformat(timespec="seconds")
        items = [{"file": d.filename, "saved": now, "data": d.editor.to_qaz()}
                 for d in self.docs if d.dirty and not d.password]
        if items:
            E.write_json(E.DRAFT, {"docs": items})
        else:
            self.drop_draft()

    def drop_draft(self):
        if self.testing:
            return
        for p in (E.DRAFT, E.DRAFT + ".bak", E.DRAFT + ".tmp"):
            try:
                os.remove(p)
            except OSError:
                pass

    def restore_draft(self):
        raw = E.read_json(E.DRAFT)
        items = raw.get("docs") if isinstance(raw.get("docs"), list) else ([raw] if raw.get("data") else [])
        items = [i for i in items if isinstance(i, dict) and isinstance(i.get("data"), dict) and "text" in i["data"]]
        if not items:
            return False
        if len(items) == 1:
            name = os.path.basename(items[0]["file"]) if items[0].get("file") else "Adsız"
            q = f"Kaydedilmemiş bir çalışma bulundu ({name}, {items[0].get('saved', '')}).\nGeri yüklensin mi?"
        else:
            q = f"Kaydedilmemiş {len(items)} çalışma bulundu.\nGeri yüklensin mi?"
        r = QMessageBox.question(self, APP, q)
        if r != QMessageBox.StandardButton.Yes:
            self.drop_draft()
            return False
        ok = False
        for it in items:
            d = self.cur_doc if self.cur_doc.is_blank() else self.add_doc()
            self.switch_to(d)
            try:
                self.editor.from_qaz(it["data"])
            except (KeyError, ValueError, TypeError) as e:
                self.error(f"Taslak yüklenemedi:\n{e}")
                continue
            f = it.get("file")
            self.filename = f if f and os.path.exists(f) else None
            self.fmt, self.encoding = "qaz", "utf-8"
            self.editor.document().setModified(True)
            self.dirty = True
            self.update_title()
            ok = True
        return ok

    # ---------- son / sabitlenen ----------
    def add_recent(self, path):
        path = os.path.abspath(path)
        lst = [p for p in self.cfg.get("recent_files", []) if p != path]
        self.cfg["recent_files"] = ([path] + lst)[:30]
        self.save_settings()

    def cfg_pinned(self):
        return list(self.cfg.get("pinned", []))

    def toggle_pin(self, path):
        pins = [p for p in self.cfg_pinned() if p != path]
        if path not in self.cfg_pinned():
            pins.insert(0, path)
        self.cfg["pinned"] = pins[:24]
        self.save_settings()

    def remove_entry(self, path):
        self.cfg["recent_files"] = [p for p in self.cfg.get("recent_files", []) if p != path]
        self.cfg["pinned"] = [p for p in self.cfg_pinned() if p != path]
        self.save_settings()
        self.toast("Listeden kaldırıldı")

    def home_entries(self):
        pins = [p for p in self.cfg_pinned() if os.path.isfile(p)]
        rec = [p for p in self.cfg.get("recent_files", []) if os.path.isfile(p) and p not in pins]
        return pins, rec

    _ft = {}

    def full_text(self, path):
        """Dosyanın tüm metni (arama için; mtime ile önbelleklenir). Okunamayan/şifreli dosya: boş."""
        try:
            key = (path, os.path.getmtime(path))
        except OSError:
            return ""
        if key in self._ft:
            return self._ft[key]
        txt = ""
        try:
            if path.lower().endswith(".qaz"):
                with open(path, "r", encoding="utf-8") as f:
                    txt = str(json.load(f).get("text", ""))
            else:
                with open(path, "rb") as f:
                    raw = f.read(3_000_000)
                for enc in ("utf-8-sig", "cp1254"):
                    try:
                        txt = raw.decode(enc)
                        break
                    except UnicodeDecodeError:
                        continue
        except Exception:  # noqa: BLE001
            txt = ""
        if len(self._ft) > 600:
            self._ft.clear()
        self._ft[key] = txt
        return txt

    def search_files(self, q):
        """Son/sabitlenen belgelerde ve bunların klasörlerindeki .qaz/.txt dosyalarında ad ya da içerik araması."""
        q = q.strip().lower()
        if not q:
            return []
        pins, rec = self.home_entries()
        cand, seen, folders = [], set(), []
        for p in pins + rec:
            if p not in seen:
                seen.add(p)
                cand.append(p)
            d = os.path.dirname(p)
            if d not in folders:
                folders.append(d)
        if self.default_dir() not in folders:
            folders.append(self.default_dir())
        for d in folders[:8]:
            try:
                for fn in os.listdir(d):
                    fp = os.path.join(d, fn)
                    if fn.lower().endswith((".qaz", ".txt")) and fp not in seen and os.path.isfile(fp):
                        seen.add(fp)
                        cand.append(fp)
            except OSError:
                pass
        out = [p for p in cand[:400] if q in os.path.basename(p).lower() or q in self.full_text(p).lower()]
        out.sort(key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0, reverse=True)
        return out

    def default_dir(self):
        d = os.path.join(os.path.expanduser("~"), "Documents")
        return d if os.path.isdir(d) else os.path.expanduser("~")

    def open_folder(self, folder):
        try:
            os.startfile(folder)  # noqa: S606
        except (OSError, AttributeError):
            self.toast("Klasör açılamadı")

    # ---------- imza ----------
    def sign_document(self):
        if not self.need_feature("signing", "Belge imzalama yalnızca Professional sürümünde"):
            return
        if self.password:
            self.info("Şifreli belgeler imzalanamaz. Önce şifreyi kaldırın.")
            return
        if not self.filename or not self.filename.lower().endswith(".qaz") or self.dirty:
            self.info("İmzalamak için belgeyi önce .qaz olarak kaydedin\n(Dosya > Farklı Kaydet) ve değişiklik bırakmayın.")
            return
        try:
            data = self.editor.to_qaz()
            h, acc = E.lookup_license(self.acct.key)
            data["sig"] = E.make_signature(data, h, acc)
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except OSError as e:
            self.error(f"İmzalanamadı:\n{e}")
            return
        self.sig_raw, self.sig_ok = data["sig"], True
        self.update_title()
        self.toast("Belge imzalandı ✓")

    def verify_document(self):
        if not self.filename or not self.filename.lower().endswith(".qaz"):
            self.info("İmza yalnızca kaydedilmiş .qaz belgelerinde doğrulanabilir.")
            return
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            self.error(f"Dosya okunamadı:\n{e}")
            return
        ok, sig = E.verify_signature(data)
        if ok is None:
            self.info("Bu belge imzalı değil.")
        elif ok:
            ed = E.EDITIONS.get(sig.get("edition"), {}).get("label", sig.get("edition", ""))
            msg = (f"✓ İmza geçerli.\n\nİmzalayan: {sig.get('name', '')} ({sig.get('id', '')})\n"
                   f"Sürüm: {ed}\nTarih: {sig.get('time', '')}")
            if self.dirty:
                msg += "\n\nNot: Ekrandaki belgede kaydedilmemiş değişiklikler var."
            self.info(msg)
        else:
            QMessageBox.warning(self, APP, "⚠ İmza geçersiz: belge imzalandıktan sonra değiştirilmiş ya da imza tanınmıyor.")

    # ---------- yazdır ----------
    def print_file(self):
        if os.name != "nt":
            self.info("Yazdırma yalnızca Windows'ta desteklenir.")
            return
        try:
            fd, tmp = tempfile.mkstemp(suffix=".txt")
            with os.fdopen(fd, "w", encoding="utf-8-sig") as f:
                f.write(self.editor.toPlainText())
            os.startfile(tmp, "print")  # noqa: S606
        except OSError as e:
            self.error(f"Yazdırılamadı:\n{e}")

    # ---------- şifre ----------
    def _ask_decrypt(self, obj, path):
        for _ in range(3):
            pw, ok = QInputDialog.getText(self, APP, f"{os.path.basename(path)} şifreli.\nŞifreyi girin:",
                                          QLineEdit.EchoMode.Password)
            if not ok:
                return None, None
            try:
                return qz_crypto.decrypt_doc(obj, pw), pw
            except qz_crypto.WrongPassword:
                self.error("Şifre yanlış.")
            except ValueError as e:
                self.error(str(e))
                return None, None
        return None, None

    def set_password(self):
        pw, ok = QInputDialog.getText(self, APP, "Yeni şifre:\n(Unutursanız belge açılamaz, kurtarma yolu yoktur.)",
                                      QLineEdit.EchoMode.Password)
        if not ok or not pw:
            return
        pw2, ok = QInputDialog.getText(self, APP, "Şifreyi tekrar girin:", QLineEdit.EchoMode.Password)
        if not ok:
            return
        if pw != pw2:
            self.error("Şifreler uyuşmuyor.")
            return
        self.password = pw
        self.editor.document().setModified(True)
        self.refresh_tab(self.cur_doc)
        self.toast("Şifre ayarlandı - kaydedince belge şifrelenir")

    def remove_password(self):
        if not self.password:
            self.info("Bu belgenin şifresi yok.")
            return
        self.password = None
        self.editor.document().setModified(True)
        self.refresh_tab(self.cur_doc)
        self.toast("Şifre kaldırıldı - kaydedince belge şifresiz olur")

    # ---------- belge geçmişi ----------
    def show_history(self):
        if self.password:
            self.info("Şifreli belgelerin geçmişi saklanmaz (güvenlik için).")
            return
        if not self.filename:
            self.info("Geçmiş için belgeyi önce kaydedin.")
            return
        dlg = qz_history.HistoryDialog(self, self.filename)
        if dlg.exec() and dlg.chosen:
            self.editor.from_qaz(dlg.chosen)
            self.editor.document().setModified(True)
            self.toast("Sürüm geri yüklendi - kaydetmek için Ctrl+S")
