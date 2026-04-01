"""Entry point for `python -m pdfdiff`."""

import io
import sys

# Force UTF-8 on stdout/stderr so Unicode characters from PDFs
# don't fail with 'charmap' codec errors on Windows.
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from pdfdiff.cli import app

app()
