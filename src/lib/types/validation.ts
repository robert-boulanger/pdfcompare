// TypeScript interfaces matching pdfdiff/models.py ValidationReport JSON output

export type Severity = 'hint' | 'warning' | 'error';

export interface ValidationIssue {
	severity: Severity;
	page: number;
	message: string;
	snippet?: string;
	bbox?: [number, number, number, number];
	check?: string;
}

export interface ValidationSummary {
	warnings: number;
	errors: number;
	hints: number;
	total: number;
}

export interface ValidationReport {
	issues: ValidationIssue[];
	pages_checked: number;
	checks_run: string[];
	summary: ValidationSummary;
}
