using SuperSuat.Domain.Entities;

namespace SuperSuat.Application.Interfaces;

public class ProcessingOptions
{
    public string? TargetLanguage { get; set; }
    public bool IncludeSummary { get; set; } = true;
    public bool IncludeChapterSummaries { get; set; } = false;
}

public class ProcessedPaper
{
    public Paper Paper { get; set; } = new();
    public TextContent TextContent { get; set; } = new();
    public List<Figure> Figures { get; set; } = [];
    public List<Table> Tables { get; set; } = [];
    public List<Equation> Equations { get; set; } = [];
}

public interface IPdfProcessingService
{
    Task<ProcessedPaper> ProcessPdfAsync(byte[] pdfData, ProcessingOptions options, CancellationToken cancellationToken = default);
}
