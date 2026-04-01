<script lang="ts">
	interface Props {
		x: number;
		y: number;
		text?: string;
		placeholder?: string;
		readonly?: boolean;
		onSubmit: (text: string) => void;
		onCancel: () => void;
		onDelete?: () => void;
	}

	let { x, y, text = '', placeholder = 'Add a note...', readonly = false, onSubmit, onCancel, onDelete }: Props = $props();

	let inputText = $state('');
	let textareaEl: HTMLTextAreaElement | undefined = $state();
	let initialized = false;

	// Set initial text and focus once on mount
	$effect(() => {
		if (!initialized) {
			initialized = true;
			inputText = text;
		}
		if (textareaEl && !readonly) {
			textareaEl.focus();
			textareaEl.select();
		}
	});

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			e.stopPropagation();
			onCancel();
		}
		if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
			e.preventDefault();
			submit();
		}
	}

	function submit() {
		const trimmed = inputText.trim();
		if (trimmed) onSubmit(trimmed);
		else onCancel();
	}

	// Position the popover: prefer right side, arrow points left to the annotation
	const popoverStyle = $derived.by(() => {
		const left = x + 16;
		const top = y - 20;
		return `left: ${left}px; top: ${top}px;`;
	});
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<div class="popover-backdrop" onclick={onCancel}>
	<div
		class="note-popover"
		style={popoverStyle}
		onclick={(e) => e.stopPropagation()}
		onkeydown={handleKeydown}
	>
		<div class="popover-arrow"></div>
		{#if readonly}
			<div class="popover-text">{text}</div>
			<div class="popover-actions">
				{#if onDelete}
					<button class="popover-btn delete" onclick={onDelete}>Delete</button>
				{/if}
				<button class="popover-btn" onclick={onCancel}>Close</button>
			</div>
		{:else}
			<textarea
				bind:this={textareaEl}
				bind:value={inputText}
				{placeholder}
				rows="3"
				class="popover-textarea"
			></textarea>
			<div class="popover-actions">
				{#if onDelete}
					<button class="popover-btn delete" onclick={onDelete}>Delete</button>
				{/if}
				<div class="spacer"></div>
				<button class="popover-btn" onclick={onCancel}>Cancel</button>
				<button class="popover-btn primary" onclick={submit}>OK</button>
			</div>
		{/if}
	</div>
</div>

<style>
	.popover-backdrop {
		position: fixed;
		inset: 0;
		z-index: 1000;
	}

	.note-popover {
		position: absolute;
		width: 240px;
		background: var(--bg-primary, #ffffff);
		border: 1px solid var(--border-color, #d1d1d1);
		border-radius: var(--radius-md, 6px);
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
		padding: 8px;
		z-index: 1001;
		font-size: var(--font-size-body, 13px);
	}

	.popover-arrow {
		position: absolute;
		left: -6px;
		top: 20px;
		width: 10px;
		height: 10px;
		background: var(--bg-primary, #ffffff);
		border-left: 1px solid var(--border-color, #d1d1d1);
		border-bottom: 1px solid var(--border-color, #d1d1d1);
		transform: rotate(45deg);
	}

	.popover-textarea {
		width: 100%;
		border: 1px solid var(--border-color, #d1d1d1);
		border-radius: var(--radius-sm, 4px);
		padding: 6px 8px;
		font-size: var(--font-size-body, 13px);
		font-family: var(--font-family);
		resize: vertical;
		outline: none;
		background: var(--bg-primary, #ffffff);
		color: var(--text-primary, #1d1d1f);
		box-sizing: border-box;
	}

	.popover-textarea:focus {
		border-color: var(--accent-blue, #007aff);
	}

	.popover-text {
		padding: 4px 2px 8px;
		color: var(--text-primary, #1d1d1f);
		white-space: pre-wrap;
		word-break: break-word;
		line-height: 1.4;
	}

	.popover-actions {
		display: flex;
		gap: 4px;
		margin-top: 6px;
		justify-content: flex-end;
	}

	.spacer {
		flex: 1;
	}

	.popover-btn {
		padding: 3px 10px;
		border: 1px solid var(--border-color, #d1d1d1);
		border-radius: var(--radius-sm, 4px);
		background: var(--bg-primary, #ffffff);
		font-size: var(--font-size-caption, 11px);
		color: var(--text-primary, #1d1d1f);
		cursor: pointer;
		font-family: var(--font-family);
	}

	.popover-btn:hover {
		background: rgba(0, 0, 0, 0.04);
	}

	.popover-btn.primary {
		background: var(--accent-blue, #007aff);
		color: white;
		border-color: var(--accent-blue, #007aff);
	}

	.popover-btn.primary:hover {
		background: color-mix(in srgb, var(--accent-blue, #007aff) 85%, black);
	}

	.popover-btn.delete {
		color: var(--accent-red, #ff3b30);
		border-color: var(--accent-red, #ff3b30);
	}

	.popover-btn.delete:hover {
		background: rgba(255, 59, 48, 0.1);
	}
</style>
