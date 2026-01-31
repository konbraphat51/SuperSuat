# Data Structure Specifications

## Overview

This document describes the data structures and database schemas for the SuperSuat paper reading assistance application.

## DynamoDB Tables

### Table Design Principles

- Single-table design where appropriate for related entities
- Use composite primary keys (PK + SK) for efficient queries
- Global Secondary Indexes (GSI) for alternative access patterns
- Use sparse indexes to optimize storage and query performance

---

## 1. Papers Table

### Table Name: `supersuat-papers`

### Purpose
Stores paper metadata and content information.

### Schema

| Attribute | Type | Description |
|-----------|------|-------------|
| PK | String | Partition key: `PAPER#{paperId}` |
| SK | String | Sort key: `METADATA` for paper metadata, `CONTENT` for text content, `FIGURE#{order}`, `TABLE#{order}`, `EQUATION#{order}` |
| paperId | String | Unique paper identifier (UUID) |
| title | String | Paper title |
| authors | List\<String\> | List of author names |
| description | String | Short description of the paper |
| tags | List\<String\> | Tags for categorization |
| originalUrl | String | URL to original paper (optional) |
| pdfUrl | String | S3 URL to stored PDF |
| createdAt | String | ISO 8601 timestamp |
| updatedAt | String | ISO 8601 timestamp |
| GSI1PK | String | `PAPERS` (for listing all papers) |
| GSI1SK | String | `{createdAt}#{paperId}` |

### Access Patterns

| Access Pattern | Key Condition | Index |
|---------------|---------------|-------|
| Get paper by ID | PK = `PAPER#{paperId}`, SK = `METADATA` | Primary |
| List all papers | GSI1PK = `PAPERS` | GSI1 |
| Get paper content | PK = `PAPER#{paperId}`, SK = `CONTENT` | Primary |
| Get all figures | PK = `PAPER#{paperId}`, SK begins_with `FIGURE#` | Primary |
| Get all tables | PK = `PAPER#{paperId}`, SK begins_with `TABLE#` | Primary |
| Get all equations | PK = `PAPER#{paperId}`, SK begins_with `EQUATION#` | Primary |

### Item Examples

#### Paper Metadata Item
```json
{
  "PK": "PAPER#550e8400-e29b-41d4-a716-446655440000",
  "SK": "METADATA",
  "paperId": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Attention Is All You Need",
  "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
  "description": "Introduces the Transformer architecture",
  "tags": ["deep learning", "nlp", "attention"],
  "originalUrl": "https://arxiv.org/abs/1706.03762",
  "pdfUrl": "s3://supersuat-papers/pdfs/550e8400.pdf",
  "createdAt": "2024-01-15T10:30:00Z",
  "updatedAt": "2024-01-15T10:30:00Z",
  "GSI1PK": "PAPERS",
  "GSI1SK": "2024-01-15T10:30:00Z#550e8400-e29b-41d4-a716-446655440000"
}
```

#### Text Content Item
```json
{
  "PK": "PAPER#550e8400-e29b-41d4-a716-446655440000",
  "SK": "CONTENT",
  "paperId": "550e8400-e29b-41d4-a716-446655440000",
  "sections": [
    {
      "id": "sec-1",
      "title": "Introduction",
      "level": 1,
      "order": 1,
      "paragraphs": [
        {
          "id": "para-1-1",
          "content": "Recurrent neural networks...",
          "order": 1,
          "type": "TEXT"
        },
        {
          "id": "para-1-2",
          "content": "\\frac{a}{b}",
          "order": 2,
          "type": "EQUATION"
        }
      ]
    }
  ]
}
```

#### Figure Item
```json
{
  "PK": "PAPER#550e8400-e29b-41d4-a716-446655440000",
  "SK": "FIGURE#001",
  "figureId": "fig-001",
  "paperId": "550e8400-e29b-41d4-a716-446655440000",
  "caption": "The Transformer model architecture",
  "imageUrl": "s3://supersuat-papers/figures/550e8400/fig-001.png",
  "order": 1
}
```

#### Table Item
```json
{
  "PK": "PAPER#550e8400-e29b-41d4-a716-446655440000",
  "SK": "TABLE#001",
  "tableId": "tbl-001",
  "paperId": "550e8400-e29b-41d4-a716-446655440000",
  "caption": "Performance comparison",
  "content": "| Model | BLEU | Parameters |\n|-------|------|------------|\n| Transformer | 28.4 | 65M |",
  "order": 1
}
```

