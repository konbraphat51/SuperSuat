import React, { useState, useEffect } from "react";
import { PdfParagraphOverlayer } from "../../PdfParagraphOverlayer";
import type { OcrData } from "../../../scripts/OcrData";

export const PageHome = () => {
	const [ocrData, setOcrData] = useState<OcrData | null>(null);
	const [pdfFile, setPdfFile] = useState<string | null>(null);
	const [overlayColor, setOverlayColor] = useState("#ffffff");
	const [textColor, setTextColor] = useState("#000000");

	// Load OCR data from public folder
	useEffect(() => {
		fetch('/ocr.json')
			.then(response => response.json())
			.then((data: OcrData) => setOcrData(data))
			.catch(error => console.error('Error loading OCR data:', error));
	}, []);

	const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
		const file = event.target.files?.[0];
		if (file && file.type === 'application/pdf') {
			const reader = new FileReader();
			reader.onload = (e) => {
				if (e.target?.result) {
					setPdfFile(e.target.result as string);
				}
			};
			reader.readAsDataURL(file);
		}
	};

	return (
		<div style={{ padding: '20px' }}>
			<h1>PDF Paragraph Overlayer Demo</h1>
			
			<div style={{ marginBottom: '20px' }}>
				<div style={{ marginBottom: '10px' }}>
					<label htmlFor="pdf-upload">Upload PDF File: </label>
					<input
						id="pdf-upload"
						type="file"
						accept=".pdf"
						onChange={handleFileChange}
					/>
				</div>
				
				<div style={{ marginBottom: '10px' }}>
					<label htmlFor="overlay-color">Overlay Background Color: </label>
					<input
						id="overlay-color"
						type="color"
						value={overlayColor}
						onChange={(e) => setOverlayColor(e.target.value)}
					/>
				</div>
				
				<div style={{ marginBottom: '10px' }}>
					<label htmlFor="text-color">Text Color: </label>
					<input
						id="text-color"
						type="color"
						value={textColor}
						onChange={(e) => setTextColor(e.target.value)}
					/>
				</div>
			</div>

			{pdfFile && ocrData ? (
				<div style={{ border: '1px solid #ccc', padding: '20px' }}>
					<h3>Page 1 with Overlays:</h3>
					<PdfParagraphOverlayer
						pdfRendererProps={{
							src: pdfFile,
							pageNumber: 1,
							scale: 1.5,
							maxWidth: 800
						}}
						ocrData={ocrData}
						overlayBackgroundColor={overlayColor}
						overlayTextColor={textColor}
					/>
					
					<h3 style={{ marginTop: '40px' }}>Page 2 with Overlays:</h3>
					<PdfParagraphOverlayer
						pdfRendererProps={{
							src: pdfFile,
							pageNumber: 2,
							scale: 1.5,
							maxWidth: 800
						}}
						ocrData={ocrData}
						overlayBackgroundColor={overlayColor}
						overlayTextColor={textColor}
					/>
				</div>
			) : (
				<div style={{ padding: '20px', backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
					{!pdfFile && <p>Please upload a PDF file to see the overlay demo.</p>}
					{!ocrData && <p>Loading OCR data...</p>}
				</div>
			)}
			
			<div style={{ marginTop: '40px', padding: '20px', backgroundColor: '#f9f9f9', borderRadius: '8px' }}>
				<h3>How it works:</h3>
				<ul>
					<li>Upload a PDF file that corresponds to the OCR data in <code>public/ocr.json</code></li>
					<li>The component renders the PDF page using <code>PdfPageRenderer</code></li>
					<li>OCR data provides polygon coordinates for each text paragraph</li>
					<li>Overlay rectangles are drawn with customizable background color to hide original text</li>
					<li>New text is rendered with automatic font sizing to fit within the detected regions</li>
					<li>Colors are adjustable using the color pickers above</li>
				</ul>
			</div>
		</div>
	);
};
