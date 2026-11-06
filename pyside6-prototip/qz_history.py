"""Belge geçmişi: her başarılı kayıtta belgenin bir kopyası saklanır; eski sürüme dönülebilir."""
import hashlib
import json
import os
import time
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem

import qv_engine as E
from qv_widgets import AButton

KEEP = 20


def folder(path):
    h = hashlib.sha1(os.path.normcase(os.path.abspath(path)).encode("utf-8")).hexdigest()[:16]
    d = os.path.join(E.DATA_DIR if hasattr(E, "DATA_DIR") else os.path.dirname(E.CONFIG), "versions", h)
    os.makedirs(d, exist_ok=True)
    return d


def snapshot(path, data):
    """Kayıt anının kopyasını yazar (en çok KEEP adet tutulur)."""
    try:
        d = folder(path)
        name = time.strftime("%Y%m%d-%H%M%S") + ".json"
        with open(os.path.join(d, name), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        files = sorted(x for x in os.listdir(d) if x.endswith(".json"))
        for old in files[:-KEEP]:
            os.remove(os.path.join(d, old))
        return True
    except OSError:
        return False


def versions(path):
    """[(zaman_damgası_metni, dosya_yolu, karakter_sayısı)] yeniden eskiye."""
    d = folder(path)
    out = []
    for fn in sorted((x for x in os.listdir(d) if x.endswith(".json")), reverse=True):
        fp = os.path.join(d, fn)
        try:
            ts = datetime.strptime(fn[:-5], "%Y%m%d-%H%M%S").strftime("%d.%m.%Y %H:%M:%S")
            with open(fp, "r", encoding="utf-8") as f:
                n = len(str(json.load(f).get("text", "")))
        except (OSError, ValueError):
            continue
        out.append((ts, fp, n))
    return out


class HistoryDialog(QDialog):
    """Seçilen sürümü döndürür (self.chosen = sözlük) ya da None."""

    def __init__(self, parent, path):
        super().__init__(parent)
        self.setWindowTitle("qaZNot - Belge Geçmişi")
        self.resize(460, 420)
        self.chosen = None
        lay = QVBoxLayout(self)
        t = QLabel(os.path.basename(path))
        t.setObjectName("qzbig")
        t.setStyleSheet("font-size: 16px;")
        lay.addWidget(t)
        s = QLabel("Her kayıtta bir kopya saklanır (en çok 20). Geri yüklenen sürüm kaydedilmeden önce değişmez.")
        s.setObjectName("qzmuted")
        s.setWordWrap(True)
        lay.addWidget(s)
        self.lst = QListWidget()
        for ts, fp, n in versions(path):
            it = QListWidgetItem(f"{ts}    ·    {n} karakter")
            it.setData(Qt.ItemDataRole.UserRole, fp)
            self.lst.addItem(it)
        if not self.lst.count():
            self.lst.addItem("Henüz kayıtlı sürüm yok.")
            self.lst.item(0).setFlags(Qt.ItemFlag.NoItemFlags)
        else:
            self.lst.setCurrentRow(0)
        self.lst.itemDoubleClicked.connect(lambda *_: self.pick())
        lay.addWidget(self.lst, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        b1 = AButton("Geri yükle")
        b1.setObjectName("qzprimary")
        b1.setFixedHeight(34)
        b1.clicked.connect(self.pick)
        b2 = AButton("Kapat")
        b2.setObjectName("qzfield")
        b2.setFixedHeight(34)
        b2.clicked.connect(self.reject)
        row.addWidget(b1)
        row.addWidget(b2)
        lay.addLayout(row)

    def pick(self):
        it = self.lst.currentItem()
        fp = it.data(Qt.ItemDataRole.UserRole) if it else None
        if not fp:
            return
        try:
            with open(fp, "r", encoding="utf-8") as f:
                self.chosen = json.load(f)
        except (OSError, ValueError):
            return
        self.accept()