#### Equation Item
```json
{
  "PK": "PAPER#550e8400-e29b-41d4-a716-446655440000",
  "SK": "EQUATION#001",
  "equationId": "eq-001",
  "paperId": "550e8400-e29b-41d4-a716-446655440000",
  "latexContent": "\\text{Attention}(Q, K, V) = \\text{softmax}\\left(\\frac{QK^T}{\\sqrt{d_k}}\\right)V",
  "order": 1
}
```

---

## 2. Translations Table

### Table Name: `supersuat-translations`

### Purpose
Stores translated content for papers in various languages.

### Schema

| Attribute | Type | Description |
|-----------|------|-------------|
| PK | String | Partition key: `PAPER#{paperId}` |
| SK | String | Sort key: `LANG#{language}` |
| translationId | String | Unique translation identifier (UUID) |
| paperId | String | Reference to paper |
| language | String | Language code (e.g., "ja", "zh", "ko") |
| sections | List\<Object\> | Translated sections |
| createdAt | String | ISO 8601 timestamp |

### Access Patterns

| Access Pattern | Key Condition | Index |
|---------------|---------------|-------|
| Get translation | PK = `PAPER#{paperId}`, SK = `LANG#{language}` | Primary |
| List available languages | PK = `PAPER#{paperId}` | Primary |

### Item Example

```json
{
  "PK": "PAPER#550e8400-e29b-41d4-a716-446655440000",
  "SK": "LANG#ja",
  "translationId": "trans-001",
  "paperId": "550e8400-e29b-41d4-a716-446655440000",
  "language": "ja",
  "sections": [
    {
      "sectionId": "sec-1",
      "translatedTitle": "はじめに",
      "paragraphs": [
        {
          "paragraphId": "para-1-1",
          "translatedContent": "リカレントニューラルネットワークは..."
        }
      ]
    }
  ],
  "createdAt": "2024-01-16T08:00:00Z"
}
```

---

## 3. Summaries Table

### Table Name: `supersuat-summaries`

### Purpose
Stores paper summaries in various languages.

### Schema

| Attribute | Type | Description |
|-----------|------|-------------|
| PK | String | Partition key: `PAPER#{paperId}` |
| SK | String | Sort key: `SUMMARY#{language}` |
| summaryId | String | Unique summary identifier (UUID) |
| paperId | String | Reference to paper |
| language | String | Language code |
| wholeSummary | String | Summary of entire paper |
| chapterSummaries | List\<Object\> | Per-chapter summaries (optional) |
| createdAt | String | ISO 8601 timestamp |

### Access Patterns

| Access Pattern | Key Condition | Index |
|---------------|---------------|-------|
| Get summary | PK = `PAPER#{paperId}`, SK = `SUMMARY#{language}` | Primary |

### Item Example

```json
{
  "PK": "PAPER#550e8400-e29b-41d4-a716-446655440000",
  "SK": "SUMMARY#ja",
  "summaryId": "sum-001",
  "paperId": "550e8400-e29b-41d4-a716-446655440000",
  "language": "ja",
  "wholeSummary": "この論文では、Transformerと呼ばれる新しいアーキテクチャを提案しています...",
  "chapterSummaries": [
    {
      "sectionId": "sec-1",
      "summary": "導入部では、RNNの限界とアテンション機構の重要性について述べています..."
    }
  ],
  "createdAt": "2024-01-16T09:00:00Z"
}
```

---

## 4. Highlights Table

### Table Name: `supersuat-highlights`

### Purpose
Stores user highlights with notes.

### Schema

| Attribute | Type | Description |
|-----------|------|-------------|
| PK | String | Partition key: `USER#{userId}#PAPER#{paperId}` |
| SK | String | Sort key: `HIGHLIGHT#{highlightId}` |
| highlightId | String | Unique highlight identifier (UUID) |
| paperId | String | Reference to paper |
| userId | String | Reference to user |
| paragraphId | String | Reference to paragraph |
| startOffset | Number | Start character offset in paragraph |
| endOffset | Number | End character offset in paragraph |
| color | String | Highlight color (hex) |
| note | String | User note (optional) |
| createdAt | String | ISO 8601 timestamp |
| GSI1PK | String | `PAPER#{paperId}` (for fetching all highlights of a paper) |
| GSI1SK | String | `USER#{userId}#HIGHLIGHT#{highlightId}` |

