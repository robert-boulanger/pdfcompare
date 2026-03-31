"""PDF annotation writer — add highlights, freetext, and notes to PDFs.

New module (not ported from Bleisatz). Uses PyMuPDF to write annotations.
"""

from __future__ import annotations

import json


def save_annotations(
    pdf_path: str,
    output_path: str,
    annotations_json: str,
) -> None:
    """Write annotations to a PDF and save to output_path.

    Args:
        pdf_path: Path to the source PDF.
        output_path: Path for the annotated output PDF.
        annotations_json: JSON string with annotation list.

    Annotation JSON format:
        [
            {
                "type": "highlight",
                "page": 1,
                "bbox": [x0, y0, x1, y1],
                "color": [1.0, 1.0, 0.0],
                "content": "optional note text"
            },
            {
                "type": "freetext",
                "page": 1,
                "bbox": [x0, y0, x1, y1],
                "text": "Annotation text",
                "font_size": 11,
                "color": [1.0, 0.0, 0.0]
            },
            {
                "type": "note",
                "page": 1,
                "point": [x, y],
                "text": "Sticky note content",
                "icon": "Comment"
            }
        ]
    """
    import fitz  # type: ignore[import-not-found]

    annotations = json.loads(annotations_json)
    doc = fitz.open(pdf_path)

    for ann in annotations:
        ann_type = ann["type"]
        page_num = ann["page"] - 1  # convert to 0-based
        if page_num < 0 or page_num >= len(doc):
            continue

        page = doc[page_num]

        if ann_type == "highlight":
            _add_highlight(page, ann)
        elif ann_type == "freetext":
            _add_freetext(page, ann)
        elif ann_type == "note":
            _add_note(page, ann)

    doc.save(output_path, deflate=True)
    doc.close()


def _add_highlight(page: object, ann: dict) -> None:
    """Add a highlight annotation to a page."""
    import fitz  # type: ignore[import-not-found]

    bbox = ann["bbox"]
    rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
    highlight = page.add_highlight_annot(rect)  # type: ignore[union-attr]

    color = ann.get("color", [1.0, 1.0, 0.0])  # default yellow
    highlight.set_colors(stroke=color)

    content = ann.get("content", "")
    if content:
        highlight.set_info(content=content)

    highlight.update()


def _add_freetext(page: object, ann: dict) -> None:
    """Add a freetext annotation to a page."""
    import fitz  # type: ignore[import-not-found]

    bbox = ann["bbox"]
    rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
    text = ann.get("text", "")
    font_size = ann.get("font_size", 11)
    color = ann.get("color", [0.0, 0.0, 0.0])

    freetext = page.add_freetext_annot(  # type: ignore[union-attr]
        rect,
        text,
        fontsize=font_size,
        text_color=color,
    )
    freetext.update()


def _add_note(page: object, ann: dict) -> None:
    """Add a sticky note (text annotation) to a page."""
    import fitz  # type: ignore[import-not-found]

    point = ann.get("point", [0, 0])
    pos = fitz.Point(point[0], point[1])
    text = ann.get("text", "")
    icon = ann.get("icon", "Comment")

    note = page.add_text_annot(pos, text, icon=icon)  # type: ignore[union-attr]
    note.update()
