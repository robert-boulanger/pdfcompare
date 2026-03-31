"""Data models for pdfdiff — paragraphs, diffs, validation issues."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# Paragraph extraction models
# ---------------------------------------------------------------------------

@dataclass
class WordBBox:
    """A single word with its bounding box."""

    text: str
    bbox: list[float]  # [x0, y0, x1, y1]


@dataclass
class Paragraph:
    """A paragraph extracted from a PDF with position data."""

    id: int
    text: str
    page: int  # 1-based
    y: float  # vertical center of bbox
    bbox: list[float]  # [x0, y0, x1, y1]
    word_bboxes: list[WordBBox] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Diff models
# ---------------------------------------------------------------------------

@dataclass
class ParagraphMapping:
    """Maps a paragraph index in the left PDF to one in the right PDF."""

    left: int | None
    right: int | None


@dataclass
class WordChange:
    """A word-level change within a paragraph diff."""

    type: str  # "added", "removed", "changed"
    left_words: list[str] = field(default_factory=list)
    right_words: list[str] = field(default_factory=list)
    left_bboxes: list[list[float]] = field(default_factory=list)
    right_bboxes: list[list[float]] = field(default_factory=list)


@dataclass
class Difference:
    """A single difference between two PDFs."""

    type: str  # "added", "removed", "changed"
    left_para: int | None
    right_para: int | None
    left_snippet: str | None
    right_snippet: str | None
    left_page: int | None
    right_page: int | None
    left_bbox: list[float] | None
    right_bbox: list[float] | None
    word_changes: list[WordChange] = field(default_factory=list)


@dataclass
class DiffSummary:
    """Summary statistics for a PDF diff."""

    total_paragraphs_left: int
    total_paragraphs_right: int
    added: int
    removed: int
    changed: int
    unchanged: int


@dataclass
class DiffResult:
    """Complete result of comparing two PDFs."""

    paragraphs_left: list[Paragraph]
    paragraphs_right: list[Paragraph]
    paragraph_map: list[ParagraphMapping]
    differences: list[Difference]
    summary: DiffSummary

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(asdict(self), ensure_ascii=False)


# ---------------------------------------------------------------------------
# Validation / Analysis models
# ---------------------------------------------------------------------------

class Severity(Enum):
    HINT = "hint"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationIssue:
    """A single typographic issue found during analysis."""

    severity: Severity
    page: int
    message: str
    snippet: str = ""
    bbox: list[float] | None = None
    check: str = ""

    def to_dict(self) -> dict:
        """Serialize to dict for JSON output."""
        d: dict = {
            "severity": self.severity.value,
            "page": self.page,
            "message": self.message,
        }
        if self.snippet:
            d["snippet"] = self.snippet
        if self.bbox:
            d["bbox"] = self.bbox
        if self.check:
            d["check"] = self.check
        return d


@dataclass
class ValidationReport:
    """Complete validation report for a PDF."""

    issues: list[ValidationIssue] = field(default_factory=list)
    pages_checked: int = 0
    checks_run: list[str] = field(default_factory=list)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)

    @property
    def hint_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.HINT)

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({
            "issues": [i.to_dict() for i in self.issues],
            "pages_checked": self.pages_checked,
            "checks_run": self.checks_run,
            "summary": {
                "warnings": self.warning_count,
                "errors": self.error_count,
                "hints": self.hint_count,
                "total": len(self.issues),
            },
        }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Document type detection
# ---------------------------------------------------------------------------

class DocumentType(Enum):
    BOOK = "book"
    MAGAZINE = "magazine"
    FLYER = "flyer"


# ---------------------------------------------------------------------------
# Visual diff models
# ---------------------------------------------------------------------------

@dataclass
class PageVisualDiff:
    """Visual diff result for a single page."""

    page: int  # 1-based
    changed_pixels_percent: float
    diff_image_base64: str  # PNG as base64


@dataclass
class VisualDiffResult:
    """Complete visual diff result."""

    pages: list[PageVisualDiff]
    total_pages_left: int
    total_pages_right: int
    dpi: int

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(asdict(self), ensure_ascii=False)
