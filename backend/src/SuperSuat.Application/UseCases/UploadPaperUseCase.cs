using SuperSuat.Application.Interfaces;
using SuperSuat.Domain.Entities;

namespace SuperSuat.Application.UseCases;

public class UploadPaperUseCase
{
    private readonly IPdfProcessingService _pdfProcessingService;
    private readonly IPaperRepository _paperRepository;
    private readonly ITextContentRepository _textContentRepository;
    private readonly IFigureRepository _figureRepository;
    private readonly ITableRepository _tableRepository;
    private readonly IEquationRepository _equationRepository;
    private readonly IStorageService _storageService;

    public UploadPaperUseCase(
        IPdfProcessingService pdfProcessingService,
        IPaperRepository paperRepository,
        ITextContentRepository textContentRepository,
        IFigureRepository figureRepository,
        ITableRepository tableRepository,
        IEquationRepository equationRepository,
        IStorageService storageService)
    {
        _pdfProcessingService = pdfProcessingService;
        _paperRepository = paperRepository;
        _textContentRepository = textContentRepository;
        _figureRepository = figureRepository;
        _tableRepository = tableRepository;
        _equationRepository = equationRepository;
        _storageService = storageService;
    }

    public async Task<Paper> ExecuteAsync(byte[] pdfData, ProcessingOptions options, CancellationToken cancellationToken = default)
    {
        // Process the PDF
        var processedPaper = await _pdfProcessingService.ProcessPdfAsync(pdfData, options, cancellationToken);

        // Generate IDs
        var paperId = Guid.NewGuid().ToString();
        var now = DateTime.UtcNow;

        processedPaper.Paper.Id = paperId;
        processedPaper.Paper.CreatedAt = now;
        processedPaper.Paper.UpdatedAt = now;

        // Upload PDF to storage
        var pdfUrl = await _storageService.UploadAsync(pdfData, $"pdfs/{paperId}.pdf", "application/pdf", cancellationToken);
        processedPaper.Paper.PdfUrl = pdfUrl;

        // Set paper ID on related entities
        processedPaper.TextContent.Id = Guid.NewGuid().ToString();
        processedPaper.TextContent.PaperId = paperId;

        foreach (var figure in processedPaper.Figures)
        {
            figure.PaperId = paperId;
        }

        foreach (var table in processedPaper.Tables)
        {
            table.PaperId = paperId;
        }

        foreach (var equation in processedPaper.Equations)
        {
            equation.PaperId = paperId;
        }

        // Save all entities
        await _paperRepository.CreateAsync(processedPaper.Paper, cancellationToken);
        await _textContentRepository.CreateAsync(processedPaper.TextContent, cancellationToken);

        if (processedPaper.Figures.Count > 0)
            await _figureRepository.CreateBatchAsync(processedPaper.Figures, cancellationToken);

        if (processedPaper.Tables.Count > 0)
            await _tableRepository.CreateBatchAsync(processedPaper.Tables, cancellationToken);

        if (processedPaper.Equations.Count > 0)
            await _equationRepository.CreateBatchAsync(processedPaper.Equations, cancellationToken);

        return processedPaper.Paper;
    }
}
