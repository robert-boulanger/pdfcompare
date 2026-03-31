"""Typographic analysis of existing PDF files using PyMuPDF.

Ported from Bleisatz pdf_analyzer.py.
Standalone analysis — extracts text with position data and checks for
common typographic issues.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from pdfdiff.models import DocumentType, Severity, ValidationIssue, ValidationReport


@dataclass
class TextLine:
    """A single line of text with position and font metadata."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    font_size: float
    is_bold: bool
    page: int  # 1-based


@dataclass
class WordBox:
    """A single word with its bounding box from PyMuPDF."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    block_no: int
    line_no: int


@dataclass
class PageInfo:
    """Extracted layout information for a single page."""

    number: int  # 1-based
    width_pt: float
    height_pt: float
    lines: list[TextLine] = field(default_factory=list)
    word_boxes: list[WordBox] = field(default_factory=list)


@dataclass
class TypeArea:
    """Detected type area (Satzspiegel) boundaries."""

    left: float
    right: float
    top: float
    bottom: float


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_line_bbox(page: PageInfo, line_text: str) -> list[float] | None:
    """Find the bbox of a line on a page by matching its text start."""
    prefix = line_text[:30]
    for line in page.lines:
        if line.text.startswith(prefix):
            return [line.x0, line.y0, line.x1, line.y1]
    return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def analyze_pdf(
    path: str,
    *,
    lang: str = "de",
    skip_checks: set[str] | None = None,
    word_spacing_factor: float = 1.8,
    doc_type: DocumentType | None = None,
) -> ValidationReport:
    """Run all typographic checks on an existing PDF.

    Args:
        path: Path to the PDF file.
        lang: Language hint (reserved for future use).
        skip_checks: Set of check names to skip.
        word_spacing_factor: Flag lines with avg gap > N x the page median.
        doc_type: Document type for adaptive checks. If None, auto-detected.

    Returns:
        ValidationReport with all found issues.
    """
    import fitz  # type: ignore[import-not-found]

    skips = skip_checks or set()

    doc = fitz.open(path)
    pages = _extract_pages(doc)
    doc.close()

    if not pages:
        return ValidationReport(issues=[
            ValidationIssue(Severity.WARNING, 0, "PDF contains no pages."),
        ])

    # Auto-detect document type if not provided
    if doc_type is None:
        from pdfdiff.detector import detect_document_type
        doc_type = detect_document_type(path)

    report = ValidationReport()
    report.pages_checked = len(pages)
    type_area = _detect_type_area(pages)

    # --- Standard checks (7 from Bleisatz) ---
    if "page_info" not in skips:
        check_page_info(pages, report)
        report.checks_run.append("page_info")
    if "text_overflow" not in skips:
        check_text_overflow(pages, type_area, report)
        report.checks_run.append("text_overflow")
    # Widows/orphans only for book-like documents
    if "widows_orphans" not in skips and doc_type != DocumentType.FLYER:
        check_widows_orphans(pages, report)
        report.checks_run.append("widows_orphans")
    if "word_spacing" not in skips:
        check_word_spacing(pages, type_area, report, spacing_factor=word_spacing_factor)
        report.checks_run.append("word_spacing")
    if "hyphenation" not in skips and doc_type != DocumentType.FLYER:
        check_hyphenation_at_page_break(pages, report)
        report.checks_run.append("hyphenation")
    if "consecutive_hyphens" not in skips and doc_type != DocumentType.FLYER:
        check_consecutive_hyphens(pages, report)
        report.checks_run.append("consecutive_hyphens")
    if "justification" not in skips:
        check_justification(pages, type_area, report)
        report.checks_run.append("justification")

    # --- Extended checks (new in pdfcompare) ---
    if "image_text_overlap" not in skips:
        check_image_text_overlap(path, pages, report)
        report.checks_run.append("image_text_overlap")
    if "clipped_content" not in skips:
        check_clipped_content(path, pages, type_area, report)
        report.checks_run.append("clipped_content")
    if "column_consistency" not in skips and doc_type != DocumentType.FLYER:
        check_column_consistency(pages, type_area, report)
        report.checks_run.append("column_consistency")
    if "sparse_pages" not in skips:
        check_sparse_pages(pages, type_area, report)
        report.checks_run.append("sparse_pages")

    report.issues.sort(key=lambda i: (i.page == 0, i.page))
    return report


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def _extract_pages(doc: object) -> list[PageInfo]:
    """Extract text lines with position data from all pages."""
    import fitz  # type: ignore[import-not-found]

    pages: list[PageInfo] = []

    for page_idx in range(len(doc)):  # type: ignore[arg-type]
        page = doc[page_idx]  # type: ignore[index]
        rect = page.rect
        page_info = PageInfo(
            number=page_idx + 1,
            width_pt=rect.width,
            height_pt=rect.height,
        )

        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

        for block in blocks:
            if block["type"] != 0:
                continue

            for line_data in block["lines"]:
                spans = line_data["spans"]
                if not spans:
                    continue

                text_parts: list[str] = []
                font_sizes: list[float] = []
                has_bold = False

                for span in spans:
                    text_parts.append(span["text"])
                    font_sizes.append(span["size"])
                    if span["flags"] & 2 ** 4:
                        has_bold = True

                full_text = "".join(text_parts).strip()
                if not full_text:
                    continue

                bbox = line_data["bbox"]
                avg_size = statistics.mean(font_sizes) if font_sizes else 0.0

                page_info.lines.append(TextLine(
                    text=full_text,
                    x0=bbox[0],
                    y0=bbox[1],
                    x1=bbox[2],
                    y1=bbox[3],
                    font_size=avg_size,
                    is_bold=has_bold,
                    page=page_idx + 1,
                ))

        for w in page.get_text("words"):
            page_info.word_boxes.append(WordBox(
                text=w[4],
                x0=w[0], y0=w[1], x1=w[2], y1=w[3],
                block_no=w[5], line_no=w[6],
            ))

        pages.append(page_info)

    return pages


# ---------------------------------------------------------------------------
# Type area (Satzspiegel) detection
# ---------------------------------------------------------------------------

def _detect_type_area(pages: list[PageInfo]) -> TypeArea:
    """Heuristically detect the type area from text line positions."""
    all_x0: list[float] = []
    all_x1: list[float] = []
    all_y0: list[float] = []
    all_y1: list[float] = []

    for page in pages:
        for line in page.lines:
            if len(line.text) < 15:
                continue
            all_x0.append(line.x0)
            all_x1.append(line.x1)
            all_y0.append(line.y0)
            all_y1.append(line.y1)

    if len(all_x0) < 10:
        if pages:
            w = pages[0].width_pt
            h = pages[0].height_pt
            return TypeArea(left=w * 0.1, right=w * 0.9, top=h * 0.1, bottom=h * 0.9)
        return TypeArea(left=50, right=500, top=50, bottom=750)

    all_x0.sort()
    all_x1.sort()
    all_y0.sort()
    all_y1.sort()

    n = len(all_x0)
    p5 = int(n * 0.05)
    p95 = int(n * 0.95) - 1

    return TypeArea(
        left=all_x0[p5],
        right=all_x1[p95],
        top=all_y0[p5],
        bottom=all_y1[p95],
    )


# ---------------------------------------------------------------------------
# Check: Page info
# ---------------------------------------------------------------------------

def check_page_info(pages: list[PageInfo], report: ValidationReport) -> None:
    """Report basic page information."""
    if not pages:
        return

    first = pages[0]
    w_mm = first.width_pt / 72.0 * 25.4
    h_mm = first.height_pt / 72.0 * 25.4

    report.issues.append(ValidationIssue(
        severity=Severity.HINT,
        page=0,
        message=f"{len(pages)} Seiten, {w_mm:.0f} \u00d7 {h_mm:.0f} mm",
        check="page_info",
    ))


# ---------------------------------------------------------------------------
# Check: Text overflow
# ---------------------------------------------------------------------------

def check_text_overflow(
    pages: list[PageInfo],
    type_area: TypeArea,
    report: ValidationReport,
) -> None:
    """Find lines that extend beyond the detected type area."""
    threshold_pt = 2.0

    for page in pages:
        for line in page.lines:
            if len(line.text) < 10:
                continue

            overflow_right = line.x1 - type_area.right
            if overflow_right > threshold_pt:
                snippet = line.text[:50] + ("\u2026" if len(line.text) > 50 else "")
                report.issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    page=page.number,
                    message=(
                        f"Text extends beyond type area "
                        f"(+{overflow_right:.1f}pt)"
                    ),
                    snippet=snippet,
                    bbox=[line.x0, line.y0, line.x1, line.y1],
                    check="text_overflow",
                ))


# ---------------------------------------------------------------------------
# Check: Widows and orphans
# ---------------------------------------------------------------------------

def _is_paragraph_boundary(line_a: TextLine, line_b: TextLine) -> bool:
    """Detect if there's a paragraph break between two lines."""
    line_height = line_a.y1 - line_a.y0
    gap = line_b.y0 - line_a.y1
    return bool(line_height > 0 and gap > line_height * 1.5)


