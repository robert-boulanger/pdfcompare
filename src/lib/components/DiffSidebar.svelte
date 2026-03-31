<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		isOpen: boolean;
		activeTab: 'text-diff' | 'typography';
		onTabChange: (tab: 'text-diff' | 'typography') => void;
		onToggle: () => void;
		textDiffContent: Snippet;
		typographyContent: Snippet;
	}

	let { isOpen, activeTab, onTabChange, onToggle, textDiffContent, typographyContent }: Props = $props();

	let sidebarWidth = $state(320);
	let isResizing = $state(false);

	function startResize(e: MouseEvent) {
		e.preventDefault();
		isResizing = true;
		const startX = e.clientX;
		const startWidth = sidebarWidth;

		function onMouseMove(ev: MouseEvent) {
			const delta = startX - ev.clientX;
			sidebarWidth = Math.max(240, Math.min(600, startWidth + delta));
		}

		function onMouseUp() {
			isResizing = false;
			window.removeEventListener('mousemove', onMouseMove);
			window.removeEventListener('mouseup', onMouseUp);
		}

		window.addEventListener('mousemove', onMouseMove);
		window.addEventListener('mouseup', onMouseUp);
	}
</script>

{#if isOpen}
	<div class="sidebar" style:width="{sidebarWidth}px">
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<div
			class="resize-handle"
			class:resizing={isResizing}
			onmousedown={startResize}
			role="separator"
			aria-orientation="vertical"
			aria-valuenow={sidebarWidth}
			aria-valuemin={240}
			aria-valuemax={600}
		></div>

		<!-- Header with tabs -->
		<div class="sidebar-header">
			<div class="segmented-control">
				<button
					class="segment"
					class:active={activeTab === 'text-diff'}
					onclick={() => onTabChange('text-diff')}
				>
					Text-Diff
				</button>
				<button
					class="segment"
					class:active={activeTab === 'typography'}
					onclick={() => onTabChange('typography')}
				>
					Typografie
				</button>
			</div>
			<button class="close-btn" onclick={onToggle} title="Close sidebar">✕</button>
		</div>

		<!-- Tab content -->
		<div class="sidebar-content">
			{#if activeTab === 'text-diff'}
				{@render textDiffContent()}
			{:else}
				{@render typographyContent()}
			{/if}
		</div>
	</div>
{/if}

<style>
	.sidebar {
		display: flex;
		flex-direction: column;
		background: var(--bg-primary);
		border-left: 0.5px solid var(--border-color);
		flex-shrink: 0;
		position: relative;
		overflow: hidden;
	}

	.resize-handle {
		position: absolute;
		left: 0;
		top: 0;
		bottom: 0;
		width: 4px;
		cursor: col-resize;
		z-index: 10;
	}

	.resize-handle:hover,
	.resize-handle.resizing {
		background: var(--accent-blue);
		opacity: 0.3;
	}

	.sidebar-header {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		padding: var(--spacing-sm) var(--spacing-md);
		border-bottom: 0.5px solid var(--border-color);
		flex-shrink: 0;
	}

	.segmented-control {
		display: flex;
		flex: 1;
		background: var(--bg-secondary);
		border-radius: var(--radius-sm);
		padding: 2px;
		gap: 1px;
	}

	.segment {
		flex: 1;
		padding: 4px 8px;
		border: none;
		border-radius: 3px;
		background: transparent;
		font-family: var(--font-family);
		font-size: var(--font-size-caption);
		font-weight: 500;
		color: var(--text-secondary);
		cursor: pointer;
		transition: all 0.15s;
	}

	.segment.active {
		background: var(--bg-primary);
		color: var(--text-primary);
		box-shadow: 0 0.5px 2px rgba(0, 0, 0, 0.1);
	}

	.segment:hover:not(.active) {
		color: var(--text-primary);
	}

	.close-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 20px;
		height: 20px;
		border: none;
		border-radius: var(--radius-sm);
		background: transparent;
		font-size: 11px;
		color: var(--text-secondary);
		cursor: pointer;
	}

	.close-btn:hover {
		background: rgba(0, 0, 0, 0.06);
		color: var(--text-primary);
	}

	.sidebar-content {
		flex: 1;
		overflow-y: auto;
		overflow-x: hidden;
	}
</style>
