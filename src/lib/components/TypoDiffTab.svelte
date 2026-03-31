<script lang="ts">
	import type { ValidationIssue } from '$lib/types/validation';

	interface Props {
		resolvedIssues: ValidationIssue[];
		newIssues: ValidationIssue[];
		commonIssues: ValidationIssue[];
		isValidating: boolean;
		validationError: string | null;
		hasReports: boolean;
		onIssueClick?: (issue: ValidationIssue, side: 'left' | 'right') => void;
	}

	let { resolvedIssues, newIssues, commonIssues, isValidating, validationError, hasReports, onIssueClick }: Props = $props();

	function severityIcon(severity: string): string {
		switch (severity) {
			case 'error': return '⊘';
			case 'warning': return '⚠';
			case 'hint': return 'ℹ';
			default: return '•';
		}
	}

	function checkLabel(check: string | undefined): string {
		if (!check) return '';
		// Convert snake_case to readable label
		return check.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
	}
</script>

{#if isValidating}
	<div class="empty-state">Validating...</div>
{:else if validationError}
	<div class="empty-state error">{validationError}</div>
{:else if !hasReports}
	<div class="empty-state">No validation results yet.</div>
{:else if resolvedIssues.length === 0 && newIssues.length === 0 && commonIssues.length === 0}
	<div class="empty-state success">No typographic issues found.</div>
{:else}
	<!-- Resolved issues (only in left = fixed in new version) -->
	{#if resolvedIssues.length > 0}
		<div class="section">
			<div class="section-header resolved">
				<span class="section-badge resolved-badge">{resolvedIssues.length}</span>
				Resolved
			</div>
			{#each resolvedIssues as issue}
				<button
					class="issue-row"
					onclick={() => onIssueClick?.(issue, 'left')}
				>
					<span class="issue-icon severity-{issue.severity}">
						{severityIcon(issue.severity)}
					</span>
					<div class="issue-content">
						{#if issue.check}
							<span class="issue-check">{checkLabel(issue.check)}</span>
						{/if}
						<span class="issue-message">{issue.message}</span>
						{#if issue.snippet}
							<span class="issue-snippet">"{issue.snippet}"</span>
						{/if}
					</div>
					<span class="issue-page">p.{issue.page}</span>
				</button>
			{/each}
		</div>
	{/if}

	<!-- New issues (only in right = introduced in new version) -->
	{#if newIssues.length > 0}
		<div class="section">
			<div class="section-header new-issues">
				<span class="section-badge new-badge">{newIssues.length}</span>
				New
			</div>
			{#each newIssues as issue}
				<button
					class="issue-row"
					onclick={() => onIssueClick?.(issue, 'right')}
				>
					<span class="issue-icon severity-{issue.severity}">
						{severityIcon(issue.severity)}
					</span>
					<div class="issue-content">
						{#if issue.check}
							<span class="issue-check">{checkLabel(issue.check)}</span>
						{/if}
						<span class="issue-message">{issue.message}</span>
						{#if issue.snippet}
							<span class="issue-snippet">"{issue.snippet}"</span>
						{/if}
					</div>
					<span class="issue-page">p.{issue.page}</span>
				</button>
			{/each}
		</div>
	{/if}

	<!-- Unchanged issues (in both) -->
	{#if commonIssues.length > 0}
		<div class="section">
			<div class="section-header unchanged">
				<span class="section-badge unchanged-badge">{commonIssues.length}</span>
				Unchanged
			</div>
			{#each commonIssues as issue}
				<button
					class="issue-row issue-muted"
					onclick={() => onIssueClick?.(issue, 'right')}
				>
					<span class="issue-icon severity-{issue.severity}">
						{severityIcon(issue.severity)}
					</span>
					<div class="issue-content">
						{#if issue.check}
							<span class="issue-check">{checkLabel(issue.check)}</span>
						{/if}
						<span class="issue-message">{issue.message}</span>
					</div>
					<span class="issue-page">p.{issue.page}</span>
				</button>
			{/each}
		</div>
	{/if}
{/if}

<style>
	.empty-state {
		padding: var(--spacing-lg);
		color: var(--text-secondary);
		font-size: var(--font-size-caption);
		text-align: center;
	}

	.empty-state.error {
		color: var(--accent-red);
	}

	.empty-state.success {
		color: var(--accent-green);
	}

	.section {
		border-bottom: 0.5px solid var(--border-color);
	}

	.section-header {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		padding: var(--spacing-sm) var(--spacing-md);
		font-size: var(--font-size-caption);
		font-weight: 600;
		color: var(--text-secondary);
		background: var(--bg-secondary);
	}

	.section-badge {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 18px;
		height: 18px;
		padding: 0 5px;
		border-radius: 9px;
		font-size: 10px;
		font-weight: 700;
		color: white;
	}

	.resolved-badge { background: var(--accent-green); }
	.new-badge { background: var(--accent-orange); }
	.unchanged-badge { background: var(--text-secondary); }

	.issue-row {
		display: flex;
		align-items: flex-start;
		gap: var(--spacing-sm);
		padding: var(--spacing-sm) var(--spacing-md);
		border: none;
		border-bottom: 0.5px solid var(--border-color);
		background: transparent;
		cursor: pointer;
		text-align: left;
		font-family: var(--font-family);
		transition: background 0.1s;
		width: 100%;
	}

	.issue-row:last-child {
		border-bottom: none;
	}

	.issue-row:hover {
		background: rgba(0, 0, 0, 0.03);
	}

	.issue-row.issue-muted {
		opacity: 0.6;
	}

	.issue-icon {
		flex-shrink: 0;
		width: 18px;
		height: 18px;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 12px;
	}

	.issue-icon.severity-error { color: var(--accent-red); }
	.issue-icon.severity-warning { color: var(--accent-orange); }
	.issue-icon.severity-hint { color: var(--accent-blue); }

	.issue-content {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 1px;
	}

	.issue-check {
		font-size: 10px;
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.3px;
	}

	.issue-message {
		font-size: var(--font-size-caption);
		color: var(--text-primary);
		line-height: 1.3;
	}

	.issue-snippet {
		font-size: 10px;
		color: var(--text-secondary);
		font-style: italic;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.issue-page {
		flex-shrink: 0;
		font-size: 10px;
		color: var(--text-secondary);
		padding-top: 1px;
	}
</style>
