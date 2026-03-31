"""Document type detection — classify PDFs as book, magazine, or flyer.

Heuristic based on the ratio of text area vs. image/vector area per page.
"""

from __future__ import annotations

from pdfdiff.models import DocumentType


def detect_document_type(pdf_path: str) -> DocumentType:
    """Detect document type based on text vs. graphic content ratio.

    Categories:
        BOOK: >70% text area (text-heavy, long-form content)
        MAGAZINE: 30-70% text area (mixed text and graphics)
        FLYER: <30% text area (graphic-heavy, short content)

    Uses PyMuPDF to measure text bounding boxes vs. image/drawing areas.
    """
    import fitz  # type: ignore[import-not-found]

    doc = fitz.open(pdf_path)
    if len(doc) == 0:
        doc.close()
        return DocumentType.FLYER

    text_ratios: list[float] = []

    for page_idx in range(min(len(doc), 20)):  # sample up to 20 pages
        page = doc[page_idx]
        page_area = page.rect.width * page.rect.height
        if page_area <= 0:
            continue

        text_area = _measure_text_area(page)
        image_area = _measure_image_area(page)

        total_content = text_area + image_area
        if total_content <= 0:
            text_ratios.append(0.0)
        else:
            text_ratios.append(text_area / total_content)

    doc.close()

    if not text_ratios:
        return DocumentType.FLYER

    avg_text_ratio = sum(text_ratios) / len(text_ratios)

    if avg_text_ratio > 0.70:
        return DocumentType.BOOK
    elif avg_text_ratio > 0.30:
        return DocumentType.MAGAZINE
    else:
        return DocumentType.FLYER


def _measure_text_area(page: object) -> float:
    """Measure total text bounding box area on a page."""
    import fitz  # type: ignore[import-not-found]

    total = 0.0
    blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]  # type: ignore[union-attr]

    for block in blocks:
        if block["type"] != 0:  # skip non-text
            continue
        bbox = block["bbox"]
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        if w > 0 and h > 0:
            total += w * h

    return total


def _measure_image_area(page: object) -> float:
    """Measure total image and drawing area on a page."""
    total = 0.0

    # Images
    for img in page.get_images(full=True):  # type: ignore[union-attr]
        xref = img[0]
        try:
            rects = page.get_image_rects(xref)  # type: ignore[union-attr]
            for rect in rects:
                if rect.width > 0 and rect.height > 0:
                    total += rect.width * rect.height
        except Exception:
            pass

    # Drawings (vector graphics)
    try:
        for drawing in page.get_drawings():  # type: ignore[union-attr]
            rect = drawing.get("rect")
            if rect:
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                if w > 5 and h > 5:  # skip tiny decorations
                    total += w * h
    except Exception:
        pass

    return total
