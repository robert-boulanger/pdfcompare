"""PDF text extraction — extract paragraphs with position data.

Ported from Bleisatz pdf_diff.py (extraction part).
Uses PyMuPDF for text extraction with bounding boxes.
"""

from __future__ import annotations

from dataclasses import dataclass

from pdfdiff.models import Paragraph, WordBBox


@dataclass
class _RawLine:
    """Intermediate line representation during extraction."""

    text: str
    page: int  # 1-based
    x0: float
    y0: float
    x1: float
    y1: float
    font_size: float


def extract_paragraphs(pdf_path: str) -> list[Paragraph]:
    """Extract paragraphs from a PDF using PyMuPDF.

    Merges consecutive text lines into paragraphs based on vertical gaps.
    Filters out headers/footers by detecting repeated short text across pages.
    Collects word-level bounding boxes for fine-grained diff highlighting.
    """
    import fitz  # type: ignore[import-not-found]

    doc = fitz.open(pdf_path)
    raw_lines = _extract_text_blocks(doc)
    page_words = _extract_page_words(doc)
    doc.close()

    filtered = _filter_headers_footers(raw_lines)
    paragraphs = _merge_into_paragraphs(filtered)

    for i, p in enumerate(paragraphs):
        p.id = i

    # Assign word bboxes to paragraphs
    _assign_word_bboxes(paragraphs, page_words)

    return paragraphs


def _extract_text_blocks(doc: object) -> list[_RawLine]:
    """Extract all text lines from a PDF document."""
    import fitz  # type: ignore[import-not-found]

    lines: list[_RawLine] = []

    for page_idx in range(len(doc)):  # type: ignore[arg-type]
        page = doc[page_idx]  # type: ignore[index]
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

        for block in blocks:
            if block["type"] != 0:  # skip images
                continue

            for line_data in block["lines"]:
                spans = line_data["spans"]
                if not spans:
                    continue

                text = page.get_text("text", clip=line_data["bbox"]).strip()
                if not text:
                    text = "".join(s["text"] for s in spans).strip()
                if not text:
                    continue

                bbox = line_data["bbox"]
                avg_size = sum(s["size"] for s in spans) / len(spans)

                lines.append(_RawLine(
                    text=text,
                    page=page_idx + 1,
                    x0=bbox[0],
                    y0=bbox[1],
                    x1=bbox[2],
                    y1=bbox[3],
                    font_size=avg_size,
                ))

    return lines


def _filter_headers_footers(lines: list[_RawLine]) -> list[_RawLine]:
    """Remove repeated short text that appears on many pages (headers/footers).

    A line is considered a header/footer if:
    - It's short (< 60 chars)
    - The same text (or its page-number variant) appears on > 30% of pages
    """
    if not lines:
        return lines

    page_count = max(ln.page for ln in lines)
    if page_count < 4:
        return lines

    text_pages: dict[str, set[int]] = {}
    for ln in lines:
        if len(ln.text) > 60:
            continue
        normalized = "".join(c for c in ln.text if not c.isdigit()).strip()
        if len(normalized) < 2:
            normalized = "__pagenum__"
        text_pages.setdefault(normalized, set()).add(ln.page)

    threshold = page_count * 0.3
    repeated: set[str] = set()
    for normalized, pages in text_pages.items():
        if len(pages) > threshold:
            repeated.add(normalized)

    if not repeated:
        return lines

    result: list[_RawLine] = []
    for ln in lines:
        if len(ln.text) <= 60:
            normalized = "".join(c for c in ln.text if not c.isdigit()).strip()
            if len(normalized) < 2:
                normalized = "__pagenum__"
            if normalized in repeated:
                continue
        result.append(ln)

    return result


def _merge_into_paragraphs(lines: list[_RawLine]) -> list[Paragraph]:
    """Merge consecutive lines into paragraphs based on vertical gaps.

    Lines on the same page with small vertical gaps (< 1.5x line height)
    are merged into a single paragraph.
    """
    if not lines:
        return []

    paragraphs: list[Paragraph] = []
    current_lines: list[_RawLine] = [lines[0]]

    for i in range(1, len(lines)):
        prev = lines[i - 1]
        curr = lines[i]

        if curr.page != prev.page:
            _flush_paragraph(current_lines, paragraphs)
            current_lines = [curr]
            continue

        line_height = prev.y1 - prev.y0
        gap = curr.y0 - prev.y1

        if (line_height > 0 and gap > line_height * 1.5) or \
           abs(curr.font_size - prev.font_size) > 2.0:
            _flush_paragraph(current_lines, paragraphs)
            current_lines = [curr]
        else:
            current_lines.append(curr)

    _flush_paragraph(current_lines, paragraphs)
    return paragraphs


def _flush_paragraph(lines: list[_RawLine], out: list[Paragraph]) -> None:
    """Create a Paragraph from accumulated lines and append to output."""
    if not lines:
        return

    text = " ".join(ln.text for ln in lines)
    while "  " in text:
        text = text.replace("  ", " ")
    text = text.strip()

    if not text:
        return

    x0 = min(ln.x0 for ln in lines)
    y0 = min(ln.y0 for ln in lines)
    x1 = max(ln.x1 for ln in lines)
    y1 = max(ln.y1 for ln in lines)

    out.append(Paragraph(
        id=0,
        text=text,
        page=lines[0].page,
        y=(y0 + y1) / 2.0,
        bbox=[round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)],
        word_bboxes=[],
    ))


def _extract_page_words(doc: object) -> dict[int, list[WordBBox]]:
    """Extract word-level bounding boxes grouped by page number (1-based)."""
    page_words: dict[int, list[WordBBox]] = {}

    for page_idx in range(len(doc)):  # type: ignore[arg-type]
        page = doc[page_idx]  # type: ignore[index]
        words: list[WordBBox] = []
        for w in page.get_text("words"):
            text = w[4].strip()
            if text:
                words.append(WordBBox(
                    text=text,
                    bbox=[round(w[0], 1), round(w[1], 1), round(w[2], 1), round(w[3], 1)],
                ))
        page_words[page_idx + 1] = words

    return page_words


def _assign_word_bboxes(
    paragraphs: list[Paragraph],
    page_words: dict[int, list[WordBBox]],
) -> None:
    """Assign word bboxes to paragraphs by checking Y-overlap with paragraph bbox."""
    for para in paragraphs:
        words = page_words.get(para.page, [])
        if not words:
            continue

        p_y0 = para.bbox[1]
        p_y1 = para.bbox[3]
        margin = 2.0  # small tolerance for bbox alignment

        matched: list[WordBBox] = []
        for w in words:
            w_y0 = w.bbox[1]
            w_y1 = w.bbox[3]
            # Word overlaps vertically with paragraph
            if w_y1 > p_y0 - margin and w_y0 < p_y1 + margin:
                matched.append(w)

        # Sort by position: top-to-bottom, then left-to-right
        matched.sort(key=lambda wb: (wb.bbox[1], wb.bbox[0]))
        para.word_bboxes = matched