def _looks_like_heading(line: TextLine, median_size: float) -> bool:
    """Check if a line looks like a heading."""
    if line.font_size > median_size * 1.15:
        return True
    if line.is_bold and len(line.text) < 60:
        return True
    return bool(line.text and line.text[0].isdigit() and len(line.text) < 50)


def check_widows_orphans(
    pages: list[PageInfo],
    report: ValidationReport,
) -> None:
    """Detect widows (Hurenkinder) and orphans (Schusterjungen)."""
    if len(pages) < 2:
        return

    all_sizes = [ln.font_size for p in pages for ln in p.lines if ln.font_size > 0]
    median_size = statistics.median(all_sizes) if all_sizes else 10.0

    for i in range(1, len(pages)):
        prev_page = pages[i - 1]
        curr_page = pages[i]

        if not prev_page.lines or not curr_page.lines:
            continue

        last_line = prev_page.lines[-1]
        first_line = curr_page.lines[0]

        if _looks_like_heading(first_line, median_size):
            continue
        if _looks_like_heading(last_line, median_size):
            continue

        # Widow: short line alone at top of page
        if (
            len(first_line.text) < 25
            and not first_line.text.endswith("-")
            and len(curr_page.lines) > 1
        ):
            second_line = curr_page.lines[1]
            if (
                _is_paragraph_boundary(first_line, second_line)
                or len(second_line.text) > len(first_line.text) * 2
            ):
                report.issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    page=curr_page.number,
                    message="Possible widow (short line at page start)",
                    snippet=first_line.text[:40],
                    bbox=[first_line.x0, first_line.y0, first_line.x1, first_line.y1],
                    check="widows_orphans",
                ))

        # Orphan: single paragraph line at bottom of page
        if len(prev_page.lines) >= 2:
            second_last = prev_page.lines[-2]
            if _is_paragraph_boundary(second_last, last_line) and len(last_line.text) > 20:
                report.issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    page=prev_page.number,
                    message="Possible orphan (single paragraph line at page end)",
                    snippet=last_line.text[:40],
                    bbox=[last_line.x0, last_line.y0, last_line.x1, last_line.y1],
                    check="widows_orphans",
                ))


