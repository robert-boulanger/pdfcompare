<script lang="ts">
	import { open, save } from '@tauri-apps/plugin-dialog';
	import { invoke } from '@tauri-apps/api/core';
	import PdfPanel from '$lib/components/PdfPanel.svelte';
	import DiffSidebar from '$lib/components/DiffSidebar.svelte';
	import TextDiffTab from '$lib/components/TextDiffTab.svelte';
	import TypoDiffTab from '$lib/components/TypoDiffTab.svelte';
	import AnnotationToolbar from '$lib/components/AnnotationToolbar.svelte';
	import { getDiffStore } from '$lib/stores/diffStore.svelte';
	import { getValidationStore } from '$lib/stores/validationStore.svelte';
	import { getAnnotationStore } from '$lib/stores/annotationStore.svelte';
	import type { Annotation } from '$lib/types/annotations';
	import '../styles/macos-theme.css';

	let leftPdfPath: string | null = $state(null);
	let rightPdfPath: string | null = $state(null);
	let isDraggingLeft = $state(false);
	let isDraggingRight = $state(false);

	const diff = getDiffStore();
	const validation = getValidationStore();
	const ann = getAnnotationStore();
	const canCompare = $derived(!!leftPdfPath && !!rightPdfPath && !diff.isComparing);

	// Sidebar state
	let sidebarOpen = $state(false);
	let sidebarTab: 'text-diff' | 'typography' = $state('text-diff');

	async function openPdf(side: 'left' | 'right') {
		// Warn about unsaved annotations
		if (ann.isDirty) {
			const discard = confirm('Unsaved annotations will be lost. Continue?');
			if (!discard) return;
		}

		const selected = await open({
			multiple: false,
			filters: [{ name: 'PDF', extensions: ['pdf'] }]
		});

		if (selected) {
			if (side === 'left') {
				leftPdfPath = selected as string;
			} else {
				rightPdfPath = selected as string;
			}
			diff.clearDiff();
			validation.clearValidation();
			ann.clearAnnotations();
			sidebarOpen = false;
		}
	}

	async function saveAnnotations() {
		if (!rightPdfPath || ann.annotations.length === 0) return;

		const outputPath = await save({
			defaultPath: rightPdfPath.replace(/\.pdf$/i, '_annotated.pdf'),
			filters: [{ name: 'PDF', extensions: ['pdf'] }]
		});

		if (!outputPath) return;

		try {
			await invoke('save_annotations', {
				pdfPath: rightPdfPath,
				outputPath,
				annotations: ann.toExportJson()
			});
			ann.markSaved();
			alert('Annotations saved successfully.');
		} catch (e) {
			alert(`Save failed: ${e instanceof Error ? e.message : String(e)}`);
		}
	}

	function handleAnnotationCreate(a: Omit<Annotation, 'id'>) {
		ann.addAnnotation(a);
	}

	function handleKeydown(e: KeyboardEvent) {
		// Cmd/Ctrl+S → Save annotations
		if ((e.metaKey || e.ctrlKey) && e.key === 's') {
			e.preventDefault();
			if (ann.isDirty) saveAnnotations();
		}
		// Delete/Backspace → Remove selected annotation
		if ((e.key === 'Delete' || e.key === 'Backspace') && ann.selectedId) {
			// Don't delete if user is typing in an input
			if ((e.target as HTMLElement).tagName === 'INPUT' || (e.target as HTMLElement).tagName === 'TEXTAREA') return;
			ann.removeAnnotation(ann.selectedId);
		}
		// Escape → Deselect tool
		if (e.key === 'Escape') {
			ann.setTool('none');
			ann.selectAnnotation(null);
		}
		// H → Highlight tool
		if (e.key === 'h' && !(e.target as HTMLElement).closest('input, textarea')) {
			ann.setTool(ann.activeTool === 'highlight' ? 'none' : 'highlight');
		}
		// N → Note tool
		if (e.key === 'n' && !(e.target as HTMLElement).closest('input, textarea')) {
			ann.setTool(ann.activeTool === 'note' ? 'none' : 'note');
		}
	}

	let leftPanel: PdfPanel | undefined = $state();
	let rightPanel: PdfPanel | undefined = $state();
	let scrollSyncEnabled = $state(true);

	function handleLeftScroll(info: { page: number; scrollRatio: number }) {
		if (scrollSyncEnabled && rightPanel) {
			rightPanel.syncScrollTo(info.scrollRatio);
		}
	}

	function handleRightScroll(info: { page: number; scrollRatio: number }) {
		if (scrollSyncEnabled && leftPanel) {
			leftPanel.syncScrollTo(info.scrollRatio);
		}
	}

	async function comparePdfs() {
		if (!leftPdfPath || !rightPdfPath) return;
		// Run diff and validation in parallel
		await Promise.all([
			diff.runDiff(leftPdfPath, rightPdfPath),
			validation.runValidation(leftPdfPath, rightPdfPath)
		]);
		// Auto-open sidebar when results arrive
		sidebarOpen = true;
	}

	function navigateToDifference(index: number) {
		diff.selectDifference(index);
		const d = diff.diffResult?.differences[index];
		if (!d) return;

		if (d.left_page && leftPanel) {
			leftPanel.scrollToPagePosition(d.left_page, d.left_bbox?.[1]);
			leftPanel.flashHighlight(index);
		}
		if (d.right_page && rightPanel) {
			rightPanel.scrollToPagePosition(d.right_page, d.right_bbox?.[1]);
			rightPanel.flashHighlight(index);
		}
	}

	function navigateToIssue(issue: import('$lib/types/validation').ValidationIssue, side: 'left' | 'right') {
		const panel = side === 'left' ? leftPanel : rightPanel;
		if (panel && issue.page) {
			panel.scrollToPagePosition(issue.page, issue.bbox?.[1]);
		}
	}

	function handleDragOver(e: DragEvent, side: 'left' | 'right') {
		e.preventDefault();
		if (side === 'left') isDraggingLeft = true;
		else isDraggingRight = true;
	}

	function handleDragLeave(side: 'left' | 'right') {
		if (side === 'left') isDraggingLeft = false;
		else isDraggingRight = false;
	}

	function handleDrop(e: DragEvent, side: 'left' | 'right') {
		e.preventDefault();
		if (side === 'left') isDraggingLeft = false;
		else isDraggingRight = false;

		// Tauri's native file drop will be used in later phases
		// for now, the file dialog is the primary way to open PDFs
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="app-layout" onkeydown={handleKeydown}>
	<header class="app-toolbar">
		<div class="toolbar-section">
			<button class="toolbar-btn" onclick={() => openPdf('left')} title="Open left PDF">
				<span class="btn-icon">&#128194;</span>
				Open Left
			</button>
			<button class="toolbar-btn" onclick={() => openPdf('right')} title="Open right PDF">
				<span class="btn-icon">&#128194;</span>
				Open Right
			</button>
		</div>

		<div class="toolbar-title">PDF Compare</div>

		<div class="toolbar-section toolbar-right">
			<button
				class="toolbar-btn sync-btn"
				class:sync-active={scrollSyncEnabled}
				onclick={() => scrollSyncEnabled = !scrollSyncEnabled}
				title={scrollSyncEnabled ? 'Scroll sync on' : 'Scroll sync off'}
			>
				Sync {scrollSyncEnabled ? 'On' : 'Off'}
			</button>
			{#if diff.isComparing || validation.isValidating}
				<span class="toolbar-status">
					{diff.isComparing ? 'Comparing...' : 'Validating...'}
				</span>
			{:else if diff.diffResult}
				<button
					class="toolbar-btn summary-btn"
					onclick={() => sidebarOpen = !sidebarOpen}
					title={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
				>
					<span class="summary-diff">
						{diff.diffResult.summary.added}+ {diff.diffResult.summary.removed}− {diff.diffResult.summary.changed}~
					</span>
					{#if validation.resolvedIssues.length > 0 || validation.newIssues.length > 0}
						<span class="summary-sep">|</span>
						<span class="summary-validation">
							{#if validation.resolvedIssues.length > 0}
								<span class="summary-resolved">{validation.resolvedIssues.length} fixed</span>
							{/if}
							{#if validation.newIssues.length > 0}
								<span class="summary-new">{validation.newIssues.length} new</span>
							{/if}
						</span>
					{/if}
					<span class="sidebar-indicator">{sidebarOpen ? '▶' : '◀'}</span>
				</button>
			{:else if diff.compareError}
				<span class="toolbar-status diff-error" title={diff.compareError}>
					{diff.compareError.length > 60 ? diff.compareError.slice(0, 60) + '...' : diff.compareError}
				</span>
			{/if}
			<button
				class="toolbar-btn compare-btn"
				onclick={comparePdfs}
				disabled={!canCompare}
				title="Compare both PDFs"
			>
				Compare
			</button>
		</div>
	</header>

	{#if rightPdfPath}
		<AnnotationToolbar
			activeTool={ann.activeTool}
			activeColorIndex={ann.activeColorIndex}
			isDirty={ann.isDirty}
			hasSelection={!!ann.selectedAnnotation}
			onToolChange={(tool) => ann.setTool(tool)}
			onColorChange={(i) => ann.setColorIndex(i)}
			onSave={saveAnnotations}
			onDelete={() => { if (ann.selectedId) ann.removeAnnotation(ann.selectedId); }}
		/>
	{/if}

	<main class="split-view">
		<div
			class="panel-container"
			class:drag-over={isDraggingLeft}
			role="region"
			aria-label="Left PDF"
			ondragover={(e) => handleDragOver(e, 'left')}
			ondragleave={() => handleDragLeave('left')}
			ondrop={(e) => handleDrop(e, 'left')}
		>
			<PdfPanel bind:this={leftPanel} pdfPath={leftPdfPath} label="Original" side="left" highlights={sidebarTab === 'text-diff' ? diff.leftHighlights : []} activeHighlightIndex={diff.selectedDifferenceIndex} validationHighlights={sidebarTab === 'typography' ? validation.leftValidationHighlights : []} onHighlightClick={navigateToDifference} onScrollChange={handleLeftScroll} />
		</div>

		<div class="splitter"></div>

		<div
			class="panel-container"
			class:drag-over={isDraggingRight}
			role="region"
			aria-label="Right PDF"
			ondragover={(e) => handleDragOver(e, 'right')}
			ondragleave={() => handleDragLeave('right')}
			ondrop={(e) => handleDrop(e, 'right')}
		>
			<PdfPanel bind:this={rightPanel} pdfPath={rightPdfPath} label="Modified" side="right" highlights={sidebarTab === 'text-diff' ? diff.rightHighlights : []} activeHighlightIndex={diff.selectedDifferenceIndex} validationHighlights={sidebarTab === 'typography' ? validation.rightValidationHighlights : []} onHighlightClick={navigateToDifference} onScrollChange={handleRightScroll} annotations={ann.annotations} selectedAnnotationId={ann.selectedId} annotationTool={ann.activeTool} onAnnotationCreate={handleAnnotationCreate} onAnnotationSelect={(id) => ann.selectAnnotation(id)} onAnnotationUpdate={(id, updates) => ann.updateAnnotation(id, updates)} onAnnotationDelete={(id) => ann.removeAnnotation(id)} annotationColor={ann.activeColor.rgb} />
		</div>

		<DiffSidebar
			isOpen={sidebarOpen}
			activeTab={sidebarTab}
			onTabChange={(tab) => sidebarTab = tab}
			onToggle={() => sidebarOpen = !sidebarOpen}
		>
			{#snippet textDiffContent()}
				<TextDiffTab
					diffResult={diff.diffResult}
					selectedIndex={diff.selectedDifferenceIndex}
					onSelect={navigateToDifference}
				/>
			{/snippet}
			{#snippet typographyContent()}
				<TypoDiffTab
					resolvedIssues={validation.resolvedIssues}
					newIssues={validation.newIssues}
					commonIssues={validation.commonIssues}
					isValidating={validation.isValidating}
					validationError={validation.validationError}
					hasReports={!!validation.leftReport && !!validation.rightReport}
					onIssueClick={navigateToIssue}
				/>
			{/snippet}
		</DiffSidebar>
	</main>
</div>

<style>
	.app-layout {
		display: flex;
		flex-direction: column;
		height: 100vh;
		background: var(--bg-secondary);
	}

	.app-toolbar {
		display: flex;
		align-items: center;
		height: 38px;
		padding: 0 var(--spacing-md);
		background: var(--bg-toolbar);
		backdrop-filter: blur(20px);
		-webkit-app-region: drag;
		border-bottom: 0.5px solid var(--border-color);
		flex-shrink: 0;
	}

	.toolbar-section {
		display: flex;
		gap: var(--spacing-xs);
		-webkit-app-region: no-drag;
	}

	.toolbar-right {
		margin-left: auto;
	}

	.toolbar-title {
		flex: 1;
		text-align: center;
		font-size: var(--font-size-body);
		font-weight: 600;
		color: var(--text-primary);
		pointer-events: none;
	}

	.toolbar-btn {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 3px 10px;
		border: 1px solid var(--border-color);
		border-radius: var(--radius-sm);
		background: var(--bg-primary);
		font-size: var(--font-size-caption);
		color: var(--text-primary);
		cursor: pointer;
		font-family: var(--font-family);
		transition: background 0.15s;
	}

	.toolbar-btn:hover {
		background: rgba(0, 0, 0, 0.04);
	}

	.toolbar-btn:active {
		background: rgba(0, 0, 0, 0.08);
	}

	.btn-icon {
		font-size: 12px;
	}

	.split-view {
		display: flex;
		flex: 1;
		gap: 0;
		padding: var(--spacing-sm);
		overflow: hidden;
	}

	.panel-container {
		flex: 1;
		min-width: 0;
		border-radius: var(--radius-md);
		overflow: hidden;
		border: 2px solid transparent;
		transition: border-color 0.15s;
	}

	.panel-container.drag-over {
		border-color: var(--accent-blue);
	}

	.splitter {
		width: var(--spacing-sm);
		cursor: col-resize;
		flex-shrink: 0;
	}

	.compare-btn {
		font-weight: 600;
		background: var(--accent-blue, #007aff);
		color: white;
		border-color: var(--accent-blue, #007aff);
	}

	.compare-btn:hover:not(:disabled) {
		background: color-mix(in srgb, var(--accent-blue, #007aff) 85%, black);
	}

	.compare-btn:disabled {
		opacity: 0.4;
		cursor: default;
	}

	.toolbar-status {
		font-size: var(--font-size-caption, 11px);
		color: var(--text-secondary, #86868b);
	}

	.diff-error {
		color: var(--accent-red, #ff3b30);
	}

	.sync-btn {
		font-weight: 500;
		min-width: 64px;
	}

	.summary-btn {
		font-size: var(--font-size-caption);
		font-weight: 500;
		gap: 6px;
	}

	.summary-diff {
		color: var(--text-primary);
	}

	.summary-sep {
		color: var(--border-color);
		margin: 0 2px;
	}

	.summary-validation {
		display: flex;
		gap: 6px;
	}

	.summary-resolved {
		color: var(--accent-green);
	}

	.summary-new {
		color: var(--accent-orange);
	}

	.sidebar-indicator {
		font-size: 9px;
		color: var(--text-secondary);
	}

	.sync-active {
		background: rgba(0, 122, 255, 0.1);
		border-color: var(--accent-blue, #007aff);
		color: var(--accent-blue, #007aff);
	}
</style>