### Access Patterns

| Access Pattern | Key Condition | Index |
|---------------|---------------|-------|
| Get highlights by user and paper | PK = `USER#{userId}#PAPER#{paperId}` | Primary |
| Get single highlight | PK = `USER#{userId}#PAPER#{paperId}`, SK = `HIGHLIGHT#{highlightId}` | Primary |

### Item Example

```json
{
  "PK": "USER#user-123#PAPER#550e8400-e29b-41d4-a716-446655440000",
  "SK": "HIGHLIGHT#hl-001",
  "highlightId": "hl-001",
  "paperId": "550e8400-e29b-41d4-a716-446655440000",
  "userId": "user-123",
  "paragraphId": "para-1-1",
  "startOffset": 0,
  "endOffset": 50,
  "color": "#FFEB3B",
  "note": "Important concept to understand",
  "createdAt": "2024-01-17T14:30:00Z"
}
```

---

## 5. Highlight Presets Table

### Table Name: `supersuat-highlight-presets`

### Purpose
Stores user's highlight color presets.

### Schema

| Attribute | Type | Description |
|-----------|------|-------------|
| PK | String | Partition key: `USER#{userId}` |
| SK | String | Sort key: `PRESET#{presetId}` |
| presetId | String | Unique preset identifier (UUID) |
| userId | String | Reference to user |
| name | String | Preset name |
| color | String | Color hex code |
| isDefault | Boolean | Whether this is the default preset |
| createdAt | String | ISO 8601 timestamp |

### Access Patterns

| Access Pattern | Key Condition | Index |
|---------------|---------------|-------|
| Get all presets for user | PK = `USER#{userId}` | Primary |
| Get single preset | PK = `USER#{userId}`, SK = `PRESET#{presetId}` | Primary |

### Item Example

```json
{
  "PK": "USER#user-123",
  "SK": "PRESET#preset-001",
  "presetId": "preset-001",
  "userId": "user-123",
  "name": "Important",
  "color": "#FFEB3B",
  "isDefault": true,
  "createdAt": "2024-01-10T09:00:00Z"
}
```

---

## API Data Transfer Objects (DTOs)

### Request DTOs

#### UploadPaperRequest
```typescript
interface UploadPaperRequest {
  file: File;  // PDF file
}
```

#### UpdatePaperMetaRequest
```typescript
interface UpdatePaperMetaRequest {
  title?: string;
  authors?: string[];
  description?: string;
  tags?: string[];
  originalUrl?: string;
}
```

#### CreateTranslationRequest
```typescript
interface CreateTranslationRequest {
  language: string;  // Target language code
}
```

#### CreateSummaryRequest
```typescript
interface CreateSummaryRequest {
  language: string;
  includeChapterSummaries: boolean;
}
```

#### CreateHighlightRequest
```typescript
interface CreateHighlightRequest {
  paragraphId: string;
  startOffset: number;
  endOffset: number;
  color: string;
  note?: string;
}
```

#### UpdateHighlightRequest
```typescript
interface UpdateHighlightRequest {
  color?: string;
  note?: string;
}
```

#### CreatePresetRequest
```typescript
interface CreatePresetRequest {
  name: string;
  color: string;
}
```

#### UpdatePresetRequest
```typescript
interface UpdatePresetRequest {
  name?: string;
  color?: string;
}
```

#### ChatRequest
```typescript
interface ChatRequest {
  message: string;
}
```

### Response DTOs

#### PaperListResponse
```typescript
interface PaperListResponse {
  papers: PaperSummary[];
  nextToken?: string;  // For pagination
}

interface PaperSummary {
  id: string;
  title: string;
  authors: string[];
  description: string;
  tags: string[];
  createdAt: string;
}
```