# ---------------------------------------------------------------------------
# Check: Word spacing
# ---------------------------------------------------------------------------

def check_word_spacing(
    pages: list[PageInfo],
    type_area: TypeArea,
    report: ValidationReport,
    *,
    spacing_factor: float = 1.8,
) -> None:
    """Detect lines with excessively large word spacing."""
    type_width = type_area.right - type_area.left
    if type_width <= 0:
        return

    for page in pages:
        line_words: dict[tuple[int, int], list[WordBox]] = {}
        for wb in page.word_boxes:
            key = (wb.block_no, wb.line_no)
            line_words.setdefault(key, []).append(wb)

        line_gaps: list[tuple[str, float, float]] = []

        for _key, words in line_words.items():
            if len(words) < 3:
                continue
            words.sort(key=lambda w: w.x0)

            line_x0 = words[0].x0
            line_x1 = words[-1].x1
            if (line_x1 - line_x0) < type_width * 0.85:
                continue

            gaps: list[float] = []
            for j in range(len(words) - 1):
                gap = words[j + 1].x0 - words[j].x1
                if gap > 0:
                    gaps.append(gap)

            if not gaps:
                continue

            avg_gap = statistics.mean(gaps)
            max_gap = max(gaps)
            line_text = " ".join(w.text for w in words)
            line_gaps.append((line_text, avg_gap, max_gap))

        if len(line_gaps) < 5:
            continue

        gap_values = [g for _, g, _ in line_gaps]
        median_gap = statistics.median(gap_values)

        if median_gap <= 0:
            continue

        for line_text, avg_gap, max_gap in line_gaps:
            flagged = False
            if avg_gap > median_gap * spacing_factor and avg_gap > 5.0:
                flagged = True
            if max_gap > median_gap * 3.0 and max_gap > 12.0:
                flagged = True

            if flagged:
                snippet = line_text[:50] + ("\u2026" if len(line_text) > 50 else "")
                # Find the line bbox from page lines
                line_bbox = _find_line_bbox(page, line_text)
                report.issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    page=page.number,
                    message=(
                        f"Excessive word spacing "
                        f"({avg_gap:.1f}pt, max {max_gap:.1f}pt, "
                        f"median {median_gap:.1f}pt)"
                    ),
                    snippet=snippet,
                    bbox=line_bbox,
                    check="word_spacing",
                ))


