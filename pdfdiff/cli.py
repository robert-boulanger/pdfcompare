"""Typer CLI for pdfdiff — diff, validate, annotate, visual-diff commands.

Designed for both interactive use and Tauri sidecar JSON communication.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from pdfdiff import __version__

app = typer.Typer(
    name="pdfdiff",
    help="PDF comparison and typographic analysis tool.",
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    if value:
        print(f"pdfdiff {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version", "-v",
            help="Show version.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """pdfdiff — PDF comparison and typographic analysis."""


@app.command()
def diff(
    left: Annotated[
        Path, typer.Argument(help="Path to the original PDF."),
    ],
    right: Annotated[
        Path, typer.Argument(help="Path to the modified PDF."),
    ],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="JSON output (for sidecar/GUI integration)."),
    ] = False,
) -> None:
    """Compare two PDFs at paragraph level."""
    _validate_pdf(left, "Left")
    _validate_pdf(right, "Right")

    from pdfdiff.differ import diff_paragraphs
    from pdfdiff.extractor import extract_paragraphs

    left_paras = extract_paragraphs(str(left))
    right_paras = extract_paragraphs(str(right))
    result = diff_paragraphs(left_paras, right_paras)

    if json_output:
        print(result.to_json())
        return

    s = result.summary
    print(
        f"{s.total_paragraphs_left} paragraphs (original) vs. "
        f"{s.total_paragraphs_right} paragraphs (modified)"
    )

    if not result.differences:
        print("No differences found.")
        return

    print(f"\n{len(result.differences)} differences:")
    for i, d in enumerate(result.differences, 1):
        if d.type == "added":
            print(f"  [{i}] +ADDED p.{d.right_page}: {d.right_snippet}")
        elif d.type == "removed":
            print(f"  [{i}] -REMOVED p.{d.left_page}: {d.left_snippet}")
        else:
            print(f"  [{i}] ~CHANGED p.{d.left_page}->{d.right_page}: {d.left_snippet}")

    print(
        f"\n{s.changed} changed, {s.added} added, "
        f"{s.removed} removed, {s.unchanged} unchanged"
    )


@app.command()
def validate(
    pdf: Annotated[
        Path, typer.Argument(help="Path to the PDF file."),
    ],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="JSON output."),
    ] = False,
    word_spacing_factor: Annotated[
        float,
        typer.Option("--word-spacing-factor", help="Word spacing threshold factor."),
    ] = 1.8,
) -> None:
    """Analyze a PDF for typographic issues."""
    _validate_pdf(pdf, "Input")

    from pdfdiff.analyzer import analyze_pdf

    report = analyze_pdf(str(pdf), word_spacing_factor=word_spacing_factor)

    if json_output:
        print(report.to_json())
        return

    if not report.issues:
        print("No typographic issues found.")
        return

    for issue in report.issues:
        severity = "WARNING" if issue.severity.value == "warning" else (
            "ERROR" if issue.severity.value == "error" else "hint"
        )
        loc = f"p.{issue.page}" if issue.page > 0 else "global"
        snippet = f' "{issue.snippet}"' if issue.snippet else ""
        print(f"  [{severity}] {loc}: {issue.message}{snippet}")

    print(
        f"\n{report.warning_count} warnings, "
        f"{report.hint_count} hints"
    )


@app.command()
def annotate(
    input_pdf: Annotated[
        Path, typer.Argument(help="Path to the source PDF."),
    ],
    output_pdf: Annotated[
        Path, typer.Argument(help="Path for the annotated output PDF."),
    ],
    annotations: Annotated[
        str,
        typer.Option("--annotations", help="JSON string with annotations."),
    ] = "[]",
) -> None:
    """Write annotations to a PDF."""
    _validate_pdf(input_pdf, "Input")

    from pdfdiff.annotator import save_annotations

    save_annotations(str(input_pdf), str(output_pdf), annotations)
    print(f"Annotated PDF saved to: {output_pdf}")


@app.command(name="visual-diff")
def visual_diff(
    left: Annotated[
        Path, typer.Argument(help="Path to the original PDF."),
    ],
    right: Annotated[
        Path, typer.Argument(help="Path to the modified PDF."),
    ],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="JSON output."),
    ] = False,
    dpi: Annotated[
        int,
        typer.Option("--dpi", help="Render DPI for comparison."),
    ] = 150,
) -> None:
    """Compare two PDFs visually (pixel-level)."""
    _validate_pdf(left, "Left")
    _validate_pdf(right, "Right")

    from pdfdiff.visual_differ import visual_diff as run_visual_diff

    result = run_visual_diff(str(left), str(right), dpi=dpi)

    if json_output:
        print(result.to_json())
        return

    print(
        f"{result.total_pages_left} pages (original) vs. "
        f"{result.total_pages_right} pages (modified)"
    )

    if not result.pages:
        print("No visual differences found.")
        return

    for p in result.pages:
        status = "IDENTICAL" if p.changed_pixels_percent < 0.1 else "CHANGED"
        print(f"  Page {p.page}: {p.changed_pixels_percent:.2f}% changed [{status}]")


@app.command()
def detect(
    pdf: Annotated[
        Path, typer.Argument(help="Path to the PDF file."),
    ],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="JSON output."),
    ] = False,
) -> None:
    """Detect document type (book, magazine, flyer)."""
    _validate_pdf(pdf, "Input")

    from pdfdiff.detector import detect_document_type

    doc_type = detect_document_type(str(pdf))

    if json_output:
        import json
        print(json.dumps({"type": doc_type.value}))
        return

    print(f"Document type: {doc_type.value}")


def _validate_pdf(path: Path, label: str) -> None:
    """Validate that a path points to an existing PDF file."""
    if not path.exists():
        print(f"Error: {label} file not found: {path}")
        raise typer.Exit(code=1)
    if path.suffix.lower() != ".pdf":
        print(f"Error: {label} is not a PDF: {path.suffix}")
        raise typer.Exit(code=1)
