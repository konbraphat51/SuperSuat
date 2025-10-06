export interface OcrParagraph {
	polygon: [number, number];
	role: string;
	content: string;
}

export interface OcrFigure {
	id: string;
	polygon: [number, number];
	caption: {
		content: string;
		polygon: [number, number];
	} | null;
}

export interface OcrPage {
	width: number;
	height: number;
	number: number;
	paragraphs: OcrParagraph[];
	figures: OcrFigure[];
}

export interface OcrData {
	pages: OcrPage[];
}
