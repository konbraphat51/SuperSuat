export interface OcrParagraph {
	polygon: [number, number, number, number, number, number, number, number];
	role: string;
	content: string;
	paragraph_index: number; // 0-indexed
}

export interface OcrPage {
	width: number;
	height: number;
	number: number;
	paragraphs: OcrParagraph[];
}

export interface OcrData {
	pages: OcrPage[];
}
