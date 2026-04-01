<script lang="ts">
	import type { PDFDocumentProxy } from 'pdfjs-dist';

	interface Props {
		pdfDoc: PDFDocumentProxy;
		currentPage: number;
		onGoToPage: (page: number) => void;
	}

	let { pdfDoc, currentPage, onGoToPage }: Props = $props();

	const THUMB_SCALE = 0.15;

	interface ThumbData {
		pageNum: number;
		canvas: HTMLCanvasElement;
	}

	let thumbs: ThumbData[] = $state([]);

	$effect(() => {
		// Re-render thumbnails when pdfDoc changes
		const doc = pdfDoc;
		if (!doc) return;

		const renderAll = async () => {
			const result: ThumbData[] = [];
			for (let pageNum = 1; pageNum <= doc.numPages; pageNum++) {
				const page = await doc.getPage(pageNum);
				const viewport = page.getViewport({ scale: THUMB_SCALE });

				const canvas = document.createElement('canvas');
				canvas.width = viewport.width;
				canvas.height = viewport.height;
				canvas.style.width = `${viewport.width}px`;
				canvas.style.height = `${viewport.height}px`;

				const context = canvas.getContext('2d')!;
				await page.render({ canvasContext: context, viewport }).promise;

				result.push({ pageNum, canvas });
			}
			thumbs = result;
		};

		renderAll();
	});
</script>

<div class="thumb-sidebar">
	{#each thumbs as thumb (thumb.pageNum)}
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="thumb-item"
			class:thumb-active={thumb.pageNum === currentPage}
			onclick={() => onGoToPage(thumb.pageNum)}
		>
			{@html thumb.canvas.outerHTML}
			<span class="thumb-label">{thumb.pageNum}</span>
		</div>
	{/each}
</div>

<style>
	.thumb-sidebar {
		width: 80px;
		overflow-y: auto;
		background: var(--bg-primary, #ffffff);
		border-right: 0.5px solid var(--border-color, #d1d1d1);
		padding: 4px;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 4px;
		flex-shrink: 0;
	}

	.thumb-item {
		cursor: pointer;
		border: 2px solid transparent;
		border-radius: 3px;
		padding: 2px;
		text-align: center;
		transition: border-color 0.15s;
	}

	.thumb-item:hover {
		border-color: rgba(0, 0, 0, 0.15);
	}

	.thumb-item.thumb-active {
		border-color: var(--accent-blue, #007aff);
	}

	.thumb-label {
		display: block;
		font-size: 9px;
		color: var(--text-secondary, #86868b);
		margin-top: 1px;
	}
</style>
