"""PDF paragraph diff — compare two lists of extracted paragraphs.

Ported from Bleisatz pdf_diff.py (diff part).
Uses difflib.SequenceMatcher for paragraph-level matching.
"""

from __future__ import annotations

import difflib

from pdfdiff.models import (
    Difference,
    DiffResult,
    DiffSummary,
    Paragraph,
    ParagraphMapping,
    WordBBox,
    WordChange,
)


def diff_paragraphs(
    left: list[Paragraph],
    right: list[Paragraph],
) -> DiffResult:
    """Compare two lists of paragraphs and produce a diff result.

    Uses difflib.SequenceMatcher for paragraph-level matching.
    """
    left_texts = [p.text for p in left]
    right_texts = [p.text for p in right]

    matcher = difflib.SequenceMatcher(None, left_texts, right_texts, autojunk=False)

    paragraph_map: list[ParagraphMapping] = []
    differences: list[Difference] = []
    added = 0
    removed = 0
    changed = 0
    unchanged = 0

    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            for li, ri in zip(range(i1, i2), range(j1, j2), strict=True):
                paragraph_map.append(ParagraphMapping(left=li, right=ri))
                unchanged += 1

        elif op == "replace":
            pairs = min(i2 - i1, j2 - j1)
            for k in range(pairs):
                li = i1 + k
                ri = j1 + k
                paragraph_map.append(ParagraphMapping(left=li, right=ri))
                wc = _compute_word_changes(left[li], right[ri])
                differences.append(Difference(
                    type="changed",
                    left_para=li,
                    right_para=ri,
                    left_snippet=_snippet(left[li].text),
                    right_snippet=_snippet(right[ri].text),
                    left_page=left[li].page,
                    right_page=right[ri].page,
                    left_bbox=left[li].bbox,
                    right_bbox=right[ri].bbox,
                    word_changes=wc,
                ))
                changed += 1

            for li in range(i1 + pairs, i2):
                paragraph_map.append(ParagraphMapping(left=li, right=None))
                differences.append(Difference(
                    type="removed",
                    left_para=li,
                    right_para=None,
                    left_snippet=_snippet(left[li].text),
                    right_snippet=None,
                    left_page=left[li].page,
                    right_page=None,
                    left_bbox=left[li].bbox,
                    right_bbox=None,
                ))
                removed += 1

            for ri in range(j1 + pairs, j2):
                paragraph_map.append(ParagraphMapping(left=None, right=ri))
                differences.append(Difference(
                    type="added",
                    left_para=None,
                    right_para=ri,
                    left_snippet=None,
                    right_snippet=_snippet(right[ri].text),
                    left_page=None,
                    right_page=right[ri].page,
                    left_bbox=None,
                    right_bbox=right[ri].bbox,
                ))
                added += 1

        elif op == "insert":
            for ri in range(j1, j2):
                paragraph_map.append(ParagraphMapping(left=None, right=ri))
                differences.append(Difference(
                    type="added",
                    left_para=None,
                    right_para=ri,
                    left_snippet=None,
                    right_snippet=_snippet(right[ri].text),
                    left_page=None,
                    right_page=right[ri].page,
                    left_bbox=None,
                    right_bbox=right[ri].bbox,
                ))
                added += 1

        elif op == "delete":
            for li in range(i1, i2):
                paragraph_map.append(ParagraphMapping(left=li, right=None))
                differences.append(Difference(
                    type="removed",
                    left_para=li,
                    right_para=None,
                    left_snippet=_snippet(left[li].text),
                    right_snippet=None,
                    left_page=left[li].page,
                    right_page=None,
                    left_bbox=left[li].bbox,
                    right_bbox=None,
                ))
                removed += 1

    summary = DiffSummary(
        total_paragraphs_left=len(left),
        total_paragraphs_right=len(right),
        added=added,
        removed=removed,
        changed=changed,
        unchanged=unchanged,
    )

    return DiffResult(
        paragraphs_left=left,
        paragraphs_right=right,
        paragraph_map=paragraph_map,
        differences=differences,
        summary=summary,
    )


def _snippet(text: str, max_len: int = 80) -> str:
    """Truncate text to a readable snippet."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "\u2026"


def _compute_word_changes(
    left_para: Paragraph,
    right_para: Paragraph,
) -> list[WordChange]:
    """Compute word-level changes between two paragraphs.

    Uses difflib.SequenceMatcher on word lists and maps changed words
    back to their bounding boxes.
    """
    left_words = [wb.text for wb in left_para.word_bboxes]
    right_words = [wb.text for wb in right_para.word_bboxes]

    if not left_words or not right_words:
        return []

    matcher = difflib.SequenceMatcher(None, left_words, right_words, autojunk=False)
    changes: list[WordChange] = []

    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            continue

        lw = left_words[i1:i2]
        rw = right_words[j1:j2]
        lb = [left_para.word_bboxes[k].bbox for k in range(i1, i2)]
        rb = [right_para.word_bboxes[k].bbox for k in range(j1, j2)]

        if op == "replace":
            change_type = "changed"
        elif op == "insert":
            change_type = "added"
        elif op == "delete":
            change_type = "removed"
        else:
            continue

        changes.append(WordChange(
            type=change_type,
            left_words=lw,
            right_words=rw,
            left_bboxes=lb,
            right_bboxes=rb,
        ))

    return changes