# ---------------------------------------------------------------------------
# Check: Hyphenation at page break
# ---------------------------------------------------------------------------

def check_hyphenation_at_page_break(
    pages: list[PageInfo],
    report: ValidationReport,
) -> None:
    """Detect pages ending with a hyphenated word."""
    for page in pages:
        if not page.lines:
            continue

        last_line = page.lines[-1]
        text = last_line.text.rstrip()

        if text.endswith("-") or text.endswith("\u00ad"):
            snippet = text[-30:] if len(text) > 30 else text
            report.issues.append(ValidationIssue(
                severity=Severity.WARNING,
                page=page.number,
                message="Hyphenation at page break",
                snippet=snippet,
                bbox=[last_line.x0, last_line.y0, last_line.x1, last_line.y1],
                check="hyphenation",
            ))


# ---------------------------------------------------------------------------
# Check: Consecutive hyphens
# ---------------------------------------------------------------------------

def check_consecutive_hyphens(
    pages: list[PageInfo],
    report: ValidationReport,
) -> None:
    """Detect 3 or more consecutive lines ending with a hyphen."""
    for page in pages:
        if len(page.lines) < 3:
            continue

        streak = 0
        streak_start_line: TextLine | None = None

        for line in page.lines:
            text = line.text.rstrip()
            if text.endswith("-") or text.endswith("\u00ad"):
                if streak == 0:
                    streak_start_line = line
                streak += 1
            else:
                if streak >= 3 and streak_start_line is not None:
                    report.issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        page=page.number,
                        message=f"{streak} consecutive hyphenations",
                        snippet=streak_start_line.text[:40],
                        bbox=[streak_start_line.x0, streak_start_line.y0,
                              streak_start_line.x1, streak_start_line.y1],
                        check="consecutive_hyphens",
                    ))
                streak = 0
                streak_start_line = None

        if streak >= 3 and streak_start_line is not None:
            report.issues.append(ValidationIssue(
                severity=Severity.WARNING,
                page=page.number,
                message=f"{streak} consecutive hyphenations",
                snippet=streak_start_line.text[:40],
                check="consecutive_hyphens",
            ))


