import * as pdfjsLib from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

let initialized = false;

export function initPdfJs(): void {
	if (initialized) return;

	pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;

	initialized = true;
}

export { pdfjsLib };
