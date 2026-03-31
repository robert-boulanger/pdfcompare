import { invoke } from '@tauri-apps/api/core';
import type { ValidationReport, ValidationIssue } from '$lib/types/validation';
import type { ValidationHighlight, ValidationHighlightType } from '$lib/types/diff';

// Reactive state
let leftReport: ValidationReport | null = $state(null);
let rightReport: ValidationReport | null = $state(null);
let isValidating = $state(false);
let validationError: string | null = $state(null);

// Match issues between left and right by check + snippet
function issueKey(issue: ValidationIssue): string {
	return `${issue.check ?? ''}::${issue.snippet ?? ''}::${issue.message}`;
}

// Issues only in left (resolved in the new version)
const resolvedIssues: ValidationIssue[] = $derived.by(() => {
	if (!leftReport || !rightReport) return [];
	const rightKeys = new Set(rightReport.issues.map(issueKey));
	return leftReport.issues.filter((i) => !rightKeys.has(issueKey(i)));
});

// Issues only in right (new in the new version)
const newIssues: ValidationIssue[] = $derived.by(() => {
	if (!leftReport || !rightReport) return [];
	const leftKeys = new Set(leftReport.issues.map(issueKey));
	return rightReport.issues.filter((i) => !leftKeys.has(issueKey(i)));
});

// Issues present in both
const commonIssues: ValidationIssue[] = $derived.by(() => {
	if (!leftReport || !rightReport) return [];
	const rightKeys = new Set(rightReport.issues.map(issueKey));
	return leftReport.issues.filter((i) => rightKeys.has(issueKey(i)));
});

// Convert issues to highlights for rendering in PDF panels
function issuesToHighlights(issues: ValidationIssue[], type: ValidationHighlightType): ValidationHighlight[] {
	return issues
		.filter((i) => i.bbox && i.page > 0)
		.map((i) => ({
			page: i.page,
			bbox: i.bbox as [number, number, number, number],
			type,
			message: i.message
		}));
}

// Highlights for left panel: resolved (green) + common (dimmed orange)
const leftValidationHighlights: ValidationHighlight[] = $derived.by(() => {
	return [
		...issuesToHighlights(resolvedIssues, 'resolved'),
		...issuesToHighlights(commonIssues, 'unchanged')
	];
});

// Highlights for right panel: new (orange) + common (dimmed orange)
const rightValidationHighlights: ValidationHighlight[] = $derived.by(() => {
	return [
		...issuesToHighlights(newIssues, 'new'),
		...issuesToHighlights(commonIssues, 'unchanged')
	];
});

async function runValidation(leftPath: string, rightPath: string): Promise<void> {
	isValidating = true;
	validationError = null;
	leftReport = null;
	rightReport = null;

	try {
		const [leftJson, rightJson] = await Promise.all([
			invoke<string>('validate_pdf', { pdfPath: leftPath }),
			invoke<string>('validate_pdf', { pdfPath: rightPath })
		]);
		leftReport = JSON.parse(leftJson) as ValidationReport;
		rightReport = JSON.parse(rightJson) as ValidationReport;
	} catch (e) {
		validationError = e instanceof Error ? e.message : String(e);
	} finally {
		isValidating = false;
	}
}

function clearValidation(): void {
	leftReport = null;
	rightReport = null;
	isValidating = false;
	validationError = null;
}

export function getValidationStore() {
	return {
		get leftReport() { return leftReport; },
		get rightReport() { return rightReport; },
		get isValidating() { return isValidating; },
		get validationError() { return validationError; },
		get resolvedIssues() { return resolvedIssues; },
		get newIssues() { return newIssues; },
		get commonIssues() { return commonIssues; },
		get leftValidationHighlights() { return leftValidationHighlights; },
		get rightValidationHighlights() { return rightValidationHighlights; },
		runValidation,
		clearValidation
	};
}
