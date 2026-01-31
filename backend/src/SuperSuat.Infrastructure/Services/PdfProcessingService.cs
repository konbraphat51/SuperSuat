using SuperSuat.Application.Interfaces;
using SuperSuat.Domain.Entities;

namespace SuperSuat.Infrastructure.Services;

public class PdfProcessingService : IPdfProcessingService
{
    private readonly ILlmService _llmService;

    public PdfProcessingService(ILlmService llmService)
    {
        _llmService = llmService;
    }

    public async Task<ProcessedPaper> ProcessPdfAsync(byte[] pdfData, ProcessingOptions options, CancellationToken cancellationToken = default)
    {
        // Generate paper ID
        var paperId = Guid.NewGuid().ToString();

        // Extract text content
        var textContent = await _llmService.ExtractTextAsync(pdfData, cancellationToken);
        textContent.Id = Guid.NewGuid().ToString();
        textContent.PaperId = paperId;

        // Extract metadata and media
        var (paper, figures, tables, equations) = await _llmService.ExtractMetadataAndMediaAsync(pdfData, paperId, cancellationToken);

        return new ProcessedPaper
        {
            Paper = paper,
            TextContent = textContent,
            Figures = figures,
            Tables = tables,
            Equations = equations
        };
    }
}
