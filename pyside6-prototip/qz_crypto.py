"""Şifreli .qaz belgeleri: parola -> scrypt -> AES-256-GCM. Parola dosyaya yazılmaz."""
import base64
import json
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

AAD = b"qaZNot-v1"
N, R, P = 2 ** 15, 8, 1


class WrongPassword(Exception):
    pass


def _key(password, salt, n=N, r=R, p=P):
    return Scrypt(salt=salt, length=32, n=n, r=r, p=p).derive(password.encode("utf-8"))


def encrypt_doc(data, password):
    """data: .qaz sözlüğü. Döndürür: dosyaya yazılacak sözlük (düz metin içermez)."""
    salt, nonce = os.urandom(16), os.urandom(12)
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ct = AESGCM(_key(password, salt)).encrypt(nonce, raw, AAD)
    b = lambda x: base64.b64encode(x).decode("ascii")  # noqa: E731
    return {"v": 1, "app": "qaZNot",
            "enc": {"alg": "AES-256-GCM", "kdf": "scrypt", "n": N, "r": R, "p": P,
                    "salt": b(salt), "nonce": b(nonce), "ct": b(ct)}}


def is_encrypted(obj):
    return isinstance(obj, dict) and isinstance(obj.get("enc"), dict)


def decrypt_doc(obj, password):
    e = obj["enc"]
    try:
        salt, nonce, ct = (base64.b64decode(e[k]) for k in ("salt", "nonce", "ct"))
        key = _key(password, salt, int(e.get("n", N)), int(e.get("r", R)), int(e.get("p", P)))
        raw = AESGCM(key).decrypt(nonce, ct, AAD)
    except InvalidTag:
        raise WrongPassword("Şifre yanlış ya da dosya bozuk")
    except (KeyError, ValueError, TypeError):
        raise ValueError("Şifreli belge bozuk")
    return json.loads(raw.decode("utf-8"))
