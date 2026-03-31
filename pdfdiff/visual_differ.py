"""Visual PDF comparison — pixel-level diff using PyMuPDF rendering.

Renders each page as a pixmap and computes per-pixel differences.
Detects layout shifts, image changes, color changes — everything
that text-based diff cannot see.
"""

from __future__ import annotations

import base64

from pdfdiff.models import PageVisualDiff, VisualDiffResult


def visual_diff(
    left_path: str,
    right_path: str,
    *,
    dpi: int = 150,
    threshold: float = 0.1,
) -> VisualDiffResult:
    """Compare two PDFs visually page by page.

    Args:
        left_path: Path to the original PDF.
        right_path: Path to the modified PDF.
        dpi: Render resolution (higher = more precise but slower).
        threshold: Percentage below which pages are considered identical.

    Returns:
        VisualDiffResult with per-page diff images and change percentages.
    """
    import fitz  # type: ignore[import-not-found]

    left_doc = fitz.open(left_path)
    right_doc = fitz.open(right_path)

    total_left = len(left_doc)
    total_right = len(right_doc)
    max_pages = max(total_left, total_right)

    pages: list[PageVisualDiff] = []

    for page_idx in range(max_pages):
        left_pix = _render_page(left_doc, page_idx, dpi) if page_idx < total_left else None
        right_pix = _render_page(right_doc, page_idx, dpi) if page_idx < total_right else None

        if left_pix is None and right_pix is not None:
            # Page only in right — 100% changed
            diff_png = _pixmap_to_png_base64(right_pix)
            pages.append(PageVisualDiff(
                page=page_idx + 1,
                changed_pixels_percent=100.0,
                diff_image_base64=diff_png,
            ))
        elif right_pix is None and left_pix is not None:
            # Page only in left — 100% changed (removed)
            diff_png = _pixmap_to_png_base64(left_pix)
            pages.append(PageVisualDiff(
                page=page_idx + 1,
                changed_pixels_percent=100.0,
                diff_image_base64=diff_png,
            ))
        elif left_pix is not None and right_pix is not None:
            changed_pct, diff_png = _compute_diff(left_pix, right_pix)
            if changed_pct >= threshold:
                pages.append(PageVisualDiff(
                    page=page_idx + 1,
                    changed_pixels_percent=round(changed_pct, 4),
                    diff_image_base64=diff_png,
                ))

    left_doc.close()
    right_doc.close()

    return VisualDiffResult(
        pages=pages,
        total_pages_left=total_left,
        total_pages_right=total_right,
        dpi=dpi,
    )


def _render_page(doc: object, page_idx: int, dpi: int) -> object:
    """Render a single page to a pixmap at given DPI."""
    page = doc[page_idx]  # type: ignore[index]
    mat = _dpi_matrix(dpi)
    return page.get_pixmap(matrix=mat, alpha=False)


def _dpi_matrix(dpi: int) -> object:
    """Create a PyMuPDF Matrix for the given DPI."""
    import fitz  # type: ignore[import-not-found]
    zoom = dpi / 72.0
    return fitz.Matrix(zoom, zoom)


def _compute_diff(
    left_pix: object,
    right_pix: object,
) -> tuple[float, str]:
    """Compute pixel difference between two pixmaps.

    Returns (changed_percent, diff_image_base64_png).
    Uses pure Python byte comparison (no numpy dependency).
    """
    import fitz  # type: ignore[import-not-found]

    # Ensure same dimensions by padding the smaller one
    w = max(left_pix.width, right_pix.width)  # type: ignore[union-attr]
    h = max(left_pix.height, right_pix.height)  # type: ignore[union-attr]

    left_samples = left_pix.samples  # type: ignore[union-attr]
    right_samples = right_pix.samples  # type: ignore[union-attr]
    left_stride = left_pix.stride  # type: ignore[union-attr]
    right_stride = right_pix.stride  # type: ignore[union-attr]
    left_n = left_pix.n  # type: ignore[union-attr]
    right_n = right_pix.n  # type: ignore[union-attr]
    left_w = left_pix.width  # type: ignore[union-attr]
    left_h = left_pix.height  # type: ignore[union-attr]
    right_w = right_pix.width  # type: ignore[union-attr]
    right_h = right_pix.height  # type: ignore[union-attr]

    # Build diff image
    diff_pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, w, h), 1)
    diff_pix.clear_with(255)  # white background with full alpha

    total_pixels = w * h
    changed_pixels = 0
    pixel_threshold = 30  # per-channel difference threshold

    for y in range(h):
        for x in range(w):
            # Get left pixel (white if outside bounds)
            if x < left_w and y < left_h:
                li = y * left_stride + x * left_n
                lr, lg, lb = left_samples[li], left_samples[li + 1], left_samples[li + 2]
            else:
                lr, lg, lb = 255, 255, 255

            # Get right pixel
            if x < right_w and y < right_h:
                ri = y * right_stride + x * right_n
                rr, rg, rb = right_samples[ri], right_samples[ri + 1], right_samples[ri + 2]
            else:
                rr, rg, rb = 255, 255, 255

            # Compare
            dr = abs(lr - rr)
            dg = abs(lg - rg)
            db = abs(lb - rb)

            di = y * diff_pix.stride + x * diff_pix.n
            if dr > pixel_threshold or dg > pixel_threshold or db > pixel_threshold:
                changed_pixels += 1
                # Red highlight for changed pixels
                diff_pix.samples_mv[di] = 255
                diff_pix.samples_mv[di + 1] = 50
                diff_pix.samples_mv[di + 2] = 50
                diff_pix.samples_mv[di + 3] = 200
            else:
                # Faded original for unchanged pixels
                gray = (lr + lg + lb) // 3
                faded = 200 + (gray - 200) // 4
                diff_pix.samples_mv[di] = faded
                diff_pix.samples_mv[di + 1] = faded
                diff_pix.samples_mv[di + 2] = faded
                diff_pix.samples_mv[di + 3] = 255

    changed_pct = (changed_pixels / total_pixels * 100.0) if total_pixels > 0 else 0.0
    diff_png = _pixmap_to_png_base64(diff_pix)

    return changed_pct, diff_png


def _pixmap_to_png_base64(pix: object) -> str:
    """Convert a PyMuPDF Pixmap to base64-encoded PNG."""
    png_bytes = pix.tobytes("png")  # type: ignore[union-attr]
    return base64.b64encode(png_bytes).decode("ascii")
