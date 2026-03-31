import { invoke } from '@tauri-apps/api/core';
import type { DiffResult, Difference, Highlight } from '$lib/types/diff';

// Reactive state
let diffResult: DiffResult | null = $state(null);
let isComparing = $state(false);
let compareError: string | null = $state(null);
let selectedDifferenceIndex: number | null = $state(null);

// Derived highlights for left and right panels (with word-level bboxes)
const leftHighlights: Highlight[] = $derived.by(() => {
	const dr = diffResult;
	if (!dr) return [];
	return dr.differences
		.filter((d) => d.left_bbox && d.left_page)
		.map((d, i) => ({
			page: d.left_page!,
			bbox: d.left_bbox!,
			type: d.type,
			snippet: d.left_snippet ?? '',
			differenceIndex: i,
			wordBboxes: d.word_changes
				?.flatMap((wc) => wc.left_bboxes)
		}));
});

const rightHighlights: Highlight[] = $derived.by(() => {
	const dr = diffResult;
	if (!dr) return [];
	return dr.differences
		.filter((d) => d.right_bbox && d.right_page)
		.map((d, i) => ({
			page: d.right_page!,
			bbox: d.right_bbox!,
			type: d.type,
			snippet: d.right_snippet ?? '',
			differenceIndex: i,
			wordBboxes: d.word_changes
				?.flatMap((wc) => wc.right_bboxes)
		}));
});

const selectedDifference: Difference | null = $derived.by(() => {
	const dr = diffResult;
	const idx = selectedDifferenceIndex;
	if (!dr || idx === null) return null;
	return dr.differences[idx] ?? null;
});

async function runDiff(leftPath: string, rightPath: string): Promise<void> {
	isComparing = true;
	compareError = null;
	diffResult = null;
	selectedDifferenceIndex = null;

	try {
		const json = await invoke<string>('diff_pdfs', {
			leftPath,
			rightPath
		});
		diffResult = JSON.parse(json) as DiffResult;
	} catch (e) {
		compareError = e instanceof Error ? e.message : String(e);
	} finally {
		isComparing = false;
	}
}

function selectDifference(index: number | null): void {
	selectedDifferenceIndex = index;
}

function clearDiff(): void {
	diffResult = null;
	isComparing = false;
	compareError = null;
	selectedDifferenceIndex = null;
}

export function getDiffStore() {
	return {
		get diffResult() { return diffResult; },
		get isComparing() { return isComparing; },
		get compareError() { return compareError; },
		get selectedDifferenceIndex() { return selectedDifferenceIndex; },
		get selectedDifference() { return selectedDifference; },
		get leftHighlights() { return leftHighlights; },
		get rightHighlights() { return rightHighlights; },
		runDiff,
		selectDifference,
		clearDiff
	};
}
