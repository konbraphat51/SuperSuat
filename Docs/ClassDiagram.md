# Class Diagram

## Overview

This document describes the class structure for the SuperSuat paper reading assistance application following Clean Architecture and SOLID principles.

## Backend (C# .NET 10)

### Domain Layer

```mermaid
classDiagram
    class Paper {
        +string Id
        +string Title
        +List~string~ Authors
        +string Description
        +List~string~ Tags
        +string OriginalUrl
        +DateTime CreatedAt
        +DateTime UpdatedAt
    }

    class TextContent {
        +string Id
        +string PaperId
        +List~Section~ Sections
    }

    class Section {
        +string Id
        +string Title
        +int Level
        +List~Paragraph~ Paragraphs
        +int Order
    }

    class Paragraph {
        +string Id
        +string Content
        +int Order
        +ParagraphType Type
    }

    class ParagraphType {
        <<enumeration>>
        Text
        Equation
        FigureReference
        TableReference
    }

    class Figure {
        +string Id
        +string PaperId
        +string Caption
        +string ImageUrl
        +int Order
    }

    class Table {
        +string Id
        +string PaperId
        +string Caption
        +string Content
        +int Order
    }

    class Equation {
        +string Id
        +string PaperId
        +string LatexContent
        +int Order
    }

    class Translation {
        +string Id
        +string PaperId
        +string Language
        +List~TranslatedSection~ Sections
    }

    class TranslatedSection {
        +string SectionId
        +string TranslatedTitle
        +List~TranslatedParagraph~ Paragraphs
    }

    class TranslatedParagraph {
        +string ParagraphId
        +string TranslatedContent
    }

    class Summary {
        +string Id
        +string PaperId
        +string Language
        +string WholeSummary
        +List~ChapterSummary~ ChapterSummaries
    }

    class ChapterSummary {
        +string SectionId
        +string Summary
    }

    class Highlight {
        +string Id
        +string PaperId
        +string UserId
        +string ParagraphId
        +int StartOffset
        +int EndOffset
        +string Color
        +string Note
        +DateTime CreatedAt
    }

    class HighlightColorPreset {
        +string Id
        +string UserId
        +string Name
        +string Color
        +bool IsDefault
    }

    Paper "1" --> "*" TextContent : has
    TextContent "1" --> "*" Section : contains
    Section "1" --> "*" Paragraph : contains
    Paper "1" --> "*" Figure : has
    Paper "1" --> "*" Table : has
    Paper "1" --> "*" Equation : has
    Paper "1" --> "*" Translation : has
    Translation "1" --> "*" TranslatedSection : contains
    TranslatedSection "1" --> "*" TranslatedParagraph : contains
    Paper "1" --> "*" Summary : has
    Summary "1" --> "*" ChapterSummary : contains
    Paper "1" --> "*" Highlight : has
```

### Application Layer - Interfaces

