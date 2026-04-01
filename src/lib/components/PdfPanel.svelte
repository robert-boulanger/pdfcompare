<script lang="ts">
	import { invoke, convertFileSrc } from '@tauri-apps/api/core';
	import { initPdfJs, pdfjsLib } from '$lib/services/pdfjs-setup';
	import type { PDFDocumentProxy, RenderTask } from 'pdfjs-dist';
	import type { TextContent } from 'pdfjs-dist/types/src/display/api';
	import type { Highlight, ValidationHighlight } from '$lib/types/diff';
	import type { Annotation, AnnotationTool } from '$lib/types/annotations';
	import NotePopover from './NotePopover.svelte';
	import PdfToolbar from './PdfToolbar.svelte';
	import PdfThumbnailSidebar from './PdfThumbnailSidebar.svelte';

	export interface ScrollInfo {
		page: number;
		scrollRatio: number;
	}

	interface Props {
		pdfPath: string | null;
		label: string;
		side?: 'left' | 'right';
		highlights?: Highlight[];
		activeHighlightIndex?: number | null;
		validationHighlights?: ValidationHighlight[];
		onHighlightClick?: (differenceIndex: number) => void;
		onScrollChange?: (info: ScrollInfo) => void;
		annotations?: Annotation[];
		selectedAnnotationId?: string | null;
		annotationTool?: AnnotationTool;
		onAnnotationCreate?: (ann: Omit<Annotation, 'id'>) => void;
		onAnnotationSelect?: (id: string | null) => void;
		onAnnotationUpdate?: (id: string, updates: Partial<Annotation>) => void;
		onAnnotationDelete?: (id: string) => void;
		annotationColor?: [number, number, number];
	}

	let { pdfPath, label, side = 'left', highlights = [], activeHighlightIndex = null, validationHighlights = [], onHighlightClick, onScrollChange, annotations = [], selectedAnnotationId = null, annotationTool = 'none', onAnnotationCreate, onAnnotationSelect, onAnnotationUpdate, onAnnotationDelete, annotationColor = [1, 1, 0] }: Props = $props();

	let isProgrammaticScroll = false;

	let containerEl: HTMLDivElement | undefined = $state();
	let pagesContainerEl: HTMLDivElement | undefined = $state();
	let pdfDoc: PDFDocumentProxy | null = $state(null);
	let currentPage = $state(1);
	let totalPages = $state(0);
	let scale = $state(1.0);
	let isLoading = $state(false);
	let error: string | null = $state(null);
	let pageInputValue = $state('1');

	let renderedPages = new Map<number, { canvas: HTMLCanvasElement; textLayer: HTMLDivElement; overlay: HTMLDivElement }>();
	let showThumbnails = $state(false);
	let activeRenderTasks: RenderTask[] = [];

	const ZOOM_STEP = 0.15;
	const MIN_SCALE = 0.25;
	const MAX_SCALE = 5.0;

	let lastLoadedPath: string | null = null;

	$effect(() => {
		initPdfJs();
	});

	$effect(() => {
		const path = pdfPath;
		if (path !== lastLoadedPath) {
			lastLoadedPath = path;
			if (path) {
				loadPdf(path);
			} else {
				cleanup();
			}
		}
	});

	// Cleanup on component destroy
	$effect(() => {
		return () => cleanup();
	});

	async function loadPdf(path: string) {
		cleanup();
		isLoading = true;
		error = null;

		try {
			const assetUrl = convertFileSrc(path);
			let data: Uint8Array | string;
			try {
				const response = await fetch(assetUrl);
				if (!response.ok) throw new Error(`Asset fetch failed: ${response.status}`);
				const buffer = await response.arrayBuffer();
				data = new Uint8Array(buffer);
			} catch {
				const base64 = await invoke<string>('load_pdf_file', { path });
				const binaryString = atob(base64);
				data = new Uint8Array(binaryString.length);
				for (let i = 0; i < binaryString.length; i++) {
					data[i] = binaryString.charCodeAt(i);
				}
			}

			pdfDoc = await pdfjsLib.getDocument({ data }).promise;
			totalPages = pdfDoc.numPages;
			currentPage = 1;
			pageInputValue = '1';

			await fitWidth();
			await renderVisiblePages();
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
			pdfDoc = null;
		} finally {
			isLoading = false;
		}
	}

	async function fitWidth() {
		if (!pdfDoc || !containerEl) return;
		const page = await pdfDoc.getPage(1);
		const viewport = page.getViewport({ scale: 1.0 });
		const containerWidth = containerEl.clientWidth - 24;
		scale = containerWidth / viewport.width;
	}

	async function renderVisiblePages() {
		if (!pdfDoc || !pagesContainerEl) return;

		cancelRenderTasks();
		pagesContainerEl.innerHTML = '';
		renderedPages.clear();

		for (let pageNum = 1; pageNum <= totalPages; pageNum++) {
			await renderPage(pageNum);
		}
	}

	function cancelRenderTasks() {
		for (const task of activeRenderTasks) {
			task.cancel();
		}
		activeRenderTasks = [];
	}

	async function renderPage(pageNum: number) {
		if (!pdfDoc || !pagesContainerEl) return;

		const page = await pdfDoc.getPage(pageNum);
		const viewport = page.getViewport({ scale });

		const pageWrapper = document.createElement('div');
		pageWrapper.className = 'pdf-page-wrapper';
		pageWrapper.dataset.pageNum = String(pageNum);
		pageWrapper.style.width = `${viewport.width}px`;
		pageWrapper.style.height = `${viewport.height}px`;

		const canvas = document.createElement('canvas');
		const context = canvas.getContext('2d')!;
		const dpr = window.devicePixelRatio || 1;
		canvas.width = Math.floor(viewport.width * dpr);
		canvas.height = Math.floor(viewport.height * dpr);
		canvas.style.width = `${viewport.width}px`;
		canvas.style.height = `${viewport.height}px`;
		context.scale(dpr, dpr);
		pageWrapper.appendChild(canvas);

		const textLayerDiv = document.createElement('div');
		textLayerDiv.className = 'pdf-text-layer';
		textLayerDiv.style.width = `${viewport.width}px`;
		textLayerDiv.style.height = `${viewport.height}px`;
		pageWrapper.appendChild(textLayerDiv);

		const overlayDiv = document.createElement('div');
		overlayDiv.className = 'pdf-overlay-layer';
		overlayDiv.style.width = `${viewport.width}px`;
		overlayDiv.style.height = `${viewport.height}px`;
		pageWrapper.appendChild(overlayDiv);

		pagesContainerEl.appendChild(pageWrapper);

		const renderTask = page.render({ canvasContext: context, viewport });
		activeRenderTasks.push(renderTask);

		try {
			await renderTask.promise;
			const textContent: TextContent = await page.getTextContent();
			const textLayer = new pdfjsLib.TextLayer({
				textContentSource: textContent,
				container: textLayerDiv,
				viewport
			});
			await textLayer.render();
		} catch (e) {
			if (e instanceof Error && e.name !== 'RenderingCancelledException') {
				console.error(`Error rendering page ${pageNum}:`, e);
			}
		}

		renderedPages.set(pageNum, { canvas, textLayer: textLayerDiv, overlay: overlayDiv });
	}

	function cleanup() {
		cancelRenderTasks();
		renderedPages.clear();
		if (pagesContainerEl) {
			pagesContainerEl.innerHTML = '';
		}
		if (pdfDoc) {
			pdfDoc.destroy();
			pdfDoc = null;
		}
		totalPages = 0;
		currentPage = 1;
		error = null;
	}

	let scrollDebounceTimer: ReturnType<typeof setTimeout> | null = null;

	function handleScroll() {
		if (!pagesContainerEl) return;

		const scrollTop = pagesContainerEl.scrollTop;
		const wrappers = pagesContainerEl.querySelectorAll('.pdf-page-wrapper');

		for (const wrapper of wrappers) {
			const el = wrapper as HTMLElement;
			const offsetTop = el.offsetTop;
			const height = el.offsetHeight;

			if (scrollTop >= offsetTop - height / 2 && scrollTop < offsetTop + height / 2) {
				const pageNum = Number(el.dataset.pageNum);
				if (pageNum !== currentPage) {
					currentPage = pageNum;
					pageInputValue = String(pageNum);
				}
				break;
			}
		}

		// Emit scroll position for sync (debounced, skip programmatic scrolls)
		if (!isProgrammaticScroll && onScrollChange) {
			if (scrollDebounceTimer) clearTimeout(scrollDebounceTimer);
			scrollDebounceTimer = setTimeout(() => {
				const maxScroll = pagesContainerEl!.scrollHeight - pagesContainerEl!.clientHeight;
				const ratio = maxScroll > 0 ? scrollTop / maxScroll : 0;
				onScrollChange!({ page: currentPage, scrollRatio: ratio });
			}, 50);
		}
	}

	function goToPage(pageNum: number) {
		if (pageNum < 1 || pageNum > totalPages || !pagesContainerEl) return;

		const wrapper = pagesContainerEl.querySelector(
			`[data-page-num="${pageNum}"]`
		) as HTMLElement | null;
		if (wrapper) {
			pagesContainerEl.scrollTo({ top: wrapper.offsetTop, behavior: 'smooth' });
			currentPage = pageNum;
			pageInputValue = String(pageNum);
		}
	}

	async function zoomIn() {
		scale = Math.min(scale + ZOOM_STEP, MAX_SCALE);
		renderedPages.clear();
		await renderVisiblePages();
	}

	async function zoomOut() {
		scale = Math.max(scale - ZOOM_STEP, MIN_SCALE);
		renderedPages.clear();
		await renderVisiblePages();
	}

	async function zoomFit() {
		await fitWidth();
		renderedPages.clear();
		await renderVisiblePages();
	}

	// --- Highlight rendering ---

	function getDiffColor(type: string, isActive: boolean): { bg: string; border: string } {
		const alpha = isActive ? 0.3 : 0.1;
		const borderAlpha = isActive ? 0.7 : 0.25;

		if (type === 'added') {
			return { bg: `rgba(52, 199, 89, ${alpha})`, border: `rgba(52, 199, 89, ${borderAlpha})` };
		}
		if (type === 'removed') {
			return { bg: `rgba(255, 59, 48, ${alpha})`, border: `rgba(255, 59, 48, ${borderAlpha})` };
		}
		if (side === 'left') {
			return { bg: `rgba(255, 59, 48, ${alpha})`, border: `rgba(255, 59, 48, ${borderAlpha})` };
		}
		return { bg: `rgba(52, 199, 89, ${alpha})`, border: `rgba(52, 199, 89, ${borderAlpha})` };
	}

	const VALIDATION_COLORS: Record<string, { bg: string; border: string }> = {
		resolved: { bg: 'rgba(52, 199, 89, 0.2)', border: 'rgba(52, 199, 89, 0.5)' },
		new: { bg: 'rgba(255, 149, 0, 0.2)', border: 'rgba(255, 149, 0, 0.5)' },
		unchanged: { bg: 'rgba(255, 149, 0, 0.08)', border: 'rgba(255, 149, 0, 0.2)' }
	};

	function createHighlightEl(
		bbox: [number, number, number, number],
		bg: string,
		border: string,
		opts?: { title?: string; dataIndex?: string; dataType?: string; onClick?: () => void }
	): HTMLDivElement {
		const [x0, y0, x1, y1] = bbox;
		const el = document.createElement('div');
		el.className = 'pdf-highlight';
		if (opts?.dataType) el.dataset.type = opts.dataType;
		if (opts?.dataIndex) el.dataset.index = opts.dataIndex;
		el.style.position = 'absolute';
		el.style.left = `${x0 * scale}px`;
		el.style.top = `${y0 * scale}px`;
		el.style.width = `${(x1 - x0) * scale}px`;
		el.style.height = `${(y1 - y0) * scale}px`;
		el.style.background = bg;
		el.style.border = `1px solid ${border}`;
		el.style.borderRadius = '2px';
		el.style.pointerEvents = 'auto';
		el.style.cursor = 'pointer';
		if (opts?.title) el.title = opts.title;
		if (opts?.onClick) el.addEventListener('click', opts.onClick);
		return el;
	}

	function renderHighlightsForPage(pageNum: number) {
		const pageData = renderedPages.get(pageNum);
		if (!pageData) return;

		const overlay = pageData.overlay;
		// Remove non-annotation elements
		overlay.querySelectorAll('.pdf-highlight').forEach(el => el.remove());

		const viewportWidth = parseFloat(overlay.style.width);
		const viewportHeight = parseFloat(overlay.style.height);

		const pageHighlights = highlights.filter((h) => h.page === pageNum);
		for (const hl of pageHighlights) {
			const isActive = activeHighlightIndex === hl.differenceIndex;
			const colors = getDiffColor(hl.type, isActive);

			if (hl.wordBboxes && hl.wordBboxes.length > 0) {
				for (const wbbox of hl.wordBboxes) {
					if (wbbox[0] * scale > viewportWidth || wbbox[1] * scale > viewportHeight) continue;
					const el = createHighlightEl(wbbox, colors.bg, colors.border, {
						title: hl.snippet,
						dataIndex: String(hl.differenceIndex),
						dataType: hl.type,
						onClick: () => onHighlightClick?.(hl.differenceIndex)
					});
					overlay.appendChild(el);
				}
			} else {
				if (hl.bbox[0] * scale > viewportWidth || hl.bbox[1] * scale > viewportHeight) continue;
				const el = createHighlightEl(hl.bbox, colors.bg, colors.border, {
					title: hl.snippet,
					dataIndex: String(hl.differenceIndex),
					dataType: hl.type,
					onClick: () => onHighlightClick?.(hl.differenceIndex)
				});
				overlay.appendChild(el);
			}
		}

		const pageValHighlights = validationHighlights.filter((vh) => vh.page === pageNum);
		for (const vh of pageValHighlights) {
			if (vh.bbox[0] * scale > viewportWidth || vh.bbox[1] * scale > viewportHeight) continue;
			const colors = VALIDATION_COLORS[vh.type] ?? VALIDATION_COLORS['unchanged'];
			const el = createHighlightEl(vh.bbox, colors.bg, colors.border, {
				title: vh.message,
				dataType: `val-${vh.type}`
			});
			overlay.appendChild(el);
		}
	}

	// --- Annotation rendering ---

	function rgbToHex(rgb: [number, number, number]): string {
		return '#' + rgb.map(c => Math.round(c * 255).toString(16).padStart(2, '0')).join('');
	}

	function renderAnnotationsForPage(pageNum: number) {
		const pageData = renderedPages.get(pageNum);
		if (!pageData) return;

		const overlay = pageData.overlay;
		overlay.querySelectorAll('.pdf-annotation').forEach(el => el.remove());

		const pageAnns = annotations.filter(a => a.page === pageNum);
		for (const ann of pageAnns) {
			const isSelected = selectedAnnotationId === ann.id;

			if (ann.type === 'highlight') {
				const [x0, y0, x1, y1] = ann.bbox;
				const hex = rgbToHex(ann.color);
				const el = document.createElement('div');
				el.className = 'pdf-annotation ann-highlight';
				if (isSelected) el.classList.add('ann-selected');
				el.dataset.annId = ann.id;
				el.style.position = 'absolute';
				el.style.left = `${x0 * scale}px`;
				el.style.top = `${y0 * scale}px`;
				el.style.width = `${(x1 - x0) * scale}px`;
				el.style.height = `${(y1 - y0) * scale}px`;
				el.style.background = `${hex}40`;
				el.style.border = isSelected ? '2px solid var(--accent-blue, #007aff)' : `1px solid ${hex}80`;
				el.style.borderRadius = '2px';
				el.style.pointerEvents = 'auto';
				el.style.cursor = 'pointer';
				if (ann.content) el.title = ann.content;
				el.addEventListener('click', (e) => {
					e.stopPropagation();
					onAnnotationSelect?.(ann.id);
					showPopoverForAnnotation(ann);
				});
				overlay.appendChild(el);

				if (ann.content) {
					const badge = document.createElement('div');
					badge.className = 'pdf-annotation ann-comment-badge';
					badge.style.position = 'absolute';
					badge.style.left = `${x1 * scale - 2}px`;
					badge.style.top = `${y0 * scale - 8}px`;
					badge.style.fontSize = '12px';
					badge.style.cursor = 'pointer';
					badge.style.pointerEvents = 'auto';
					badge.textContent = '💬';
					badge.addEventListener('click', (e) => {
						e.stopPropagation();
						onAnnotationSelect?.(ann.id);
						showPopoverForAnnotation(ann);
					});
					overlay.appendChild(badge);
				}
			} else if (ann.type === 'note') {
				const [x, y] = ann.point;
				const el = document.createElement('div');
				el.className = 'pdf-annotation ann-note';
				if (isSelected) el.classList.add('ann-selected');
				el.dataset.annId = ann.id;
				el.style.position = 'absolute';
				el.style.left = `${x * scale - 10}px`;
				el.style.top = `${y * scale - 10}px`;
				el.style.width = '22px';
				el.style.height = '22px';
				el.style.fontSize = '17px';
				el.style.lineHeight = '22px';
				el.style.textAlign = 'center';
				el.style.cursor = 'pointer';
				el.style.pointerEvents = 'auto';
				el.style.filter = isSelected ? 'drop-shadow(0 0 3px var(--accent-blue, #007aff))' : 'none';
				el.textContent = '💬';
				el.title = ann.text;
				el.addEventListener('click', (e) => {
					e.stopPropagation();
					onAnnotationSelect?.(ann.id);
					showPopoverForAnnotation(ann);
				});
				overlay.appendChild(el);
			}
		}
	}

	// --- Popover state ---

	let popover: { x: number; y: number; text: string; annId: string; annType: 'highlight' | 'note' } | null = $state(null);
	let pendingNote: { pageNum: number; pdfX: number; pdfY: number; screenX: number; screenY: number } | null = $state(null);

	function showPopoverForAnnotation(ann: Annotation) {
		const pageData = renderedPages.get(ann.page);
		if (!pageData) return;
		const wrapper = pageData.canvas.closest('.pdf-page-wrapper') as HTMLElement;
		if (!wrapper) return;
		const wrapperRect = wrapper.getBoundingClientRect();

		if (ann.type === 'note') {
			const [x, y] = ann.point;
			popover = { x: wrapperRect.left + x * scale, y: wrapperRect.top + y * scale, text: ann.text, annId: ann.id, annType: 'note' };
		} else if (ann.type === 'highlight') {
			const [, , x1, y0] = ann.bbox;
			popover = { x: wrapperRect.left + x1 * scale, y: wrapperRect.top + y0 * scale, text: ann.content ?? '', annId: ann.id, annType: 'highlight' };
		}
	}

	function closePopover() {
		popover = null;
		pendingNote = null;
	}

	function handlePopoverSubmit(text: string) {
		if (pendingNote && onAnnotationCreate) {
			onAnnotationCreate({
				type: 'note',
				page: pendingNote.pageNum,
				point: [pendingNote.pdfX, pendingNote.pdfY],
				text,
				icon: 'Comment',
				color: annotationColor
			} as Omit<Annotation, 'id'>);
			pendingNote = null;
			return;
		}
		if (popover && onAnnotationUpdate) {
			if (popover.annType === 'note') {
				onAnnotationUpdate(popover.annId, { text });
			} else if (popover.annType === 'highlight') {
				onAnnotationUpdate(popover.annId, { content: text || undefined });
			}
		}
		popover = null;
	}

	function handlePopoverDelete() {
		if (popover) {
			const id = popover.annId;
			popover = null;
			onAnnotationSelect?.(null);
			onAnnotationDelete?.(id);
		}
	}

	function renderAllHighlights() {
		for (const pageNum of renderedPages.keys()) {
			renderHighlightsForPage(pageNum);
			renderAnnotationsForPage(pageNum);
		}
	}

	$effect(() => {
		const _ = [highlights.length, activeHighlightIndex, validationHighlights.length, annotations, selectedAnnotationId];
		void _;
		renderAllHighlights();
	});

	// --- Annotation creation (drag) ---

	let dragStart: { x: number; y: number; pageNum: number } | null = $state(null);
	let dragRect: HTMLDivElement | null = $state(null);

	function getPageAndCoords(e: MouseEvent): { pageNum: number; pdfX: number; pdfY: number; wrapper: HTMLElement } | null {
		if (!pagesContainerEl) return null;

		const wrappers = pagesContainerEl.querySelectorAll('.pdf-page-wrapper');
		for (const w of wrappers) {
			const wrapper = w as HTMLElement;
			const rect = wrapper.getBoundingClientRect();
			if (e.clientX >= rect.left && e.clientX <= rect.right && e.clientY >= rect.top && e.clientY <= rect.bottom) {
				const localX = e.clientX - rect.left;
				const localY = e.clientY - rect.top;
				return { pageNum: Number(wrapper.dataset.pageNum), pdfX: localX / scale, pdfY: localY / scale, wrapper };
			}
		}
		return null;
	}

	function handleAnnotationMouseDown(e: MouseEvent) {
		if (annotationTool === 'none' || !onAnnotationCreate) return;
		if (e.button !== 0) return;

		const hit = getPageAndCoords(e);
		if (!hit) return;

		if (annotationTool === 'highlight') {
			e.preventDefault();
			dragStart = { x: hit.pdfX, y: hit.pdfY, pageNum: hit.pageNum };

			const rect = document.createElement('div');
			rect.className = 'annotation-drag-rect';
			rect.style.position = 'absolute';
			rect.style.left = `${e.clientX - hit.wrapper.getBoundingClientRect().left}px`;
			rect.style.top = `${e.clientY - hit.wrapper.getBoundingClientRect().top}px`;
			rect.style.width = '0';
			rect.style.height = '0';
			rect.style.border = '2px dashed var(--accent-blue, #007aff)';
			rect.style.background = 'rgba(0, 122, 255, 0.1)';
			rect.style.pointerEvents = 'none';
			rect.style.zIndex = '100';
			hit.wrapper.appendChild(rect);
			dragRect = rect;
		} else if (annotationTool === 'note') {
			e.preventDefault();
			const wrapperRect = hit.wrapper.getBoundingClientRect();
			pendingNote = {
				pageNum: hit.pageNum,
				pdfX: hit.pdfX,
				pdfY: hit.pdfY,
				screenX: wrapperRect.left + hit.pdfX * scale,
				screenY: wrapperRect.top + hit.pdfY * scale,
			};
		}
	}

	function handleAnnotationMouseMove(e: MouseEvent) {
		if (!dragStart || !dragRect) return;

		const hit = getPageAndCoords(e);
		if (!hit || hit.pageNum !== dragStart.pageNum) return;

		const wrapperRect = hit.wrapper.getBoundingClientRect();
		const startScreenX = dragStart.x * scale;
		const startScreenY = dragStart.y * scale;
		const currentX = e.clientX - wrapperRect.left;
		const currentY = e.clientY - wrapperRect.top;

		dragRect.style.left = `${Math.min(startScreenX, currentX)}px`;
		dragRect.style.top = `${Math.min(startScreenY, currentY)}px`;
		dragRect.style.width = `${Math.abs(currentX - startScreenX)}px`;
		dragRect.style.height = `${Math.abs(currentY - startScreenY)}px`;
	}

	function handleAnnotationMouseUp(e: MouseEvent) {
		if (!dragStart || !onAnnotationCreate) {
			dragStart = null;
			return;
		}

		const hit = getPageAndCoords(e);
		if (dragRect) {
			dragRect.remove();
			dragRect = null;
		}

		if (!hit || hit.pageNum !== dragStart.pageNum) {
			dragStart = null;
			return;
		}

		const x0 = Math.min(dragStart.x, hit.pdfX);
		const y0 = Math.min(dragStart.y, hit.pdfY);
		const x1 = Math.max(dragStart.x, hit.pdfX);
		const y1 = Math.max(dragStart.y, hit.pdfY);

		if (x1 - x0 < 5 || y1 - y0 < 5) {
			dragStart = null;
			return;
		}

		if (annotationTool === 'highlight') {
			onAnnotationCreate({
				type: 'highlight',
				page: dragStart.pageNum,
				bbox: [x0, y0, x1, y1],
				color: annotationColor,
			} as Omit<Annotation, 'id'>);
		}

		dragStart = null;
	}

	function handleOverlayClick(e: MouseEvent) {
		if (annotationTool === 'none' && onAnnotationSelect) {
			const target = e.target as HTMLElement;
			if (!target.closest('.pdf-annotation')) {
				onAnnotationSelect(null);
			}
		}
	}

	// --- Exported functions ---

	export function syncScrollTo(scrollRatio: number) {
		if (!pagesContainerEl) return;
		isProgrammaticScroll = true;
		const maxScroll = pagesContainerEl.scrollHeight - pagesContainerEl.clientHeight;
		pagesContainerEl.scrollTop = scrollRatio * maxScroll;
		requestAnimationFrame(() => {
			isProgrammaticScroll = false;
		});
	}

	export function flashHighlight(differenceIndex: number) {
		if (!pagesContainerEl) return;
		const el = pagesContainerEl.querySelector(
			`.pdf-highlight[data-index="${differenceIndex}"]`
		) as HTMLElement | null;
		if (!el) return;
		el.classList.remove('highlight-flash');
		void el.offsetWidth;
		el.classList.add('highlight-flash');
	}

	export function scrollToPagePosition(page: number, y?: number) {
		if (!pagesContainerEl) return;

		// Suppress scroll-sync while navigating to a specific position
		isProgrammaticScroll = true;

		const wrapper = pagesContainerEl.querySelector(
			`[data-page-num="${page}"]`
		) as HTMLElement | null;
		if (!wrapper) {
			isProgrammaticScroll = false;
			return;
		}

		if (y !== undefined) {
			const yPixel = y * scale;
			const targetTop = wrapper.offsetTop + yPixel - pagesContainerEl.clientHeight / 3;
			pagesContainerEl.scrollTo({ top: Math.max(0, targetTop), behavior: 'smooth' });
		} else {
			pagesContainerEl.scrollTo({ top: wrapper.offsetTop, behavior: 'smooth' });
		}

		currentPage = page;
		pageInputValue = String(page);

		// Release guard after smooth scroll settles
		requestAnimationFrame(() => {
			isProgrammaticScroll = false;
		});
	}
