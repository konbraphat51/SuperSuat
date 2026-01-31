using SuperSuat.Application.DTOs;
using SuperSuat.Application.Interfaces;
using SuperSuat.Domain.Entities;

namespace SuperSuat.Application.UseCases;

public class SummaryUseCases
{
    private readonly ITextContentRepository _textContentRepository;
    private readonly ISummaryRepository _summaryRepository;
    private readonly ILlmService _llmService;

    public SummaryUseCases(
        ITextContentRepository textContentRepository,
        ISummaryRepository summaryRepository,
        ILlmService llmService)
    {
        _textContentRepository = textContentRepository;
        _summaryRepository = summaryRepository;
        _llmService = llmService;
    }

    public async Task<SummaryResponse?> GetSummaryAsync(string paperId, string language, CancellationToken cancellationToken = default)
    {
        var summary = await _summaryRepository.GetByPaperIdAndLanguageAsync(paperId, language, cancellationToken);
        if (summary == null) return null;

        return MapToResponse(summary);
    }

    public async Task<SummaryResponse?> CreateSummaryAsync(string paperId, CreateSummaryRequest request, CancellationToken cancellationToken = default)
    {
        // Check if summary already exists
        var existing = await _summaryRepository.GetByPaperIdAndLanguageAsync(paperId, request.Language, cancellationToken);
        if (existing != null)
        {
            return MapToResponse(existing);
        }

        // Get text content
        var textContent = await _textContentRepository.GetByPaperIdAsync(paperId, cancellationToken);
        if (textContent == null) return null;

        // Create summary using LLM
        var summaryOptions = new SummaryOptions
        {
            Language = request.Language,
            IncludeChapterSummaries = request.IncludeChapterSummaries
        };
        var summary = await _llmService.SummarizeAsync(textContent, paperId, summaryOptions, cancellationToken);

        // Save summary
        await _summaryRepository.CreateAsync(summary, cancellationToken);

        return MapToResponse(summary);
    }

    private static SummaryResponse MapToResponse(Summary summary) => new()
    {
        Id = summary.Id,
        PaperId = summary.PaperId,
        Language = summary.Language,
        WholeSummary = summary.WholeSummary,
        ChapterSummaries = summary.ChapterSummaries?.Select(c => new ChapterSummaryDto
        {
            SectionId = c.SectionId,
            Summary = c.Summary
        }).ToList()
    };
}
