export interface OcrPage {
	width: number;
	height: number;
}

export interface OcrParagraph {
	spans: {
		offset: number;
		length: number;
	}[];
	boundingRegions: {
		pageNumber: number;
		polygon: [number, number];
	};
	role: string;
	content: string;
}