# ---------------------------------------------------------------------------
# Check: Justification detection
# ---------------------------------------------------------------------------

def check_justification(
    pages: list[PageInfo],
    type_area: TypeArea,
    report: ValidationReport,
) -> None:
    """Detect whether the PDF uses justified or ragged-right text."""
    if not pages:
        return

    type_width = type_area.right - type_area.left
    if type_width <= 0:
        return

    justified_pages = 0
    ragged_pages = 0

    for page in pages:
        full_lines = [
            ln for ln in page.lines
            if len(ln.text) > 30 and (ln.x1 - ln.x0) > type_width * 0.7
        ]
        if len(full_lines) < 5:
            continue

        right_aligned = sum(
            1 for ln in full_lines
            if abs(ln.x1 - type_area.right) < 3.0
        )
        ratio = right_aligned / len(full_lines)

        if ratio > 0.7:
            justified_pages += 1
        else:
            ragged_pages += 1

    total = justified_pages + ragged_pages
    if total == 0:
        return

    if ragged_pages > justified_pages:
        report.issues.append(ValidationIssue(
            severity=Severity.HINT,
            page=0,
            message=(
                f"Ragged-right text detected ({ragged_pages}/{total} pages). "
                f"Word spacing analysis limited."
            ),
            check="justification",
        ))
    else:
        report.issues.append(ValidationIssue(
            severity=Severity.HINT,
            page=0,
            message=f"Justified text detected ({justified_pages}/{total} pages).",
            check="justification",
        ))


# ---------------------------------------------------------------------------
# Extended Check: Image-text overlap
# ---------------------------------------------------------------------------

def check_image_text_overlap(
    path: str,
    pages: list[PageInfo],
    report: ValidationReport,
) -> None:
    """Detect text bounding boxes overlapping with image bounding boxes."""
    import fitz  # type: ignore[import-not-found]

    doc = fitz.open(path)

    for page_info in pages:
        if not page_info.lines:
            continue

        page_idx = page_info.number - 1
        if page_idx >= len(doc):
            continue

        page = doc[page_idx]

        # Collect image rects
        image_rects: list[tuple[float, float, float, float]] = []
        for img in page.get_images(full=True):
            xref = img[0]
            try:
                for rect in page.get_image_rects(xref):
                    if rect.width > 10 and rect.height > 10:
                        image_rects.append((rect.x0, rect.y0, rect.x1, rect.y1))
            except Exception:
                pass

        if not image_rects:
            continue

        # Check text lines against image rects
        for line in page_info.lines:
            for ir in image_rects:
                if _rects_overlap(
                    (line.x0, line.y0, line.x1, line.y1),
                    ir,
                ):
                    snippet = line.text[:40] + ("\u2026" if len(line.text) > 40 else "")
                    report.issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        page=page_info.number,
                        message="Text overlaps with image",
                        snippet=snippet,
                        bbox=[line.x0, line.y0, line.x1, line.y1],
                        check="image_text_overlap",
                    ))
                    break  # one warning per line is enough

    doc.close()


