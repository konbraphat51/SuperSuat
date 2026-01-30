using SuperSuat.Domain.Entities;

namespace SuperSuat.Application.Interfaces;

public class SummaryOptions
{
    public string Language { get; set; } = "en";
    public bool IncludeChapterSummaries { get; set; } = false;
}

public interface ILlmService
{
    Task<TextContent> ExtractTextAsync(byte[] pdfData, CancellationToken cancellationToken = default);
    Task<(Paper paper, List<Figure> figures, List<Table> tables, List<Equation> equations)> ExtractMetadataAndMediaAsync(byte[] pdfData, string paperId, CancellationToken cancellationToken = default);
    Task<Translation> TranslateAsync(TextContent content, string paperId, string targetLanguage, CancellationToken cancellationToken = default);
    Task<Summary> SummarizeAsync(TextContent content, string paperId, SummaryOptions options, CancellationToken cancellationToken = default);
    Task<string> ChatAsync(string paperContext, string message, CancellationToken cancellationToken = default);
}
