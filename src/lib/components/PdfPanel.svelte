<script lang="ts">
	import { invoke, convertFileSrc } from '@tauri-apps/api/core';
	import { initPdfJs, pdfjsLib } from '$lib/services/pdfjs-setup';
	import type { PDFDocumentProxy, RenderTask } from 'pdfjs-dist';
	import type { TextContent } from 'pdfjs-dist/types/src/display/api';
	import type { Highlight, ValidationHighlight } from '$lib/types/diff';
	import type { Annotation, AnnotationTool } from '$lib/types/annotations';

	export interface ScrollInfo {
		page: number;
		scrollRatio: number; // 0..1 within scroll range
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
		annotationColor?: [number, number, number];
	}

	let { pdfPath, label, side = 'left', highlights = [], activeHighlightIndex = null, validationHighlights = [], onHighlightClick, onScrollChange, annotations = [], selectedAnnotationId = null, annotationTool = 'none', onAnnotationCreate, onAnnotationSelect, onAnnotationUpdate, annotationColor = [1, 1, 0] }: Props = $props();

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
	let thumbnailContainerEl: HTMLDivElement | undefined = $state();
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
		// Only react to pdfPath changes, not to other state mutations
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

	async function loadPdf(path: string) {
		cleanup();
		isLoading = true;
		error = null;

		try {
			console.log('[PdfPanel] loadPdf called with path:', path);

			// Strategy 1: Try asset protocol (convertFileSrc)
			const assetUrl = convertFileSrc(path);
			console.log('[PdfPanel] Trying asset URL:', assetUrl);

			let data: Uint8Array | string;
			try {
				// Try loading via asset URL first (faster, no IPC overhead)
				const response = await fetch(assetUrl);
				if (!response.ok) throw new Error(`Asset fetch failed: ${response.status}`);
				const buffer = await response.arrayBuffer();
				data = new Uint8Array(buffer);
				console.log('[PdfPanel] Loaded via asset URL, bytes:', data.length);
			} catch (fetchErr) {
				console.warn('[PdfPanel] Asset URL failed, falling back to IPC:', fetchErr);
				// Strategy 2: Load via Rust command as base64
				const base64 = await invoke<string>('load_pdf_file', { path });
				console.log('[PdfPanel] Got base64 from IPC, length:', base64.length);
				const binaryString = atob(base64);
				data = new Uint8Array(binaryString.length);
				for (let i = 0; i < binaryString.length; i++) {
					data[i] = binaryString.charCodeAt(i);
				}
				console.log('[PdfPanel] Decoded base64 to bytes:', data.length);
			}

			console.log('[PdfPanel] Calling pdfjsLib.getDocument...');
			pdfDoc = await pdfjsLib.getDocument({ data }).promise;
			console.log('[PdfPanel] PDF loaded, pages:', pdfDoc.numPages);
			totalPages = pdfDoc.numPages;
			currentPage = 1;
			pageInputValue = '1';

			await fitWidth();
			await renderVisiblePages();
		} catch (e) {
			console.error('[PdfPanel] loadPdf error:', e);
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
		const containerWidth = containerEl.clientWidth - 24; // padding
		scale = containerWidth / viewport.width;
	}

	async function renderVisiblePages() {
		if (!pdfDoc || !pagesContainerEl) return;

		// Cancel active render tasks
		for (const task of activeRenderTasks) {
			task.cancel();
		}
		activeRenderTasks = [];

		// Clear existing rendered pages
		pagesContainerEl.innerHTML = '';
		renderedPages.clear();

		// Render all pages (for scroll-through)
		for (let pageNum = 1; pageNum <= totalPages; pageNum++) {
			await renderPage(pageNum);
		}
	}

	async function renderPage(pageNum: number) {
		if (!pdfDoc || !pagesContainerEl) return;

		const page = await pdfDoc.getPage(pageNum);
		const viewport = page.getViewport({ scale });

		// Create page wrapper
		const pageWrapper = document.createElement('div');
		pageWrapper.className = 'pdf-page-wrapper';
		pageWrapper.dataset.pageNum = String(pageNum);
		pageWrapper.style.width = `${viewport.width}px`;
		pageWrapper.style.height = `${viewport.height}px`;

		// Create canvas
		const canvas = document.createElement('canvas');
		const context = canvas.getContext('2d')!;
		const dpr = window.devicePixelRatio || 1;
		canvas.width = Math.floor(viewport.width * dpr);
		canvas.height = Math.floor(viewport.height * dpr);
		canvas.style.width = `${viewport.width}px`;
		canvas.style.height = `${viewport.height}px`;
		context.scale(dpr, dpr);

		pageWrapper.appendChild(canvas);

		// Create text layer
		const textLayerDiv = document.createElement('div');
		textLayerDiv.className = 'pdf-text-layer';
		textLayerDiv.style.width = `${viewport.width}px`;
		textLayerDiv.style.height = `${viewport.height}px`;
		pageWrapper.appendChild(textLayerDiv);

		// Create highlight overlay layer
		const overlayDiv = document.createElement('div');
		overlayDiv.className = 'pdf-overlay-layer';
		overlayDiv.style.width = `${viewport.width}px`;
		overlayDiv.style.height = `${viewport.height}px`;
		pageWrapper.appendChild(overlayDiv);

		pagesContainerEl.appendChild(pageWrapper);

		// Render canvas
		const renderTask = page.render({ canvasContext: context, viewport });
		activeRenderTasks.push(renderTask);

		try {
			await renderTask.promise;

			// Render text layer
			const textContent: TextContent = await page.getTextContent();
			const textLayer = new pdfjsLib.TextLayer({
				textContentSource: textContent,
				container: textLayerDiv,
				viewport
			});
			await textLayer.render();
		} catch (e) {
			// RenderingCancelledException is expected when re-rendering
			if (e instanceof Error && e.name !== 'RenderingCancelledException') {
				console.error(`Error rendering page ${pageNum}:`, e);
			}
		}

		renderedPages.set(pageNum, { canvas, textLayer: textLayerDiv, overlay: overlayDiv });
	}

	function cleanup() {
		for (const task of activeRenderTasks) {
			task.cancel();
		}
		activeRenderTasks = [];
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

	function handlePageInput(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			const num = parseInt(pageInputValue);
			if (!isNaN(num)) {
				goToPage(num);
			}
		}
	}

	async function zoomIn() {
		scale = Math.min(scale + ZOOM_STEP, MAX_SCALE);
		await renderVisiblePages();
	}

	async function zoomOut() {
		scale = Math.max(scale - ZOOM_STEP, MIN_SCALE);
		await renderVisiblePages();
	}

	async function zoomFit() {
		await fitWidth();
		await renderVisiblePages();
	}

	// Color scheme: left panel = red (removed), right panel = green (added)
	function getDiffColor(type: string, isActive: boolean): { bg: string; border: string } {
		const alpha = isActive ? 0.3 : 0.1;
		const borderAlpha = isActive ? 0.7 : 0.25;

		if (type === 'added') {
			return {
				bg: `rgba(52, 199, 89, ${alpha})`,
				border: `rgba(52, 199, 89, ${borderAlpha})`
			};
		}
		if (type === 'removed') {
			return {
				bg: `rgba(255, 59, 48, ${alpha})`,
				border: `rgba(255, 59, 48, ${borderAlpha})`
			};
		}
		// changed: red on left, green on right
		if (side === 'left') {
			return {
				bg: `rgba(255, 59, 48, ${alpha})`,
				border: `rgba(255, 59, 48, ${borderAlpha})`
			};
		}
		return {
			bg: `rgba(52, 199, 89, ${alpha})`,
			border: `rgba(52, 199, 89, ${borderAlpha})`
		};
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
		overlay.innerHTML = '';

		const viewportWidth = parseFloat(overlay.style.width);
		const viewportHeight = parseFloat(overlay.style.height);

		// Diff highlights
		const pageHighlights = highlights.filter((h) => h.page === pageNum);
		for (const hl of pageHighlights) {
			const isActive = activeHighlightIndex === hl.differenceIndex;
			const colors = getDiffColor(hl.type, isActive);

			// Word-level highlights for 'changed' type
			if (hl.wordBboxes && hl.wordBboxes.length > 0) {
				// Render each word bbox individually
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
				// Fallback: paragraph-level highlight
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

		// Validation highlights
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

	function rgbToHex(rgb: [number, number, number]): string {
		return '#' + rgb.map(c => Math.round(c * 255).toString(16).padStart(2, '0')).join('');
	}

	function renderAnnotationsForPage(pageNum: number) {
		const pageData = renderedPages.get(pageNum);
		if (!pageData) return;

		const overlay = pageData.overlay;

		// Remove existing annotation elements
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
				el.addEventListener('click', (e) => { e.stopPropagation(); onAnnotationSelect?.(ann.id); });
				overlay.appendChild(el);
			} else if (ann.type === 'freetext') {
				const [x0, y0, x1, y1] = ann.bbox;
				const hex = rgbToHex(ann.color);
				const el = document.createElement('div');
				el.className = 'pdf-annotation ann-freetext';
				if (isSelected) el.classList.add('ann-selected');
				el.dataset.annId = ann.id;
				el.style.position = 'absolute';
				el.style.left = `${x0 * scale}px`;
				el.style.top = `${y0 * scale}px`;
				el.style.width = `${(x1 - x0) * scale}px`;
				el.style.height = `${(y1 - y0) * scale}px`;
				el.style.background = 'rgba(255,255,255,0.9)';
				el.style.border = isSelected ? '2px solid var(--accent-blue, #007aff)' : `1px solid ${hex}`;
				el.style.borderRadius = '3px';
				el.style.padding = '2px 4px';
				el.style.fontSize = `${ann.fontSize * scale}px`;
				el.style.color = hex;
				el.style.overflow = 'hidden';
				el.style.pointerEvents = 'auto';
				el.style.cursor = 'pointer';
				el.style.lineHeight = '1.2';
				el.textContent = ann.text;
				el.addEventListener('click', (e) => { e.stopPropagation(); onAnnotationSelect?.(ann.id); });
				overlay.appendChild(el);
			} else if (ann.type === 'note') {
				const [x, y] = ann.point;
				const el = document.createElement('div');
				el.className = 'pdf-annotation ann-note';
				if (isSelected) el.classList.add('ann-selected');
				el.dataset.annId = ann.id;
				el.style.position = 'absolute';
				el.style.left = `${x * scale - 10}px`;
				el.style.top = `${y * scale - 10}px`;
				el.style.width = '20px';
				el.style.height = '20px';
				el.style.fontSize = '16px';
				el.style.lineHeight = '20px';
				el.style.textAlign = 'center';
				el.style.cursor = 'pointer';
				el.style.pointerEvents = 'auto';
				el.style.filter = isSelected ? 'drop-shadow(0 0 3px var(--accent-blue, #007aff))' : 'none';
				el.textContent = '📌';
				el.title = ann.text;
				el.addEventListener('click', (e) => { e.stopPropagation(); onAnnotationSelect?.(ann.id); });
				overlay.appendChild(el);
			}
		}
	}

	function renderAllHighlights() {
		for (const pageNum of renderedPages.keys()) {
			renderHighlightsForPage(pageNum);
			renderAnnotationsForPage(pageNum);
		}
	}

	// Re-render highlights when any highlight data changes
	$effect(() => {
		// Access reactive deps
		const _ = [highlights.length, activeHighlightIndex, validationHighlights.length, annotations, selectedAnnotationId];
		void _;
		renderAllHighlights();
	});

	// Annotation creation state
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
				return {
					pageNum: Number(wrapper.dataset.pageNum),
					pdfX: localX / scale,
					pdfY: localY / scale,
					wrapper
				};
			}
		}
		return null;
	}

	function handleAnnotationMouseDown(e: MouseEvent) {
		if (annotationTool === 'none' || !onAnnotationCreate) return;
		if (e.button !== 0) return;

		const hit = getPageAndCoords(e);
		if (!hit) return;

		if (annotationTool === 'highlight' || annotationTool === 'freetext') {
			e.preventDefault();
			dragStart = { x: hit.pdfX, y: hit.pdfY, pageNum: hit.pageNum };

			// Create visual drag rectangle
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
			const text = prompt('Note text:');
			if (text) {
				onAnnotationCreate({
					type: 'note',
					page: hit.pageNum,
					point: [hit.pdfX, hit.pdfY],
					text,
					icon: 'Comment',
					color: annotationColor
				} as Omit<Annotation, 'id'>);
			}
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

		const left = Math.min(startScreenX, currentX);
		const top = Math.min(startScreenY, currentY);
		const width = Math.abs(currentX - startScreenX);
		const height = Math.abs(currentY - startScreenY);

		dragRect.style.left = `${left}px`;
		dragRect.style.top = `${top}px`;
		dragRect.style.width = `${width}px`;
		dragRect.style.height = `${height}px`;
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

		// Minimum size check (at least 5 PDF points)
		if (x1 - x0 < 5 || y1 - y0 < 5) {
			dragStart = null;
			return;
		}

		const bbox: [number, number, number, number] = [x0, y0, x1, y1];

		if (annotationTool === 'highlight') {
			onAnnotationCreate({
				type: 'highlight',
				page: dragStart.pageNum,
				bbox,
				color: annotationColor,
			} as Omit<Annotation, 'id'>);
		} else if (annotationTool === 'freetext') {
			const text = prompt('Text:');
			if (text) {
				onAnnotationCreate({
					type: 'freetext',
					page: dragStart.pageNum,
					bbox,
					text,
					fontSize: 11,
					color: annotationColor,
				} as Omit<Annotation, 'id'>);
			}
		}

		dragStart = null;
	}

	function handleOverlayClick(e: MouseEvent) {
		// Deselect annotation if clicking on empty area
		if (annotationTool === 'none' && onAnnotationSelect) {
			const target = e.target as HTMLElement;
			if (!target.closest('.pdf-annotation')) {
				onAnnotationSelect(null);
			}
		}
	}

	const THUMB_SCALE = 0.15;

	async function renderThumbnails() {
		if (!pdfDoc || !thumbnailContainerEl) return;
		thumbnailContainerEl.innerHTML = '';

		for (let pageNum = 1; pageNum <= totalPages; pageNum++) {
			const page = await pdfDoc.getPage(pageNum);
			const viewport = page.getViewport({ scale: THUMB_SCALE });

			const wrapper = document.createElement('div');
			wrapper.className = 'thumb-item';
			if (pageNum === currentPage) wrapper.classList.add('thumb-active');
			wrapper.dataset.pageNum = String(pageNum);
			wrapper.addEventListener('click', () => goToPage(pageNum));

			const canvas = document.createElement('canvas');
			canvas.width = viewport.width;
			canvas.height = viewport.height;
			canvas.style.width = `${viewport.width}px`;
			canvas.style.height = `${viewport.height}px`;

			const context = canvas.getContext('2d')!;
			await page.render({ canvasContext: context, viewport }).promise;

			wrapper.appendChild(canvas);

			const label = document.createElement('span');
			label.className = 'thumb-label';
			label.textContent = String(pageNum);
			wrapper.appendChild(label);

			thumbnailContainerEl.appendChild(wrapper);
		}
	}

	// Update active thumbnail when current page changes
	$effect(() => {
		const page = currentPage;
		if (!thumbnailContainerEl) return;
		const items = thumbnailContainerEl.querySelectorAll('.thumb-item');
		for (const item of items) {
			const el = item as HTMLElement;
			el.classList.toggle('thumb-active', Number(el.dataset.pageNum) === page);
		}
	});

	function toggleThumbnails() {
		showThumbnails = !showThumbnails;
		if (showThumbnails && thumbnailContainerEl && thumbnailContainerEl.children.length === 0) {
			renderThumbnails();
		}
	}

	export function syncScrollTo(scrollRatio: number) {
		if (!pagesContainerEl) return;
		isProgrammaticScroll = true;
		const maxScroll = pagesContainerEl.scrollHeight - pagesContainerEl.clientHeight;
		pagesContainerEl.scrollTop = scrollRatio * maxScroll;
		// Reset guard after scroll event fires
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
		// Force reflow to restart animation
		void el.offsetWidth;
		el.classList.add('highlight-flash');
	}

	export function scrollToPagePosition(page: number, y?: number) {
		if (!pagesContainerEl) return;

		const wrapper = pagesContainerEl.querySelector(
			`[data-page-num="${page}"]`
		) as HTMLElement | null;
		if (!wrapper) return;

		if (y !== undefined) {
			// Scroll to specific Y position within the page
			const yPixel = y * scale;
			const targetTop = wrapper.offsetTop + yPixel - pagesContainerEl.clientHeight / 3;
			pagesContainerEl.scrollTo({ top: Math.max(0, targetTop), behavior: 'smooth' });
		} else {
			// Use scrollTo on the container instead of scrollIntoView to prevent
			// the outer layout from scrolling (which hides the toolbar)
			pagesContainerEl.scrollTo({ top: wrapper.offsetTop, behavior: 'smooth' });
		}

		currentPage = page;
		pageInputValue = String(page);
	}
</script>

<div class="pdf-panel" bind:this={containerEl}>
	<div class="pdf-toolbar">
		<span class="pdf-label">{label}</span>

		{#if pdfDoc}
			<button class="nav-btn" onclick={toggleThumbnails} title="Toggle thumbnails" class:thumb-toggle-active={showThumbnails}>
				&#9776;
			</button>
			<div class="pdf-nav">
				<button
					class="nav-btn"
					onclick={() => goToPage(currentPage - 1)}
					disabled={currentPage <= 1}
					title="Previous page"
				>
					&#9650;
				</button>
				<input
					class="page-input"
					type="text"
					bind:value={pageInputValue}
					onkeydown={handlePageInput}
					title="Go to page"
				/>
				<span class="page-total">/ {totalPages}</span>
				<button
					class="nav-btn"
					onclick={() => goToPage(currentPage + 1)}
					disabled={currentPage >= totalPages}
					title="Next page"
				>
					&#9660;
				</button>
			</div>

			<div class="zoom-controls">
				<button class="nav-btn" onclick={zoomOut} title="Zoom out">&#8722;</button>
				<button class="nav-btn zoom-fit" onclick={zoomFit} title="Fit width">Fit</button>
				<button class="nav-btn" onclick={zoomIn} title="Zoom in">&#43;</button>
				<span class="zoom-level">{Math.round(scale * 100)}%</span>
			</div>
		{/if}
	</div>

	<div class="pdf-body">
		{#if showThumbnails}
			<div class="thumb-sidebar" bind:this={thumbnailContainerEl}></div>
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

	.pdf-body {
		display: flex;
		flex: 1;
		overflow: hidden;
	}

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

	:global(.thumb-item) {
		cursor: pointer;
		border: 2px solid transparent;
		border-radius: 3px;
		padding: 2px;
		text-align: center;
		transition: border-color 0.15s;
	}

	:global(.thumb-item:hover) {
		border-color: rgba(0, 0, 0, 0.15);
	}

	:global(.thumb-item.thumb-active) {
		border-color: var(--accent-blue, #007aff);
	}

	:global(.thumb-label) {
		display: block;
		font-size: 9px;
		color: var(--text-secondary, #86868b);
		margin-top: 1px;
	}

	.thumb-toggle-active {
		color: var(--accent-blue, #007aff) !important;
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

	/* Page wrapper styles (applied to dynamically created elements) */
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
