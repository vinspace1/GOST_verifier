# GOST Verifier — Skeleton GUI

This is a minimal skeleton GUI that demonstrates how a desktop app can call the validation core (CLI) and present JSON results. The GUI accepts PDF and DOCX input files.

Files added:

- `src\core_stub.py` — a small CLI stub that emits sample JSON.
- `src\gui.py` — Tkinter-based GUI that calls a core executable/script and shows results.

Quick run (requires Python 3.8+):

```powershell
# from repository root
python src\core_stub.py path\to\document.pdf    # optional: test CLI directly (supports .pdf and .docx)
python src\gui.py                               # starts GUI that points to core_stub by default
```

Packaging to Windows executable (PyInstaller):

```powershell
# install pyinstaller if needed
pip install pyinstaller

# create a single-file exe for GUI
pyinstaller --noconfirm --onefile --windowed src\gui.py --name GOSTVerifierGUI

# create a single-file exe for core (optional)
pyinstaller --noconfirm --onefile src\core_stub.py --name gost_core
```

Notes:
- The real `validation core` should be a CLI that prints JSON to stdout (structured result). The GUI simply calls that binary/script and reads stdout.
- For a production Windows installer consider `MSIX` or `Inno Setup` and code signing (`signtool`) to avoid SmartScreen warnings.
- If you need a richer PDF preview or vector highlighting, consider embedding a WebView (Tauri/Electron) or using a native PDF widget.

Next steps you can ask me to do:
- Expand the GUI to preview PDFs and highlight issues.
- Define the JSON Schema for validation results.
- Create a CI workflow to build Windows executables.