```mermaid
classDiagram
    class IPaperRepository {
        <<interface>>
        +GetByIdAsync(id: string) Paper
        +GetAllAsync(filter: PaperFilter) List~Paper~
        +CreateAsync(paper: Paper) Paper
        +UpdateAsync(paper: Paper) Paper
        +DeleteAsync(id: string) void
    }

    class ITextContentRepository {
        <<interface>>
        +GetByPaperIdAsync(paperId: string) TextContent
        +CreateAsync(content: TextContent) TextContent
        +UpdateAsync(content: TextContent) TextContent
    }

    class IFigureRepository {
        <<interface>>
        +GetByPaperIdAsync(paperId: string) List~Figure~
        +CreateAsync(figure: Figure) Figure
    }

    class ITableRepository {
        <<interface>>
        +GetByPaperIdAsync(paperId: string) List~Table~
        +CreateAsync(table: Table) Table
    }

    class IEquationRepository {
        <<interface>>
        +GetByPaperIdAsync(paperId: string) List~Equation~
        +CreateAsync(equation: Equation) Equation
    }

    class ITranslationRepository {
        <<interface>>
        +GetByPaperIdAndLanguageAsync(paperId: string, language: string) Translation
        +GetAvailableLanguagesAsync(paperId: string) List~string~
        +CreateAsync(translation: Translation) Translation
    }

    class ISummaryRepository {
        <<interface>>
        +GetByPaperIdAndLanguageAsync(paperId: string, language: string) Summary
        +CreateAsync(summary: Summary) Summary
    }

    class IHighlightRepository {
        <<interface>>
        +GetByPaperIdAsync(paperId: string, userId: string) List~Highlight~
        +CreateAsync(highlight: Highlight) Highlight
        +UpdateAsync(highlight: Highlight) Highlight
        +DeleteAsync(id: string) void
    }

    class IHighlightColorPresetRepository {
        <<interface>>
        +GetByUserIdAsync(userId: string) List~HighlightColorPreset~
        +CreateAsync(preset: HighlightColorPreset) HighlightColorPreset
        +UpdateAsync(preset: HighlightColorPreset) HighlightColorPreset
        +DeleteAsync(id: string) void
    }

    class IPdfProcessingService {
        <<interface>>
        +ProcessPdfAsync(pdfData: byte[], options: ProcessingOptions) ProcessedPaper
    }

    class ILlmService {
        <<interface>>
        +ExtractTextAsync(pdfContent: string) TextContent
        +TranslateAsync(content: TextContent, targetLanguage: string) Translation
        +SummarizeAsync(content: TextContent, options: SummaryOptions) Summary
        +ChatAsync(context: string, message: string) string
    }

    class IStorageService {
        <<interface>>
        +UploadAsync(data: byte[], key: string) string
        +GetUrlAsync(key: string) string
        +DeleteAsync(key: string) void
    }

    class IAuthService {
        <<interface>>
        +ValidateTokenAsync(token: string) UserClaims
        +GetUserIdAsync(token: string) string
    }
```

### Application Layer - Use Cases

```mermaid
classDiagram
    class UploadPaperUseCase {
        -IPdfProcessingService _pdfService
        -IPaperRepository _paperRepo
        -ITextContentRepository _textRepo
        -IFigureRepository _figureRepo
        -ITableRepository _tableRepo
        -IEquationRepository _equationRepo
        +ExecuteAsync(command: UploadPaperCommand) Paper
    }

    class GetPaperListUseCase {
        -IPaperRepository _paperRepo
        +ExecuteAsync(query: PaperListQuery) List~PaperSummaryDto~
    }

    class GetPaperDetailUseCase {
        -IPaperRepository _paperRepo
        -ITextContentRepository _textRepo
        -IFigureRepository _figureRepo
        -ITableRepository _tableRepo
        -IEquationRepository _equationRepo
        +ExecuteAsync(paperId: string) PaperDetailDto
    }

    class UpdatePaperMetaUseCase {
        -IPaperRepository _paperRepo
        +ExecuteAsync(command: UpdatePaperMetaCommand) Paper
    }

    class GetTranslationUseCase {
        -ITranslationRepository _translationRepo
        +ExecuteAsync(paperId: string, language: string) Translation
    }

    class CreateTranslationUseCase {
        -ITextContentRepository _textRepo
        -ITranslationRepository _translationRepo
        -ILlmService _llmService
        +ExecuteAsync(command: CreateTranslationCommand) Translation
    }

    class GetSummaryUseCase {
        -ISummaryRepository _summaryRepo
        +ExecuteAsync(paperId: string, language: string) Summary
    }

    class CreateSummaryUseCase {
        -ITextContentRepository _textRepo
        -ISummaryRepository _summaryRepo
        -ILlmService _llmService
        +ExecuteAsync(command: CreateSummaryCommand) Summary
    }

    class ManageHighlightsUseCase {
        -IHighlightRepository _highlightRepo
        +GetAsync(paperId: string, userId: string) List~Highlight~
        +CreateAsync(command: CreateHighlightCommand) Highlight
        +UpdateAsync(command: UpdateHighlightCommand) Highlight
        +DeleteAsync(id: string) void
    }

    class ChatUseCase {
        -ITextContentRepository _textRepo
        -ILlmService _llmService
        +ExecuteAsync(paperId: string, message: string) string
    }

    class ManageHighlightPresetsUseCase {
        -IHighlightColorPresetRepository _presetRepo
        +GetAsync(userId: string) List~HighlightColorPreset~
        +CreateAsync(command: CreatePresetCommand) HighlightColorPreset
        +UpdateAsync(command: UpdatePresetCommand) HighlightColorPreset
        +DeleteAsync(id: string) void
        +SetDefaultAsync(userId: string, presetId: string) void
    }
```

