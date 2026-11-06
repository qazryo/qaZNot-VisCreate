"""qaZNot - PySide6 sürümü. Çalıştır:  pythonw qaznote_qt.py [dosya]
Açılış: giriş (gerekirse) -> başlangıç ekranı (menü) -> not defteri. qAnvas buradan açılır."""
import os
import sys

if "--shot" in sys.argv:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("qaznote.app")
    except Exception:  # noqa: BLE001
        pass

from PySide6.QtCore import QTimer
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QDialog

from qv_login import Account, AccountDialog
from qv_widgets import window_fade_in


def fake_account(ed="professional"):
    acc = dict(ed=ed, user="Test", name="Test kullanıcısı", email="test@qaz.local.net", id="QZ-T-000", since="2026-11-03")
    return Account("TEST-0000-0000-0000-0000", acc)


def main():
    args = sys.argv[1:]
    app = QApplication(sys.argv)
    app.setApplicationName("qaZNot")
    app.setStyle("Fusion")
    inst = os.environ.get("QZ_INSTANCE", "qaznote-pyside6")
    fake_ed = args[args.index("--fake") + 1] if "--fake" in args else os.environ.get("QZ_FAKE")
    single = not any(a in args for a in ("--multi", "--shot"))
    if single:  # zaten açıksa yenisini açma: var olan pencereyi öne getir, dosyaları ona ilet
        sk = QLocalSocket()
        sk.connectToServer(inst)
        if sk.waitForConnected(400):
            paths = [os.path.abspath(a) for a in args if not a.startswith("--") and os.path.isfile(a)]
            sk.write(("OPEN\n" + "\n".join(paths) if paths else "FOCUS").encode("utf-8"))
            sk.flush()
            sk.waitForBytesWritten(800)
            sk.disconnectFromServer()
            return 0
    if fake_ed:
        acct = fake_account(fake_ed)
    else:
        acct = Account.load()
        if acct is None:
            dlg = AccountDialog(None, required=True)
            if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.acct:
                return 0
            acct = dlg.acct
    files = [os.path.abspath(a) for a in args if not a.startswith("--") and os.path.isfile(a)]
    from qz_main import QazWindow
    win = QazWindow(acct, files or None)
    win.show()
    if not fake_ed:
        win.install_crash_log()
    if single:
        server = QLocalServer(win)
        QLocalServer.removeServer(inst)
        server.listen(inst)

        def on_conn():
            c = server.nextPendingConnection()
            c.waitForReadyRead(500)
            msg = bytes(c.readAll()).decode("utf-8", "replace")
            c.disconnectFromServer()
            win.bring_to_front()
            paths = [p for p in msg.split("\n")[1:] if p] if msg.startswith("OPEN") else []
            for p in paths:
                win.open_file(p)
            if paths:
                win.hide_home()
        server.newConnection.connect(on_conn)
        win._server = server
    if "--shot" in args:
        out = args[args.index("--shot") + 1]
        page = args[args.index("--page") + 1] if "--page" in args else "home"

        def shot():
            if page == "home":
                win.show_home(False)
            else:
                win.hide_home()
            QTimer.singleShot(500, lambda: (win.grab().save(out), app.quit()))
        QTimer.singleShot(600, shot)
    else:
        window_fade_in(win, 420)
        QTimer.singleShot(150, lambda: win.after_login(True))
        if os.environ.get("QZ_DEBUG_EXIT_MS"):  # yalnızca test için
            def dbg():
                print("DOCS=", [d.filename for d in win.docs], flush=True)
                for d in win.docs:
                    d.dirty = False
                app.quit()
            QTimer.singleShot(int(os.environ["QZ_DEBUG_EXIT_MS"]), dbg)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
