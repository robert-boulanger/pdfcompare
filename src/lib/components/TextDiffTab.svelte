<script lang="ts">
	import type { DiffResult, Difference, DifferenceType } from '$lib/types/diff';

	interface Props {
		diffResult: DiffResult | null;
		selectedIndex: number | null;
		onSelect: (index: number) => void;
	}

	let { diffResult, selectedIndex, onSelect }: Props = $props();

	let filter: DifferenceType | 'all' = $state('all');

	const filteredDifferences: { diff: Difference; originalIndex: number }[] = $derived.by(() => {
		if (!diffResult) return [];
		return diffResult.differences
			.map((diff, i) => ({ diff, originalIndex: i }))
			.filter(({ diff }) => filter === 'all' || diff.type === filter);
	});

	function typeIcon(type: DifferenceType): string {
		switch (type) {
			case 'added': return '+';
			case 'removed': return '−';
			case 'changed': return '~';
		}
	}

	function typeLabel(type: DifferenceType): string {
		switch (type) {
			case 'added': return 'Added';
			case 'removed': return 'Removed';
			case 'changed': return 'Changed';
		}
	}
</script>

{#if !diffResult}
	<div class="empty-state">Run Compare to see text differences.</div>
{:else if diffResult.differences.length === 0}
	<div class="empty-state">No differences found.</div>
{:else}
	<!-- Filter bar -->
	<div class="filter-bar">
		<button class="filter-btn" class:active={filter === 'all'} onclick={() => filter = 'all'}>
			All ({diffResult.differences.length})
		</button>
		<button class="filter-btn filter-added" class:active={filter === 'added'} onclick={() => filter = 'added'}>
			+ {diffResult.summary.added}
		</button>
		<button class="filter-btn filter-removed" class:active={filter === 'removed'} onclick={() => filter = 'removed'}>
			− {diffResult.summary.removed}
		</button>
		<button class="filter-btn filter-changed" class:active={filter === 'changed'} onclick={() => filter = 'changed'}>
			~ {diffResult.summary.changed}
		</button>
	</div>

	<!-- Difference list -->
	<div class="diff-list">
		{#each filteredDifferences as { diff, originalIndex } (originalIndex)}
			<button
				class="diff-row"
				class:selected={selectedIndex === originalIndex}
				class:type-added={diff.type === 'added'}
				class:type-removed={diff.type === 'removed'}
				class:type-changed={diff.type === 'changed'}
				onclick={() => onSelect(originalIndex)}
			>
				<span class="diff-icon type-{diff.type}" title={typeLabel(diff.type)}>
					{typeIcon(diff.type)}
				</span>
				<div class="diff-content">
					<span class="diff-snippet">
						{#if diff.type === 'removed'}
							{diff.left_snippet ?? ''}
						{:else if diff.type === 'added'}
							{diff.right_snippet ?? ''}
						{:else}
							{diff.left_snippet ?? ''}
						{/if}
					</span>
					<span class="diff-page">
						p.{diff.left_page ?? diff.right_page ?? '?'}
					</span>
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

	.filter-added.active { color: var(--accent-green); }
	.filter-removed.active { color: var(--accent-red); }
	.filter-changed.active { color: var(--accent-orange); }

	.diff-list {
		display: flex;
		flex-direction: column;
	}

	.diff-row {
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

	.diff-row:hover {
		background: rgba(0, 0, 0, 0.03);
	}

	.diff-row.selected {
		background: rgba(0, 122, 255, 0.08);
	}

	.diff-icon {
		flex-shrink: 0;
		width: 18px;
		height: 18px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 3px;
		font-size: 12px;
		font-weight: 700;
	}

	.diff-icon.type-added {
		background: rgba(52, 199, 89, 0.15);
		color: var(--accent-green);
	}

	.diff-icon.type-removed {
		background: rgba(255, 59, 48, 0.15);
		color: var(--accent-red);
	}

	.diff-icon.type-changed {
		background: rgba(255, 149, 0, 0.15);
		color: var(--accent-orange);
	}

	.diff-content {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.diff-snippet {
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

	.diff-page {
		font-size: 10px;
		color: var(--text-secondary);
	}
</style>
