export interface Paper {
  id: string;
  title: string;
  authors: string[];
  description: string;
  tags: string[];
  originalUrl?: string;
  createdAt: string;
  updatedAt?: string;
}

export interface PaperDetail extends Paper {
  content: TextContent;
  figures: Figure[];
  tables: Table[];
  equations: Equation[];
}

export interface TextContent {
  sections: Section[];
}

export interface Section {
  id: string;
  title: string;
  level: number;
  order: number;
  paragraphs: Paragraph[];
}

export interface Paragraph {
  id: string;
  content: string;
  order: number;
  type: 'Text' | 'Equation' | 'FigureReference' | 'TableReference';
}

export interface Figure {
  id: string;
  caption: string;
  imageUrl: string;
  order: number;
}

export interface Table {
  id: string;
  caption: string;
  content: string;
  order: number;
}

export interface Equation {
  id: string;
  latexContent: string;
  order: number;
}

export interface Translation {
  id: string;
  paperId: string;
  language: string;
  sections: TranslatedSection[];
}

export interface TranslatedSection {
  sectionId: string;
  translatedTitle: string;
  paragraphs: TranslatedParagraph[];
}

export interface TranslatedParagraph {
  paragraphId: string;
  translatedContent: string;
}

export interface Summary {
  id: string;
  paperId: string;
  language: string;
  wholeSummary: string;
  chapterSummaries?: ChapterSummary[];
}

export interface ChapterSummary {
  sectionId: string;
  summary: string;
}

export interface Highlight {
  id: string;
  paperId: string;
  paragraphId: string;
  startOffset: number;
  endOffset: number;
  color: string;
  note?: string;
  createdAt: string;
}

export interface HighlightColorPreset {
  id: string;
  name: string;
  color: string;
  isDefault: boolean;
}

export interface PaperFilter {
  tags?: string[];
  authors?: string[];
  fromDate?: string;
  toDate?: string;
  searchText?: string;
  pageSize?: number;
  nextToken?: string;
}

export interface ViewStyle {
  fontSize: number;
  lineHeight: number;
  fontFamily: string;
  colorSet: 'light' | 'dark' | 'sepia';
  marginSize: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}
