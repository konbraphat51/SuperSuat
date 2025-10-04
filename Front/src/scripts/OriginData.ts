export interface OriginItem {
	id: string;
	type: "paragraph" | "figure";
}

export interface OriginParagraph extends OriginItem {
	idOcr: string;
	content: string;
	highlights: {
		highlightId: string;
		area: [number, number];
	}[];
}

export interface OriginFigure extends OriginItem {
	idOcr: string;
	caption: string | null;
	highlights: string[];
}

export interface OriginHighlights {
	id: string;
	comment: string;
	color: [number, number, number];
}

export interface OriginData {
	contents: OriginItem[];
	highlights: OriginHighlights[];
}
