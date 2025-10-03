import { XMLParser, XMLBuilder } from "fast-xml-parser";

export interface OriginData {
	id: string;
	items: { item: OriginItem[] };
}

export interface OriginItem {
	index: number;
	orderIndex: number;
	type: "paragraph" | "figure";
}

export interface OriginParagraph extends OriginItem {
	content: string;
}

export interface OriginFigure extends OriginItem {
	imageId: string;
	caption: string;
}

export const origin2xml = (data: OriginData): string => {
	const builder = new XMLBuilder({
		ignoreAttributes: false,
	});
	const xmlObject = {
		"?xml": {
			"@_version": "1.0",
			"@_encoding": "UTF-8",
		},
		data: data,
	};
	return builder.build(xmlObject);
};

export const xml2origin = (xml: string): OriginData => {
	const parser = new XMLParser({
		ignoreAttributes: false,
	});
	const jsonObj = parser.parse(xml);
	return jsonObj.data;
};
