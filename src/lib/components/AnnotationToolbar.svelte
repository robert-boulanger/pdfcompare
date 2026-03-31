<script lang="ts">
	import type { AnnotationTool } from '$lib/types/annotations';
	import { ANNOTATION_COLORS } from '$lib/types/annotations';

	interface Props {
		activeTool: AnnotationTool;
		activeColorIndex: number;
		isDirty: boolean;
		hasSelection: boolean;
		onToolChange: (tool: AnnotationTool) => void;
		onColorChange: (index: number) => void;
		onSave: () => void;
		onDelete: () => void;
	}

	let { activeTool, activeColorIndex, isDirty, hasSelection, onToolChange, onColorChange, onSave, onDelete }: Props = $props();

	const tools: { tool: AnnotationTool; label: string; icon: string; title: string }[] = [
		{ tool: 'highlight', label: 'Highlight', icon: '🖍', title: 'Highlight area (H)' },
		{ tool: 'note', label: 'Note', icon: '💬', title: 'Add note (N)' },
	];

	function toggleTool(tool: AnnotationTool) {
		onToolChange(activeTool === tool ? 'none' : tool);
	}
</script>

<div class="annotation-toolbar">
	<div class="tool-group">
		{#each tools as t}
			<button
				class="tool-btn"
				class:tool-active={activeTool === t.tool}
				onclick={() => toggleTool(t.tool)}
				title={t.title}
			>
				<span class="tool-icon">{t.icon}</span>
				<span class="tool-label">{t.label}</span>
			</button>
		{/each}
	</div>

	{#if activeTool !== 'none'}
		<div class="separator"></div>
		<div class="color-group">
			{#each ANNOTATION_COLORS as color, i}
				<button
					class="color-btn"
					class:color-active={activeColorIndex === i}
					style:background-color={color.hex}
					onclick={() => onColorChange(i)}
					title={color.name}
				></button>
			{/each}
		</div>
	{/if}

	<div class="spacer"></div>

	{#if hasSelection}
		<button class="action-btn delete-btn" onclick={onDelete} title="Delete selected annotation (Del)">
			Delete
		</button>
	{/if}

	{#if isDirty}
		<button class="action-btn save-btn" onclick={onSave} title="Save annotations to PDF (Cmd+S)">
			Save PDF
		</button>
	{/if}
</div>

<style>
	.annotation-toolbar {
		display: flex;
		align-items: center;
		gap: var(--spacing-xs, 4px);
		padding: var(--spacing-xs, 4px) var(--spacing-md, 12px);
		background: var(--bg-toolbar, rgba(246, 246, 246, 0.85));
		border-bottom: 0.5px solid var(--border-color, #d1d1d1);
		min-height: 32px;
		flex-shrink: 0;
	}

	.tool-group {
		display: flex;
		gap: 2px;
	}

	.tool-btn {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 3px 10px;
		border: 1px solid var(--border-color, #d1d1d1);
		border-radius: var(--radius-sm, 4px);
		background: var(--bg-primary, #ffffff);
		font-size: var(--font-size-caption, 11px);
		color: var(--text-primary, #1d1d1f);
		cursor: pointer;
		font-family: var(--font-family);
		transition: background 0.15s, border-color 0.15s;
	}

	.tool-btn:hover {
		background: rgba(0, 0, 0, 0.04);
	}

	.tool-btn.tool-active {
		background: rgba(0, 122, 255, 0.1);
		border-color: var(--accent-blue, #007aff);
		color: var(--accent-blue, #007aff);
	}

	.tool-icon {
		font-size: 13px;
		line-height: 1;
	}

	.tool-label {
		font-weight: 500;
	}

	.separator {
		width: 1px;
		height: 18px;
		background: var(--border-color, #d1d1d1);
		margin: 0 4px;
	}

	.color-group {
		display: flex;
		gap: 4px;
	}

	.color-btn {
		width: 18px;
		height: 18px;
		border-radius: 50%;
		border: 2px solid transparent;
		cursor: pointer;
		transition: border-color 0.15s, transform 0.1s;
	}

	.color-btn:hover {
		transform: scale(1.15);
	}

	.color-btn.color-active {
		border-color: var(--text-primary, #1d1d1f);
		box-shadow: 0 0 0 1px var(--bg-primary, #ffffff);
	}

	.spacer {
		flex: 1;
	}

	.action-btn {
		padding: 3px 10px;
		border: 1px solid var(--border-color, #d1d1d1);
		border-radius: var(--radius-sm, 4px);
		font-size: var(--font-size-caption, 11px);
		font-weight: 600;
		cursor: pointer;
		font-family: var(--font-family);
		transition: background 0.15s;
	}

	.delete-btn {
		background: var(--bg-primary, #ffffff);
		color: var(--accent-red, #ff3b30);
		border-color: var(--accent-red, #ff3b30);
	}

	.delete-btn:hover {
		background: rgba(255, 59, 48, 0.1);
	}

	.save-btn {
		background: var(--accent-blue, #007aff);
		color: white;
		border-color: var(--accent-blue, #007aff);
	}

	.save-btn:hover {
		background: color-mix(in srgb, var(--accent-blue, #007aff) 85%, black);
	}
</style>
