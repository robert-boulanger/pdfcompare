// TypeScript interfaces matching pdfdiff/models.py JSON output

export interface WordBBox {
	text: string;
	bbox: [number, number, number, number];
}

export interface Paragraph {
	id: number;
	text: string;
	page: number; // 1-based
	y: number; // vertical center of bbox
	bbox: [number, number, number, number]; // [x0, y0, x1, y1] in PDF points
	word_bboxes?: WordBBox[];
}

export interface ParagraphMapping {
	left: number | null;
	right: number | null;
}

export type DifferenceType = 'added' | 'removed' | 'changed';

export interface WordChange {
	type: DifferenceType;
	left_words: string[];
	right_words: string[];
	left_bboxes: [number, number, number, number][];
	right_bboxes: [number, number, number, number][];
}

export interface Difference {
	type: DifferenceType;
	left_para: number | null;
	right_para: number | null;
	left_snippet: string | null;
	right_snippet: string | null;
	left_page: number | null;
	right_page: number | null;
	left_bbox: [number, number, number, number] | null;
	right_bbox: [number, number, number, number] | null;
	word_changes?: WordChange[];
}

export interface DiffSummary {
	total_paragraphs_left: number;
	total_paragraphs_right: number;
	added: number;
	removed: number;
	changed: number;
	unchanged: number;
}

export interface DiffResult {
	paragraphs_left: Paragraph[];
	paragraphs_right: Paragraph[];
	paragraph_map: ParagraphMapping[];
	differences: Difference[];
	summary: DiffSummary;
}

// Highlight data derived from DiffResult for rendering on a panel
export interface Highlight {
	page: number;
	bbox: [number, number, number, number];
	type: DifferenceType;
	snippet: string;
	differenceIndex: number; // index into DiffResult.differences
	wordBboxes?: [number, number, number, number][]; // word-level bboxes for fine-grained highlighting
}

export type ValidationHighlightType = 'resolved' | 'new' | 'unchanged';

// Highlight for validation issues
export interface ValidationHighlight {
	page: number;
	bbox: [number, number, number, number];
	type: ValidationHighlightType;
	message: string;
}
