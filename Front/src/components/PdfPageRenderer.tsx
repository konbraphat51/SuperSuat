import React, { useEffect, useRef, useState } from "react";
import { getDocument, GlobalWorkerOptions } from "pdfjs-dist";
import type { PDFDocumentProxy, PDFPageProxy } from "pdfjs-dist";
// pdf.js v5+ ships ESM worker; we import the URL so bundler (Vite) can create a worker blob
// Type declaration added in src/types/pdfjs-worker.d.ts
// eslint-disable-next-line import/no-unresolved
import pdfjsWorker from "pdfjs-dist/build/pdf.worker.mjs";
// Import base font (variable or aggregated weights). Some packages expose an index.css covering common weights.
import "@fontsource/noto-sans-jp";

GlobalWorkerOptions.workerSrc = pdfjsWorker as any; // Vite will transform this into a URL

export interface PdfPageRendererProps {
	/** URL or binary data for the PDF */
	src: string | ArrayBuffer | Uint8Array;
	/** 1-based page number to render */
	pageNumber: number;
	/** Scale (zoom) factor; 1 = 100% */
	scale?: number;
	/** Optional max width; the page will be scaled down to fit while preserving given scale upper bound */
	maxWidth?: number;
	/** (w,h) callback after render completes */
	onRender?: (info: {
		width: number;
		height: number;
		page: PDFPageProxy;
	}) => void;
	/** Show a simple loading indicator while fetching */
	loadingFallback?: React.ReactNode;
	/** Show if page not found */
	notFoundFallback?: React.ReactNode;
	/** Class name for wrapper */
	className?: string;
	/** Style for wrapper */
	style?: React.CSSProperties;
	/** Optional custom render text layer (future extension) */
	withTextLayer?: boolean; // reserved; currently false
}

/**
 * Renders a single PDF page to a <canvas> without exposing any viewer chrome.
 * Uses Noto Sans JP as a fallback font if the PDF lacks embedded fonts.
 */
export const PdfPageRenderer: React.FC<PdfPageRendererProps> = ({
	src,
	pageNumber,
	scale = 1,
	maxWidth,
	onRender,
	loadingFallback = "Loading page…",
	notFoundFallback = "Page not found",
	className,
	style,
}) => {
	const canvasRef = useRef<HTMLCanvasElement | null>(null);
	const [loading, setLoading] = useState(true);
	const [pageMissing, setPageMissing] = useState(false);
	const [docRef, setDocRef] = useState<PDFDocumentProxy | null>(null);
	const renderIdRef = useRef(0); // guard outdated renders

	// Load document when src changes
	useEffect(() => {
		let cancelled = false;
		setLoading(true);
		setPageMissing(false);
		setDocRef(null);

		const data =
			src instanceof Uint8Array || src instanceof ArrayBuffer
				? { data: src }
				: { url: src };
		const loadingTask = getDocument({ ...data, useSystemFonts: true }); // useSystemFonts lets pdf.js fallback to installed fonts
		loadingTask.promise
			.then((pdf) => {
				if (cancelled) return;
				setDocRef(pdf);
			})
			.catch((err) => {
				if (!cancelled) {
					console.error("Failed to load PDF", err);
					setPageMissing(true);
					setLoading(false);
				}
			});

		return () => {
			cancelled = true;
			loadingTask.destroy();
		};
	}, [src]);

	// Render page when document or pageNumber/scale changes
	useEffect(() => {
		if (!docRef) return;
		let cancelled = false;
		const currentRenderId = ++renderIdRef.current;
		setLoading(true);
		setPageMissing(false);

		docRef
			.getPage(pageNumber)
			.then(async (page) => {
				if (cancelled || currentRenderId !== renderIdRef.current) return;
				const viewport = page.getViewport({ scale });

				// Adjust scale if maxWidth given
				let finalViewport = viewport;
				if (maxWidth && viewport.width > maxWidth) {
					const adjustedScale = (maxWidth / viewport.width) * scale; // proportionally reduce
					finalViewport = page.getViewport({ scale: adjustedScale });
				}

				const canvas = canvasRef.current;
				if (!canvas) return;
				const ctx = canvas.getContext("2d", { alpha: false });
				if (!ctx) return;

				canvas.width = Math.ceil(finalViewport.width);
				canvas.height = Math.ceil(finalViewport.height);
				canvas.style.width = `${finalViewport.width}px`;
				canvas.style.height = `${finalViewport.height}px`;

				// Render page
				const renderTask = page.render({
					canvasContext: ctx,
					canvas: canvas,
					viewport: finalViewport,
					intent: "display" as any,
				});
				await renderTask.promise;

				if (cancelled || currentRenderId !== renderIdRef.current) return;
				setLoading(false);
				onRender?.({ width: finalViewport.width, height: finalViewport.height, page });
			})
			.catch((err) => {
				if (!cancelled) {
					console.warn("Could not render page", err);
					setPageMissing(true);
					setLoading(false);
				}
			});

		return () => {
			cancelled = true;
		};
	}, [docRef, pageNumber, scale, maxWidth, onRender]);

	return (
		<div
			className={className}
			style={{
				fontFamily:
					'"Noto Sans JP", "Noto Sans JP Variable", "Noto Sans", system-ui, sans-serif',
				lineHeight: 1.4,
				position: "relative",
				...style,
			}}
		>
			{loading && (
				<div
					style={{
						position: "absolute",
						inset: 0,
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
						fontSize: 14,
						color: "#555",
					}}
				>
					{loadingFallback}
				</div>
			)}
			{pageMissing && !loading && (
				<div
					style={{
						position: "absolute",
						inset: 0,
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
						fontSize: 14,
						color: "#a00",
					}}
				>
					{notFoundFallback}
				</div>
			)}
			<canvas ref={canvasRef} aria-label={`PDF page ${pageNumber}`} />
		</div>
	);
};

export default PdfPageRenderer;