### Infrastructure Layer

```mermaid
classDiagram
    class DynamoDbPaperRepository {
        -IAmazonDynamoDB _dynamoDb
        -string _tableName
    }

    class DynamoDbTextContentRepository {
        -IAmazonDynamoDB _dynamoDb
        -string _tableName
    }

    class DynamoDbFigureRepository {
        -IAmazonDynamoDB _dynamoDb
        -string _tableName
    }

    class DynamoDbTableRepository {
        -IAmazonDynamoDB _dynamoDb
        -string _tableName
    }

    class DynamoDbEquationRepository {
        -IAmazonDynamoDB _dynamoDb
        -string _tableName
    }

    class DynamoDbTranslationRepository {
        -IAmazonDynamoDB _dynamoDb
        -string _tableName
    }

    class DynamoDbSummaryRepository {
        -IAmazonDynamoDB _dynamoDb
        -string _tableName
    }

    class DynamoDbHighlightRepository {
        -IAmazonDynamoDB _dynamoDb
        -string _tableName
    }

    class DynamoDbHighlightColorPresetRepository {
        -IAmazonDynamoDB _dynamoDb
        -string _tableName
    }

    class BedrockLlmService {
        -IAmazonBedrockRuntime _bedrockRuntime
        -string _modelId
    }

    class S3StorageService {
        -IAmazonS3 _s3Client
        -string _bucketName
    }

    class CognitoAuthService {
        -IAmazonCognitoIdentityProvider _cognitoClient
        -string _userPoolId
    }

    IPaperRepository <|.. DynamoDbPaperRepository
    ITextContentRepository <|.. DynamoDbTextContentRepository
    IFigureRepository <|.. DynamoDbFigureRepository
    ITableRepository <|.. DynamoDbTableRepository
    IEquationRepository <|.. DynamoDbEquationRepository
    ITranslationRepository <|.. DynamoDbTranslationRepository
    ISummaryRepository <|.. DynamoDbSummaryRepository
    IHighlightRepository <|.. DynamoDbHighlightRepository
    IHighlightColorPresetRepository <|.. DynamoDbHighlightColorPresetRepository
    ILlmService <|.. BedrockLlmService
    IStorageService <|.. S3StorageService
    IAuthService <|.. CognitoAuthService
```

## Frontend (React + TypeScript)

### Component Structure

```mermaid
classDiagram
    class App {
        +AuthProvider
        +ThemeProvider
        +Router
    }

    class PaperListPage {
        +PaperListFilter
        +PaperListTable
        +PaperListPagination
    }

    class PaperListFilter {
        +TagFilter
        +AuthorFilter
        +DateFilter
        +ColumnSelector
    }

    class PaperListTable {
        +PaperListRow[]
    }

    class PaperReaderPage {
        +ReaderToolbar
        +ReaderSidebar
        +ReaderContent
    }

    class ReaderToolbar {
        +ViewStyleSettings
        +LanguageSelector
        +HighlightColorPicker
    }

    class ReaderSidebar {
        +SectionNavigator
        +HighlightsList
        +SummaryPanel
        +ChatPanel
    }

    class ReaderContent {
        +SectionRenderer
        +ParagraphRenderer
        +FigureRenderer
        +TableRenderer
        +EquationRenderer
        +HighlightOverlay
    }

    class ViewStyleSettings {
        +FontSizeSlider
        +LineHeightSlider
        +FontFamilySelector
        +ColorSetSelector
        +MarginSizeSlider
    }

    class HighlightColorPicker {
        +ColorPresetList
        +CustomColorInput
        +PresetManager
    }

    class SectionNavigator {
        +SectionItem[]
    }

    class HighlightsList {
        +HighlightItem[]
    }

    class SummaryPanel {
        +WholeSummary
        +ChapterSummaryList
    }

    class ChatPanel {
        +MessageList
        +MessageInput
    }

    class PaperUploadPage {
        +UploadForm
        +ProcessingStatus
    }

    class PaperMetaEditPage {
        +MetaEditForm
    }

    App --> PaperListPage
    App --> PaperReaderPage
    App --> PaperUploadPage
    App --> PaperMetaEditPage
    PaperListPage --> PaperListFilter
    PaperListPage --> PaperListTable
    PaperReaderPage --> ReaderToolbar
    PaperReaderPage --> ReaderSidebar
    PaperReaderPage --> ReaderContent
    ReaderToolbar --> ViewStyleSettings
    ReaderToolbar --> HighlightColorPicker
    ReaderSidebar --> SectionNavigator
    ReaderSidebar --> HighlightsList
    ReaderSidebar --> SummaryPanel
    ReaderSidebar --> ChatPanel
```

