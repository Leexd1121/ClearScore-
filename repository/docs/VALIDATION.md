# ClearScore 1.1.0 validation

Validated on Windows x64 with Python 3.12 and the pinned dependencies.

The upload-ready source ZIP was extracted into a fresh directory without Git
history or private samples: **59 passed, 1 skipped**, process exit code 0.
The skipped test requires an optional private PDF and is intentionally not run
for the public release. The extracted copy also passed the release manifest check.

- The original application regression run passed 46 tests, including one
  optional private PDF regression. The public suite excludes private samples.
- The public release adds 14 packaging/privacy checks for file allowlisting,
  credential and local-identity rejection, redacted errors, changed demo assets,
  deterministic ZIP metadata, and inspection of frozen Python code.
- Tests cover PDF layout/content-stream preservation, protected dark pixels,
  image codecs, alpha, EXIF orientation, multiple frames, DOCX text/layout and
  media relationships, original-file protection, errors and cancellation.
- UI checks cover all four languages, message/placeholder completeness,
  Uyghur glyph coverage, RTL layout and LTR score canvas, language changes
  after import, preview and export, and file-dialog contrast under a dark OS palette.
- The actual frozen, windowed executable successfully opened, previewed and
  exported PDF, PNG, DOCX, TIFF, AVIF and HEIC. Those launch checks also exercise
  Chinese, English, Russian and Uyghur.
- Native desktop review verified document import, language selection, the
  Uyghur interface, file-dialog readability, and the original/cleaned comparison.
- No user score or cleaned result is included in the source/release packages.
- Release inspection covered 349 portable files and 19,890 Python code objects,
  including decompressed embedded modules. No matching local identity or
  absolute frozen source path was found. Four screenshots were reviewed; the
  PNGs contain only display-density metadata. The synthetic HEIC contains no
  EXIF payload, extra metadata or embedded thumbnails.

DOCX validation checks preserved XML and an independent python-docx reopen.
The app previews embedded images; it does not claim to render Word page layout.
Language tests and visual review are not a native-speaker editorial certification.
