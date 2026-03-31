import type {
	Annotation,
	AnnotationTool,
	ExportAnnotation,
} from '$lib/types/annotations';
import { ANNOTATION_COLORS } from '$lib/types/annotations';

let annotations: Annotation[] = $state([]);
let activeTool: AnnotationTool = $state('none');
let activeColorIndex = $state(0);
let isDirty = $state(false);
let selectedId: string | null = $state(null);

const activeColor = $derived(ANNOTATION_COLORS[activeColorIndex]);

const annotationsByPage = $derived.by(() => {
	const map = new Map<number, Annotation[]>();
	for (const ann of annotations) {
		const list = map.get(ann.page) ?? [];
		list.push(ann);
		map.set(ann.page, list);
	}
	return map;
});

const selectedAnnotation = $derived.by(() => {
	if (!selectedId) return null;
	return annotations.find((a) => a.id === selectedId) ?? null;
});

let nextId = 0;
function generateId(): string {
	return `ann_${Date.now()}_${nextId++}`;
}

function addAnnotation(ann: Omit<Annotation, 'id'>): string {
	const id = generateId();
	const full = { ...ann, id } as Annotation;
	annotations = [...annotations, full];
	isDirty = true;
	selectedId = id;
	return id;
}

function removeAnnotation(id: string): void {
	annotations = annotations.filter((a) => a.id !== id);
	if (selectedId === id) selectedId = null;
	isDirty = true;
}

function updateAnnotation(id: string, updates: Partial<Annotation>): void {
	annotations = annotations.map((a) =>
		a.id === id ? { ...a, ...updates } as Annotation : a
	);
	isDirty = true;
}

function selectAnnotation(id: string | null): void {
	selectedId = id;
}

function setTool(tool: AnnotationTool): void {
	activeTool = tool;
	if (tool !== 'none') selectedId = null;
}

function setColorIndex(index: number): void {
	activeColorIndex = index;
}

function clearAnnotations(): void {
	annotations = [];
	isDirty = false;
	selectedId = null;
	activeTool = 'none';
}

function markSaved(): void {
	isDirty = false;
}

function toExportJson(): string {
	const exported: ExportAnnotation[] = annotations.map((ann) => {
		switch (ann.type) {
			case 'highlight':
				return {
					type: 'highlight',
					page: ann.page,
					bbox: ann.bbox,
					color: ann.color,
					...(ann.content ? { content: ann.content } : {}),
				};
			case 'note':
				return {
					type: 'note',
					page: ann.page,
					point: ann.point,
					text: ann.text,
					icon: ann.icon,
				};
		}
	});
	return JSON.stringify(exported);
}

export function getAnnotationStore() {
	return {
		get annotations() { return annotations; },
		get activeTool() { return activeTool; },
		get activeColor() { return activeColor; },
		get activeColorIndex() { return activeColorIndex; },
		get isDirty() { return isDirty; },
		get selectedId() { return selectedId; },
		get annotationsByPage() { return annotationsByPage; },
		get selectedAnnotation() { return selectedAnnotation; },
		addAnnotation,
		removeAnnotation,
		updateAnnotation,
		selectAnnotation,
		setTool,
		setColorIndex,
		clearAnnotations,
		markSaved,
		toExportJson,
	};
}
