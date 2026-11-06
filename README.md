# qaZNot VisCreate

A themed, rich-text **note editor** (qaZNot) with a built-in **design editor** (qAnvas).

> Version: `0.3_061126_var1` · Codename: **VisCreate** · Status: pre-release (not yet released)

## Features

### Note editor (qaZNot)
- Rich text: font, size, bold/italic/underline, color, alignment, bulleted and numbered lists, indentation, line spacing.
- Insert images into notes (paste, drag and drop, or from the menu).
- Find and replace: whole word, regular expressions (with `\1` group support), wrap-around. Search inside document contents from the home screen.
- Tabbed workspace: multiple documents in one window (Ctrl+N new tab, Ctrl+W close, Ctrl+Tab switch).
- Document history: a copy is kept on every save (up to 20), and you can restore any previous version.
- Draft recovery: unsaved changes are restored after a crash or close.
- Document encryption (AES-256-GCM, key derived from the password with scrypt). The history and drafts of an encrypted document are never stored as plain text.
- Backup and restore (File menu). License keys are not included in backups.
- Export to formatted PDF and HTML, and formatted printing.
- Focus mode (F11), word goal, keyboard shortcut list.
- 9 themes, with optional system theme following.
- Double-clicking a `.qaz` file opens qaZNot. If it is already running, the file opens in a new tab.
- Discord Rich Presence.
- Update check (when `update_url` is set).

### Design editor (qAnvas)
- Layers: text, shapes, lines, images. Copy/cut/paste (including between documents), alignment, equal distribution, smart guide lines.
- Gradient fills, undo/redo.
- Uploads library, templates, and PNG/JPG/PDF export.
- Opens from inside qaZNot as a separate process.

### Editions and licensing
The app is licensed in three tiers: **Core**, **Enterprise**, and **Professional**. Some features (e.g., templates, custom sizes, signing) depend on the tier.

## Screenshots

_Coming soon._

## Installation

### Users
1. Run `qaZNot-Kurulum-<version>.exe`.
2. In the setup wizard, choose whether to create a desktop shortcut and associate `.qaz` files.

### Running from source
Requirements: Python (developed and tested with Python 3.15).

```bash
pip install PySide6 cryptography pillow
cd pyside6-prototip
python qaznote_qt.py
```

Optional (for tests): `pip install pymupdf`

## Building

Single-folder (onedir) executable:

```bash
cd build_qt
python -m PyInstaller --noconfirm --distpath ..\dist_qt --workpath ..\build_qt qaZNot.spec
```

Installer (requires Inno Setup 6):

```bash
cd pyside6-prototip
ISCC.exe installer.iss
```

Version information is managed in one place: `pyside6-prototip/qz_version.py` (VERSION, CODENAME, BUILD_DATE). The installer (`installer.iss`) and the exe version info (`version_info.txt`) must match these values.

### Version naming
`<version>_<dd><mm><yy>_var<n>`, for example: `0.3_061126_var1` (version 0.3, built 06.11.2026, variant 1). The update check compares only the numeric part (`0.3`).

## Tests

```bash
cd pyside6-prototip
set QT_QPA_PLATFORM=offscreen
python test_qaznote_qt.py
python test_qz_editor.py
python test_extras.py
python test_backup.py
python test_qanvas.py
```

Tests do not touch real user data; they run in a temporary folder.

Known issue: `test_qaznote_qt.py` and `test_qanvas.py` report correct results but exit with `0xC0000005` afterwards.

## Project structure

```
pyside6-prototip/
  qaznote_qt.py      entry point
  qz_*.py            note editor (main window, editor, files, export, backup, encryption...)
  qanvas.py          design editor (separate process)
  qv_*.py            qAnvas engine and UI
  test_*.py          tests
  installer.iss      Inno Setup installer
  version_info.txt   Windows exe version info
```

## Data location

Settings, uploads, and the template cache are stored in `%APPDATA%\qaznote\`. Documents stay where the user saves them.

## Security notes

- Google sign-in requires an OAuth client secret. The secret is not included in this repository and must not be shared.
- Published exe files are currently unsigned.
- An encrypted document's password is never stored in the file. If it is lost, the document cannot be recovered.

## License keys

License keys for Core, Enterprise, and Professional editions: contact **Discord: qazryou**.

## License

Not decided yet.
