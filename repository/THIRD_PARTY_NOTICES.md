# Third-party software notices

ClearScore application code is MIT licensed. Dependencies are unmodified and
retain their original licenses. The portable build includes a `licenses`
directory containing the installed packages' notices and license texts.

| Component | License | Upstream source |
| --- | --- | --- |
| Python | PSF License and included notices | https://www.python.org/downloads/source/ |
| PySide6 / Shiboken6 | LGPL-3.0 (selected from upstream alternatives) | https://code.qt.io/cgit/pyside/pyside-setup.git/ |
| Qt Core, Gui, Widgets | LGPL-3.0 (selected from upstream alternatives) | https://code.qt.io/cgit/qt/qtbase.git/ |
| NumPy | BSD-3-Clause and bundled dependency notices | https://github.com/numpy/numpy |
| Pillow | MIT-CMU and bundled dependency notices | https://github.com/python-pillow/Pillow |
| pi-heif-decoder | BSD-3-Clause, decoder libraries under LGPL-3.0-or-later | https://pypi.org/project/pi-heif-decoder/ |
| libheif 1.23.4 / libde265 1.1.3 | LGPL-3.0-or-later | https://github.com/strukturag/libheif/tree/v1.23.4 and https://github.com/strukturag/libde265/tree/v1.1.3 |
| pypdf | BSD-3-Clause | https://github.com/py-pdf/pypdf |
| pypdfium2 | Apache-2.0 / BSD-3-Clause and included notices | https://github.com/pypdfium2-team/pypdfium2 |
| PDFium | BSD-style and third-party notices in BUILD_LICENSES | https://pdfium.googlesource.com/pdfium/ |
| PyInstaller bootloader | GPL-2.0-or-later with distribution exception | https://github.com/pyinstaller/pyinstaller |

The exact installed versions are recorded in `licenses/versions.json` in the
portable package. Package metadata, license files, and PDFium build notices are
collected automatically during packaging.

Qt and PySide6 are dynamically linked. Their DLLs and extension modules remain
separate in `_internal/PySide6` and `_internal/shiboken6`. Users may replace or
rebuild these components with ABI-compatible modified versions and may reverse
engineer the combined work to debug their modifications, as permitted by LGPL.
There are no application-level restrictions on doing so.

HEIC import uses the decode-only `pi-heif-decoder` build. It does not ship the
x265 encoder. Its native decoder DLLs remain separate in `_internal` and may be
replaced with ABI-compatible modified builds. The exact wheel's
`LICENSES_bundled.txt` is included with the distribution.

Sources for matching Qt/PySide releases are available from the upstream Git
repositories above under their version tags (for example `v6.12.0`), and from
https://download.qt.io/official_releases/QtForPython/ and
https://download.qt.io/official_releases/qt/ .

The GNU LGPL version 3 and GPL version 3 texts are included in `licenses/`.
To rebuild the application, follow README.md and scripts/build_windows.py.
MIT licensing of ClearScore does not relicense third-party components.
