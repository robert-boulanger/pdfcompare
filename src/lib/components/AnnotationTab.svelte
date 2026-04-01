<script lang="ts">
	import type { Annotation } from '$lib/types/annotations';

	interface Props {
		annotations: Annotation[];
		selectedId: string | null;
		onSelect: (id: string) => void;
	}

	let { annotations, selectedId, onSelect }: Props = $props();

	let filter: 'all' | 'highlight' | 'note' = $state('all');

	const sorted: Annotation[] = $derived.by(() => {
		const filtered = filter === 'all'
			? annotations
			: annotations.filter(a => a.type === filter);
		return [...filtered].sort((a, b) => {
			if (a.page !== b.page) return a.page - b.page;
			const ay = a.type === 'note' ? a.point[1] : a.bbox[1];
			const by = b.type === 'note' ? b.point[1] : b.bbox[1];
			return ay - by;
		});
	});

	const highlightCount = $derived(annotations.filter(a => a.type === 'highlight').length);
	const noteCount = $derived(annotations.filter(a => a.type === 'note').length);

	function snippet(ann: Annotation): string {
		if (ann.type === 'note') return ann.text;
		return ann.content ?? 'Highlight';
	}

	function colorHex(rgb: [number, number, number]): string {
		return '#' + rgb.map(c => Math.round(c * 255).toString(16).padStart(2, '0')).join('');
	}
</script>

{#if annotations.length === 0}
	<div class="empty-state">No annotations yet.</div>
{:else}
	<div class="filter-bar">
		<button class="filter-btn" class:active={filter === 'all'} onclick={() => filter = 'all'}>
			All ({annotations.length})
		</button>
		<button class="filter-btn filter-highlight" class:active={filter === 'highlight'} onclick={() => filter = 'highlight'}>
			&#9724; {highlightCount}
		</button>
		<button class="filter-btn filter-note" class:active={filter === 'note'} onclick={() => filter = 'note'}>
			&#128172; {noteCount}
		</button>
	</div>

	<div class="ann-list">
		{#each sorted as ann (ann.id)}
			<button
				class="ann-row"
				class:selected={selectedId === ann.id}
				onclick={() => onSelect(ann.id)}
			>
				<span class="ann-icon" style:background={colorHex(ann.color)}>
					{ann.type === 'note' ? '💬' : ''}
				</span>
				<div class="ann-content">
					<span class="ann-type">{ann.type === 'note' ? 'Note' : 'Highlight'}</span>
					<span class="ann-snippet">{snippet(ann)}</span>
					<span class="ann-page">p.{ann.page}</span>
				</div>
			</button>
		{/each}
	</div>
{/if}

<style>
	.empty-state {
		padding: var(--spacing-lg);
		color: var(--text-secondary);
		font-size: var(--font-size-caption);
		text-align: center;
	}

	.filter-bar {
		display: flex;
		gap: 2px;
		padding: var(--spacing-sm);
		border-bottom: 0.5px solid var(--border-color);
	}

	.filter-btn {
		flex: 1;
		padding: 3px 6px;
		border: none;
		border-radius: 3px;
		background: transparent;
		font-family: var(--font-family);
		font-size: 10px;
		font-weight: 500;
		color: var(--text-secondary);
		cursor: pointer;
		transition: all 0.15s;
	}

	.filter-btn:hover {
		background: rgba(0, 0, 0, 0.04);
	}

	.filter-btn.active {
		background: var(--bg-secondary);
		color: var(--text-primary);
	}

	.filter-highlight.active { color: var(--accent-orange); }
	.filter-note.active { color: var(--accent-blue); }

	.ann-list {
		display: flex;
		flex-direction: column;
	}

	.ann-row {
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

	.ann-row:hover {
		background: rgba(0, 0, 0, 0.03);
	}

	.ann-row.selected {
		background: rgba(0, 122, 255, 0.08);
	}

	.ann-icon {
		flex-shrink: 0;
		width: 18px;
		height: 18px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 3px;
		font-size: 10px;
	}

	.ann-content {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.ann-type {
		font-size: 10px;
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.3px;
	}

	.ann-snippet {
		font-size: var(--font-size-caption);
		color: var(--text-primary);
		line-height: 1.4;
		overflow: hidden;
		text-overflow: ellipsis;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
	}

	.ann-page {
		font-size: 10px;
		color: var(--text-secondary);
	}
</style>