</script>

<div class="pdf-panel" bind:this={containerEl}>
	<PdfToolbar
		{label}
		hasPdf={!!pdfDoc}
		{currentPage}
		{totalPages}
		{scale}
		{showThumbnails}
		{pageInputValue}
		onGoToPage={goToPage}
		onZoomIn={zoomIn}
		onZoomOut={zoomOut}
		onZoomFit={zoomFit}
		onToggleThumbnails={() => { showThumbnails = !showThumbnails; }}
		onPageInputChange={(v) => { pageInputValue = v; }}
	/>

	<div class="pdf-body">
		{#if showThumbnails && pdfDoc}
			<PdfThumbnailSidebar {pdfDoc} {currentPage} onGoToPage={goToPage} />
		{/if}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<div
			class="pdf-content"
			class:annotation-mode={annotationTool !== 'none'}
			bind:this={pagesContainerEl}
			onscroll={handleScroll}
			onmousedown={handleAnnotationMouseDown}
			onmousemove={handleAnnotationMouseMove}
			onmouseup={handleAnnotationMouseUp}
			onclick={handleOverlayClick}
		>
		{#if isLoading}
			<div class="pdf-status">Loading PDF...</div>
		{:else if error}
			<div class="pdf-status pdf-error">{error}</div>
		{:else if !pdfPath}
			<div class="pdf-status pdf-placeholder">
				<div class="drop-icon">&#128196;</div>
				<p>Drop a PDF here or click "Open" to load</p>
			</div>
		{/if}
		</div>
	</div>

	{#if popover}
		<NotePopover
			x={popover.x}
			y={popover.y}
			text={popover.text}
			placeholder={popover.annType === 'highlight' ? 'Add a comment...' : 'Note text...'}
			onSubmit={handlePopoverSubmit}
			onCancel={closePopover}
			onDelete={handlePopoverDelete}
		/>
	{/if}

	{#if pendingNote}
		<NotePopover
			x={pendingNote.screenX}
			y={pendingNote.screenY}
			placeholder="Note text..."
			onSubmit={handlePopoverSubmit}
			onCancel={closePopover}
		/>
	{/if}
</div>

<style>
	.pdf-panel {
		display: flex;
		flex-direction: column;
		height: 100%;
		background: var(--bg-primary, #ffffff);
		border-radius: var(--radius-md, 6px);
		overflow: hidden;
	}

	.pdf-body {
		display: flex;
		flex: 1;
		overflow: hidden;
	}

	.pdf-content {
		flex: 1;
		overflow: auto;
		padding: 12px;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 8px;
		background: var(--bg-secondary, #f5f5f5);
	}

	.pdf-status {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100%;
		color: var(--text-secondary, #86868b);
		font-size: var(--font-size-body, 13px);
	}

	.pdf-error {
		color: var(--accent-red, #ff3b30);
	}

	.pdf-placeholder {
		text-align: center;
	}

	.drop-icon {
		font-size: 48px;
		margin-bottom: 8px;
		opacity: 0.4;
	}

	:global(.pdf-page-wrapper) {
		position: relative;
		margin-bottom: 8px;
		box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
		background: white;
	}

	:global(.pdf-text-layer) {
		position: absolute;
		top: 0;
		left: 0;
		opacity: 0;
		line-height: 1;
		overflow: hidden;
	}

	:global(.pdf-text-layer ::selection) {
		background: rgba(0, 122, 255, 0.3);
	}

	:global(.pdf-text-layer:hover) {
		opacity: 1;
		color: transparent;
	}

	:global(.pdf-overlay-layer) {
		position: absolute;
		top: 0;
		left: 0;
		pointer-events: none;
	}

	:global(.pdf-highlight:hover) {
		filter: brightness(0.85);
	}

	:global(.pdf-highlight.highlight-flash) {
		animation: flash-pulse 0.6s ease-out;
	}

	@keyframes flash-pulse {
		0% { box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.8); }
		100% { box-shadow: 0 0 0 0 rgba(0, 122, 255, 0); }
	}

	.pdf-content.annotation-mode {
		cursor: crosshair;
	}

	:global(.pdf-annotation) {
		transition: border-color 0.15s;
	}

	:global(.pdf-annotation:hover) {
		filter: brightness(0.9);
	}

	:global(.pdf-annotation.ann-selected) {
		z-index: 10;
	}

	:global(.annotation-drag-rect) {
		border-radius: 2px;
	}
</style>
