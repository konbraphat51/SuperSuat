using SuperSuat.Domain.Entities;
using SuperSuat.Domain.Enums;

namespace SuperSuat.Application.DTOs;

// Request DTOs
public class UpdatePaperMetaRequest
{
    public string? Title { get; set; }
    public List<string>? Authors { get; set; }
    public string? Description { get; set; }
    public List<string>? Tags { get; set; }
    public string? OriginalUrl { get; set; }
}

public class CreateTranslationRequest
{
    public string Language { get; set; } = string.Empty;
}

public class CreateSummaryRequest
{
    public string Language { get; set; } = "en";
    public bool IncludeChapterSummaries { get; set; } = false;
}

public class CreateHighlightRequest
{
    public string ParagraphId { get; set; } = string.Empty;
    public int StartOffset { get; set; }
    public int EndOffset { get; set; }
    public string Color { get; set; } = string.Empty;
    public string? Note { get; set; }
}

public class UpdateHighlightRequest
{
    public string? Color { get; set; }
    public string? Note { get; set; }
}

public class CreatePresetRequest
{
    public string Name { get; set; } = string.Empty;
    public string Color { get; set; } = string.Empty;
}

public class UpdatePresetRequest
{
    public string? Name { get; set; }
    public string? Color { get; set; }
}

public class ChatRequest
{
    public string Message { get; set; } = string.Empty;
}

// Response DTOs
public class PaperListResponse
{
    public List<PaperSummaryDto> Papers { get; set; } = [];
    public string? NextToken { get; set; }
}

public class PaperSummaryDto
{
    public string Id { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public List<string> Authors { get; set; } = [];
    public string Description { get; set; } = string.Empty;
    public List<string> Tags { get; set; } = [];
    public DateTime CreatedAt { get; set; }

    public static PaperSummaryDto FromPaper(Paper paper) => new()
    {
        Id = paper.Id,
        Title = paper.Title,
        Authors = paper.Authors,
        Description = paper.Description,
        Tags = paper.Tags,
        CreatedAt = paper.CreatedAt
    };
}

public class PaperDetailResponse
{
    public string Id { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public List<string> Authors { get; set; } = [];
    public string Description { get; set; } = string.Empty;
    public List<string> Tags { get; set; } = [];
    public string? OriginalUrl { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
    public TextContentDto Content { get; set; } = new();
    public List<FigureDto> Figures { get; set; } = [];
    public List<TableDto> Tables { get; set; } = [];
    public List<EquationDto> Equations { get; set; } = [];
}

public class TextContentDto
{
    public List<SectionDto> Sections { get; set; } = [];
}

public class SectionDto
{
    public string Id { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public int Level { get; set; }
    public int Order { get; set; }
    public List<ParagraphDto> Paragraphs { get; set; } = [];
}

public class ParagraphDto
{
    public string Id { get; set; } = string.Empty;
    public string Content { get; set; } = string.Empty;
    public int Order { get; set; }
    public string Type { get; set; } = string.Empty;
}

public class FigureDto
{
    public string Id { get; set; } = string.Empty;
    public string Caption { get; set; } = string.Empty;
    public string ImageUrl { get; set; } = string.Empty;
    public int Order { get; set; }
}

public class TableDto
{
    public string Id { get; set; } = string.Empty;
    public string Caption { get; set; } = string.Empty;
    public string Content { get; set; } = string.Empty;
    public int Order { get; set; }
}

public class EquationDto
{
    public string Id { get; set; } = string.Empty;
    public string LatexContent { get; set; } = string.Empty;
    public int Order { get; set; }
}

public class TranslationResponse
{
    public string Id { get; set; } = string.Empty;
    public string PaperId { get; set; } = string.Empty;
    public string Language { get; set; } = string.Empty;
    public List<TranslatedSectionDto> Sections { get; set; } = [];
}

public class TranslatedSectionDto
{
    public string SectionId { get; set; } = string.Empty;
    public string TranslatedTitle { get; set; } = string.Empty;
    public List<TranslatedParagraphDto> Paragraphs { get; set; } = [];
}

public class TranslatedParagraphDto
{
    public string ParagraphId { get; set; } = string.Empty;
    public string TranslatedContent { get; set; } = string.Empty;
}

public class AvailableLanguagesResponse
{
    public List<string> Languages { get; set; } = [];
}

public class SummaryResponse
{
    public string Id { get; set; } = string.Empty;
    public string PaperId { get; set; } = string.Empty;
    public string Language { get; set; } = string.Empty;
    public string WholeSummary { get; set; } = string.Empty;
    public List<ChapterSummaryDto>? ChapterSummaries { get; set; }
}

public class ChapterSummaryDto
{
    public string SectionId { get; set; } = string.Empty;
    public string Summary { get; set; } = string.Empty;
}

public class HighlightResponse
{
    public string Id { get; set; } = string.Empty;
    public string PaperId { get; set; } = string.Empty;
    public string ParagraphId { get; set; } = string.Empty;
    public int StartOffset { get; set; }
    public int EndOffset { get; set; }
    public string Color { get; set; } = string.Empty;
    public string? Note { get; set; }
    public DateTime CreatedAt { get; set; }
}

public class HighlightListResponse
{
    public List<HighlightResponse> Highlights { get; set; } = [];
}

public class PresetResponse
{
    public string Id { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string Color { get; set; } = string.Empty;
    public bool IsDefault { get; set; }
}

public class PresetListResponse
{
    public List<PresetResponse> Presets { get; set; } = [];
}

public class ChatResponse
{
    public string Message { get; set; } = string.Empty;
}

public class ErrorResponse
{
    public string Error { get; set; } = string.Empty;
    public string? Details { get; set; }
}