### Service Layer

```mermaid
classDiagram
    class ApiClient {
        -baseUrl: string
        -authToken: string
        +get~T~(path: string) Promise~T~
        +post~T~(path: string, data: any) Promise~T~
        +put~T~(path: string, data: any) Promise~T~
        +delete(path: string) Promise~void~
    }

    class PaperService {
        -apiClient: ApiClient
        +getPapers(filter: PaperFilter) Promise~Paper[]~
        +getPaper(id: string) Promise~PaperDetail~
        +updatePaperMeta(id: string, meta: PaperMeta) Promise~Paper~
        +uploadPaper(file: File) Promise~Paper~
    }

    class TranslationService {
        -apiClient: ApiClient
        +getAvailableLanguages(paperId: string) Promise~string[]~
        +getTranslation(paperId: string, language: string) Promise~Translation~
        +createTranslation(paperId: string, language: string) Promise~Translation~
    }

    class SummaryService {
        -apiClient: ApiClient
        +getSummary(paperId: string, language: string) Promise~Summary~
        +createSummary(paperId: string, options: SummaryOptions) Promise~Summary~
    }

    class HighlightService {
        -apiClient: ApiClient
        +getHighlights(paperId: string) Promise~Highlight[]~
        +createHighlight(highlight: CreateHighlightDto) Promise~Highlight~
        +updateHighlight(id: string, highlight: UpdateHighlightDto) Promise~Highlight~
        +deleteHighlight(id: string) Promise~void~
    }

    class HighlightPresetService {
        -apiClient: ApiClient
        +getPresets() Promise~HighlightColorPreset[]~
        +createPreset(preset: CreatePresetDto) Promise~HighlightColorPreset~
        +updatePreset(id: string, preset: UpdatePresetDto) Promise~HighlightColorPreset~
        +deletePreset(id: string) Promise~void~
        +setDefault(id: string) Promise~void~
    }

    class ChatService {
        -apiClient: ApiClient
        +sendMessage(paperId: string, message: string) Promise~string~
    }

    class AuthService {
        +login() Promise~void~
        +logout() Promise~void~
        +getToken() string
        +isAuthenticated() boolean
    }

    PaperService --> ApiClient
    TranslationService --> ApiClient
    SummaryService --> ApiClient
    HighlightService --> ApiClient
    HighlightPresetService --> ApiClient
    ChatService --> ApiClient
```

### State Management (Context)

```mermaid
classDiagram
    class AuthContext {
        +user: User | null
        +isAuthenticated: boolean
        +login() void
        +logout() void
    }

    class ViewStyleContext {
        +fontSize: number
        +lineHeight: number
        +fontFamily: string
        +colorSet: ColorSet
        +marginSize: number
        +updateStyle(style: Partial~ViewStyle~) void
    }

    class HighlightContext {
        +highlights: Highlight[]
        +selectedColor: string
        +presets: HighlightColorPreset[]
        +defaultPreset: HighlightColorPreset | null
        +addHighlight(highlight: CreateHighlightDto) void
        +updateHighlight(id: string, update: UpdateHighlightDto) void
        +removeHighlight(id: string) void
        +setSelectedColor(color: string) void
    }

    class ReaderContext {
        +paper: PaperDetail | null
        +currentLanguage: string
        +translation: Translation | null
        +summary: Summary | null
        +setLanguage(language: string) void
        +loadTranslation(language: string) void
        +loadSummary(language: string) void
    }
```
