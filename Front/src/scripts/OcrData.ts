export interface OcrItem {
	index_item: number;
	type: "paragraph" | "figure";
}

export interface OcrParagraph extends OcrItem {
	polygon: [number, number, number, number, number, number, number, number];
	role: string;
	content: string;
}

export interface OcrFigure extends OcrItem {
	polygon: [number, number, number, number, number, number, number, number];
	caption: {
		content: string;
		polygon: [number, number, number, number, number, number, number, number];
	} | null;
}

export interface OcrPage {
	width: number;
	height: number;
	number: number;
	items: (OcrParagraph | OcrFigure)[];
}

export interface OcrData {
	pages: OcrPage[];
}