def _rects_overlap(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> bool:
    """Check if two rectangles overlap (more than just touching)."""
    margin = 2.0  # allow small overlap margin
    return not (
        a[2] <= b[0] + margin or  # a is left of b
        a[0] >= b[2] - margin or  # a is right of b
        a[3] <= b[1] + margin or  # a is above b
        a[1] >= b[3] - margin     # a is below b
    )


# ---------------------------------------------------------------------------
# Extended Check: Clipped content (outside trim box)
# ---------------------------------------------------------------------------

def check_clipped_content(
    path: str,
    pages: list[PageInfo],
    type_area: TypeArea,
    report: ValidationReport,
) -> None:
    """Detect content that extends outside the page trim box."""
    import fitz  # type: ignore[import-not-found]

    doc = fitz.open(path)

    for page_info in pages:
        page_idx = page_info.number - 1
        if page_idx >= len(doc):
            continue

        page = doc[page_idx]

        # Use TrimBox if available, otherwise MediaBox
        trim_rect = page.trimbox if page.trimbox else page.rect

        for line in page_info.lines:
            if len(line.text) < 5:
                continue
            # Check if line extends outside trim box
            if (line.x1 > trim_rect.x1 + 3.0 or
                line.x0 < trim_rect.x0 - 3.0 or
                line.y1 > trim_rect.y1 + 3.0 or
                line.y0 < trim_rect.y0 - 3.0):
                snippet = line.text[:40] + ("\u2026" if len(line.text) > 40 else "")
                report.issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    page=page_info.number,
                    message="Content extends outside trim box",
                    snippet=snippet,
                    bbox=[line.x0, line.y0, line.x1, line.y1],
                    check="clipped_content",
                ))

    doc.close()


# ---------------------------------------------------------------------------
# Extended Check: Column consistency
# ---------------------------------------------------------------------------

def check_column_consistency(
    pages: list[PageInfo],
    type_area: TypeArea,
    report: ValidationReport,
) -> None:
    """Detect multi-column layouts with significantly uneven column fill."""
    type_width = type_area.right - type_area.left
    if type_width <= 0:
        return

    for page in pages:
        if len(page.lines) < 10:
            continue

        # Detect columns by clustering line x0 positions
        x_starts = sorted(set(round(ln.x0, 0) for ln in page.lines if len(ln.text) > 10))
        if len(x_starts) < 2:
            continue

        # Find column boundaries: gaps > 20% of type width
        columns: list[list[TextLine]] = []
        col_boundaries: list[float] = [x_starts[0]]

        for i in range(1, len(x_starts)):
            if x_starts[i] - x_starts[i - 1] > type_width * 0.2:
                col_boundaries.append(x_starts[i])

        if len(col_boundaries) < 2:
            continue

        # Assign lines to columns
        columns = [[] for _ in col_boundaries]
        for line in page.lines:
            if len(line.text) < 10:
                continue
            for ci in range(len(col_boundaries) - 1, -1, -1):
                if line.x0 >= col_boundaries[ci] - 10:
                    columns[ci].append(line)
                    break

        # Filter empty columns
        col_counts = [len(c) for c in columns if len(c) > 0]
        if len(col_counts) < 2:
            continue

        max_lines = max(col_counts)
        min_lines = min(col_counts)

        if max_lines > 0 and min_lines < max_lines * 0.5:
            report.issues.append(ValidationIssue(
                severity=Severity.HINT,
                page=page.number,
                message=(
                    f"Uneven column fill ({len(col_counts)} columns: "
                    f"{min_lines} vs {max_lines} lines)"
                ),
                check="column_consistency",
            ))


# ---------------------------------------------------------------------------
# Extended Check: Sparse/empty pages
# ---------------------------------------------------------------------------

def check_sparse_pages(
    pages: list[PageInfo],
    type_area: TypeArea,
    report: ValidationReport,
) -> None:
    """Detect pages with unusually little content compared to the rest."""
    if len(pages) < 3:
        return

    # Calculate content density per page (lines of text)
    line_counts = [len(p.lines) for p in pages]
    if not line_counts:
        return

    median_lines = sorted(line_counts)[len(line_counts) // 2]
    if median_lines < 5:
        return  # too sparse overall to judge

    for page in pages:
        count = len(page.lines)
        # Flag pages with less than 20% of the median content
        if count < median_lines * 0.2 and count < 3:
            report.issues.append(ValidationIssue(
                severity=Severity.HINT,
                page=page.number,
                message=(
                    f"Sparse page ({count} lines, "
                    f"median is {median_lines})"
                ),
                check="sparse_pages",
            ))
