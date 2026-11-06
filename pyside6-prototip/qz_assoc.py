""".qaz dosya ilişkilendirme (yalnızca geçerli kullanıcı: HKCU\\Software\\Classes). Yönetici izni gerekmez."""
import os
import sys

PROGID = "qaZNot.Document"
EXT = ".qaz"


def open_command():
    """'%1' ile dosya yolunu alan komut satırı (exe ya da pythonw + betik)."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" "%1"'
    import shutil
    py = shutil.which("pythonw") or sys.executable
    script = os.path.abspath(sys.argv[0])
    return f'"{py}" "{script}" "%1"'


def icon_path():
    if getattr(sys, "frozen", False):
        return f"{sys.executable},0"
    ico = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icon.ico")
    return ico if os.path.exists(ico) else ""


def _set(winreg, base, path, value, name=""):
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, f"{base}\\{path}", 0, winreg.KEY_WRITE) as k:
        winreg.SetValueEx(k, name, 0, winreg.REG_SZ, value)


def register(base="Software\\Classes", notify=True):
    """.qaz uzantısını qaZNot'a bağlar. Başarılıysa True."""
    if os.name != "nt":
        return False
    import winreg
    try:
        _set(winreg, base, EXT, PROGID)
        _set(winreg, base, PROGID, "qaZNot belgesi")
        ic = icon_path()
        if ic:
            _set(winreg, base, f"{PROGID}\\DefaultIcon", ic)
        _set(winreg, base, f"{PROGID}\\shell\\open\\command", open_command())
    except OSError:
        return False
    if notify:
        _notify()
    return True


def unregister(base="Software\\Classes", notify=True):
    if os.name != "nt":
        return False
    import winreg

    def rm(path):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"{base}\\{path}", 0, winreg.KEY_ALL_ACCESS) as k:
                while True:
                    try:
                        sub = winreg.EnumKey(k, 0)
                    except OSError:
                        break
                    rm(f"{path}\\{sub}")
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"{base}\\{path}")
        except OSError:
            pass
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"{base}\\{EXT}") as k:
            if winreg.QueryValueEx(k, "")[0] == PROGID:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"{base}\\{EXT}")
    except OSError:
        pass
    rm(PROGID)
    if notify:
        _notify()
    return True


def is_registered(base="Software\\Classes"):
    if os.name != "nt":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"{base}\\{EXT}") as k:
            if winreg.QueryValueEx(k, "")[0] != PROGID:
                return False
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"{base}\\{PROGID}\\shell\\open\\command") as k:
            return winreg.QueryValueEx(k, "")[0] == open_command()
    except OSError:
        return False


def _notify():
    try:
        import ctypes
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)  # SHCNE_ASSOCCHANGED
    except Exception:  # noqa: BLE001
        pass
