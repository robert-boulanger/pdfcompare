// TypeScript interfaces for PDF annotations
// Matches pdfdiff/annotator.py JSON format

export type AnnotationTool = 'none' | 'highlight' | 'note';

export interface HighlightAnnotation {
	type: 'highlight';
	id: string;
	page: number; // 1-based
	bbox: [number, number, number, number]; // [x0, y0, x1, y1] in PDF points
	color: [number, number, number]; // RGB 0.0-1.0 for PyMuPDF
	content?: string; // optional comment text
}

export interface NoteAnnotation {
	type: 'note';
	id: string;
	page: number;
	point: [number, number]; // [x, y] in PDF points
	text: string;
	icon: string;
	color: [number, number, number];
}

export type Annotation = HighlightAnnotation | NoteAnnotation;

// Color presets as RGB tuples (0.0-1.0) for PyMuPDF
export const ANNOTATION_COLORS: { name: string; rgb: [number, number, number]; hex: string }[] = [
	{ name: 'Yellow', rgb: [1.0, 1.0, 0.0], hex: '#ffff00' },
	{ name: 'Green', rgb: [0.0, 1.0, 0.0], hex: '#00ff00' },
	{ name: 'Blue', rgb: [0.0, 0.5, 1.0], hex: '#0080ff' },
	{ name: 'Red', rgb: [1.0, 0.0, 0.0], hex: '#ff0000' },
];

// Export format matching annotator.py expectations (no id, camelCase → snake_case)
export interface ExportHighlight {
	type: 'highlight';
	page: number;
	bbox: [number, number, number, number];
	color: [number, number, number];
	content?: string;
}

export interface ExportNote {
	type: 'note';
	page: number;
	point: [number, number];
	text: string;
	icon: string;
}

export type ExportAnnotation = ExportHighlight | ExportNote;
