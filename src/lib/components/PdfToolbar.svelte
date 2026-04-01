<script lang="ts">
	interface Props {
		label: string;
		hasPdf: boolean;
		currentPage: number;
		totalPages: number;
		scale: number;
		showThumbnails: boolean;
		pageInputValue: string;
		onGoToPage: (page: number) => void;
		onZoomIn: () => void;
		onZoomOut: () => void;
		onZoomFit: () => void;
		onToggleThumbnails: () => void;
		onPageInputChange: (value: string) => void;
	}

	let {
		label, hasPdf, currentPage, totalPages, scale,
		showThumbnails, pageInputValue,
		onGoToPage, onZoomIn, onZoomOut, onZoomFit,
		onToggleThumbnails, onPageInputChange
	}: Props = $props();

	function handlePageInput(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			const num = parseInt(pageInputValue);
			if (!isNaN(num)) {
				onGoToPage(num);
			}
		}
	}
</script>

<div class="pdf-toolbar">
	<span class="pdf-label">{label}</span>

	{#if hasPdf}
		<button class="nav-btn" onclick={onToggleThumbnails} title="Toggle thumbnails" class:thumb-toggle-active={showThumbnails}>
			&#9776;
		</button>
		<div class="pdf-nav">
			<button
				class="nav-btn"
				onclick={() => onGoToPage(currentPage - 1)}
				disabled={currentPage <= 1}
				title="Previous page"
			>
				&#9650;
			</button>
			<input
				class="page-input"
				type="text"
				value={pageInputValue}
				oninput={(e) => onPageInputChange(e.currentTarget.value)}
				onkeydown={handlePageInput}
				title="Go to page"
			/>
			<span class="page-total">/ {totalPages}</span>
			<button
				class="nav-btn"
				onclick={() => onGoToPage(currentPage + 1)}
				disabled={currentPage >= totalPages}
				title="Next page"
			>
				&#9660;
			</button>
		</div>

		<div class="zoom-controls">
			<button class="nav-btn" onclick={onZoomOut} title="Zoom out">&#8722;</button>
			<button class="nav-btn zoom-fit" onclick={onZoomFit} title="Fit width">Fit</button>
			<button class="nav-btn" onclick={onZoomIn} title="Zoom in">&#43;</button>
			<span class="zoom-level">{Math.round(scale * 100)}%</span>
		</div>
	{/if}
</div>

<style>
	.pdf-toolbar {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm, 8px);
		padding: var(--spacing-xs, 4px) var(--spacing-sm, 8px);
		background: var(--bg-toolbar, rgba(246, 246, 246, 0.85));
		border-bottom: 0.5px solid var(--border-color, #d1d1d1);
		font-size: var(--font-size-caption, 11px);
		min-height: 32px;
		flex-shrink: 0;
	}

	.pdf-label {
		font-weight: 600;
		color: var(--text-secondary, #86868b);
		text-transform: uppercase;
		letter-spacing: 0.5px;
		margin-right: auto;
	}

	.pdf-nav {
		display: flex;
		align-items: center;
		gap: 2px;
	}

	.nav-btn {
		background: none;
		border: 1px solid transparent;
		border-radius: var(--radius-sm, 4px);
		padding: 2px 6px;
		cursor: pointer;
		font-size: 11px;
		color: var(--text-primary, #1d1d1f);
		line-height: 1;
	}

	.nav-btn:hover {
		background: rgba(0, 0, 0, 0.06);
	}

	.nav-btn:disabled {
		opacity: 0.3;
		cursor: default;
	}

	.nav-btn.zoom-fit {
		font-size: 10px;
		font-weight: 500;
	}

	.page-input {
		width: 36px;
		text-align: center;
		border: 1px solid var(--border-color, #d1d1d1);
		border-radius: var(--radius-sm, 4px);
		padding: 1px 4px;
		font-size: 11px;
		background: var(--bg-primary, #ffffff);
		color: var(--text-primary, #1d1d1f);
		outline: none;
	}

	.page-input:focus {
		border-color: var(--accent-blue, #007aff);
	}

	.page-total {
		color: var(--text-secondary, #86868b);
	}

	.zoom-controls {
		display: flex;
		align-items: center;
		gap: 2px;
	}

	.zoom-level {
		color: var(--text-secondary, #86868b);
		min-width: 36px;
		text-align: right;
	}

	.thumb-toggle-active {
		color: var(--accent-blue, #007aff) !important;
	}
</style>