#### PaperDetailResponse
```typescript
interface PaperDetailResponse {
  id: string;
  title: string;
  authors: string[];
  description: string;
  tags: string[];
  originalUrl?: string;
  createdAt: string;
  updatedAt: string;
  content: TextContent;
  figures: Figure[];
  tables: Table[];
  equations: Equation[];
}

interface TextContent {
  sections: Section[];
}

interface Section {
  id: string;
  title: string;
  level: number;
  order: number;
  paragraphs: Paragraph[];
}

interface Paragraph {
  id: string;
  content: string;
  order: number;
  type: 'TEXT' | 'EQUATION' | 'FIGURE_REFERENCE' | 'TABLE_REFERENCE';
}

interface Figure {
  id: string;
  caption: string;
  imageUrl: string;
  order: number;
}

interface Table {
  id: string;
  caption: string;
  content: string;  // Markdown table
  order: number;
}

interface Equation {
  id: string;
  latexContent: string;
  order: number;
}
```

#### TranslationResponse
```typescript
interface TranslationResponse {
  id: string;
  paperId: string;
  language: string;
  sections: TranslatedSection[];
}

interface TranslatedSection {
  sectionId: string;
  translatedTitle: string;
  paragraphs: TranslatedParagraph[];
}

interface TranslatedParagraph {
  paragraphId: string;
  translatedContent: string;
}
```

#### AvailableLanguagesResponse
```typescript
interface AvailableLanguagesResponse {
  languages: string[];  // e.g., ["ja", "zh", "ko"]
}
```

#### SummaryResponse
```typescript
interface SummaryResponse {
  id: string;
  paperId: string;
  language: string;
  wholeSummary: string;
  chapterSummaries?: ChapterSummary[];
}

interface ChapterSummary {
  sectionId: string;
  summary: string;
}
```

#### HighlightResponse
```typescript
interface HighlightResponse {
  id: string;
  paperId: string;
  paragraphId: string;
  startOffset: number;
  endOffset: number;
  color: string;
  note?: string;
  createdAt: string;
}
```

#### HighlightListResponse
```typescript
interface HighlightListResponse {
  highlights: HighlightResponse[];
}
```

#### PresetResponse
```typescript
interface PresetResponse {
  id: string;
  name: string;
  color: string;
  isDefault: boolean;
}
```

#### PresetListResponse
```typescript
interface PresetListResponse {
  presets: PresetResponse[];
}
```

#### ChatResponse
```typescript
interface ChatResponse {
  message: string;
}
```

---

## API Endpoints

### Papers API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/papers` | List all papers with optional filters |
| GET | `/papers/{paperId}` | Get paper details |
| POST | `/papers` | Upload new paper (multipart/form-data) |
| PUT | `/papers/{paperId}` | Update paper metadata |
| DELETE | `/papers/{paperId}` | Delete paper |

### Translations API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/papers/{paperId}/translations/languages` | Get available languages |
| GET | `/papers/{paperId}/translations/{language}` | Get translation |
| POST | `/papers/{paperId}/translations` | Create translation |

### Summaries API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/papers/{paperId}/summaries/{language}` | Get summary |
| POST | `/papers/{paperId}/summaries` | Create summary |

### Highlights API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/papers/{paperId}/highlights` | Get user's highlights for paper |
| POST | `/papers/{paperId}/highlights` | Create highlight |
| PUT | `/papers/{paperId}/highlights/{highlightId}` | Update highlight |
| DELETE | `/papers/{paperId}/highlights/{highlightId}` | Delete highlight |

### Highlight Presets API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/highlight-presets` | Get user's presets |
| POST | `/highlight-presets` | Create preset |
| PUT | `/highlight-presets/{presetId}` | Update preset |
| DELETE | `/highlight-presets/{presetId}` | Delete preset |
| PUT | `/highlight-presets/{presetId}/default` | Set as default |

### Chat API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/papers/{paperId}/chat` | Send chat message |

---

## S3 Storage Structure

```
supersuat-storage/
├── pdfs/
│   └── {paperId}.pdf
├── figures/
│   └── {paperId}/
│       ├── fig-001.png
│       ├── fig-002.png
│       └── ...
└── tables/
    └── {paperId}/
        └── (if images are needed)
```

---

## Cognito User Pool Configuration

### User Attributes

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| sub | String | Yes | Unique user ID (auto-generated) |
| email | String | Yes | User email from Google |
| name | String | No | User's display name |
| picture | String | No | Profile picture URL |

### Identity Provider

- Google OAuth 2.0
- Scopes: email, profile, openid

### Token Configuration

- Access token validity: 1 hour
- Refresh token validity: 30 days
- ID token validity: 1 hour
