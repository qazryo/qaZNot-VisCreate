"""qaZNot yedekleme: belgeler, sürüm geçmişi ve ayarlar tek zip'e alınır; lisans ve Google bilgileri dahil edilmez."""
import json
import os
import zipfile
from datetime import datetime

import qv_engine as E

SECRET_KEYS = ("license", "license_enc")
MANIFEST = "qaznot-yedek.json"
FORMAT = 1


def _safe_settings():
    cfg = E.read_json(E.CONFIG)
    for k in SECRET_KEYS:
        cfg.pop(k, None)
    return cfg


def make_backup(zip_path, doc_paths, versions_dir):
    """doc_paths: yedeklenecek belge yolları. Dönen değer: (eklenen belge sayısı, atlanan belge sayısı)."""
    added, skipped = 0, 0
    names = {}
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in doc_paths:
            if not os.path.isfile(p):
                skipped += 1
                continue
            base = os.path.basename(p)
            if base in names:
                base = f"{names[base]}_{base}"
            names[base] = names.get(base, 0) + 1
            z.write(p, f"belgeler/{base}")
            added += 1
        if os.path.isdir(versions_dir):
            for root, _, files in os.walk(versions_dir):
                for fn in files:
                    full = os.path.join(root, fn)
                    rel = os.path.relpath(full, versions_dir).replace(os.sep, "/")
                    z.write(full, f"surumler/{rel}")
        z.writestr("ayarlar.json", json.dumps(_safe_settings(), ensure_ascii=False, indent=1))
        z.writestr(MANIFEST, json.dumps({"format": FORMAT, "app": "qaZNot", "date": datetime.now().isoformat(timespec="seconds"),
                                         "docs": added}, ensure_ascii=False))
    return added, skipped


def read_manifest(zip_path):
    try:
        with zipfile.ZipFile(zip_path) as z:
            return json.loads(z.read(MANIFEST).decode("utf-8"))
    except (OSError, KeyError, ValueError, zipfile.BadZipFile):
        return None


def restore_backup(zip_path, docs_dir, versions_dir):
    """Belgeleri docs_dir'e, geçmişi versions_dir'e çıkarır. Ayarlar yalnızca yeni alanları ekler; mevcut lisans korunur.
    Dönen değer: çıkarılan belge sayısı."""
    man = read_manifest(zip_path)
    if not man or man.get("app") != "qaZNot":
        raise ValueError("Geçerli bir qaZNot yedeği değil")
    os.makedirs(docs_dir, exist_ok=True)
    n = 0
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            name = info.filename
            if name.startswith("belgeler/") and not info.is_dir():
                dest = os.path.join(docs_dir, os.path.basename(name))
                root, ext = os.path.splitext(dest)
                i = 1
                while os.path.exists(dest):  # üzerine yazma: çakışan adı numaralandır
                    dest = f"{root} ({i}){ext}"
                    i += 1
                with open(dest, "wb") as f:
                    f.write(z.read(name))
                n += 1
            elif name.startswith("surumler/") and not info.is_dir():
                rel = name[len("surumler/"):]
                dest = os.path.join(versions_dir, *rel.split("/"))
                if os.path.exists(dest):
                    continue
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "wb") as f:
                    f.write(z.read(name))
        cfg_in = json.loads(z.read("ayarlar.json").decode("utf-8")) if "ayarlar.json" in z.namelist() else {}
    cfg = E.read_json(E.CONFIG)
    for k, v in cfg_in.items():
        if k not in SECRET_KEYS and k not in cfg:
            cfg[k] = v
    E.write_json(E.CONFIG, cfg)
    return n
