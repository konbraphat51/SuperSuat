using SuperSuat.Application.DTOs;
using SuperSuat.Application.Interfaces;
using SuperSuat.Domain.Entities;

namespace SuperSuat.Application.UseCases;

public class TranslationUseCases
{
    private readonly ITextContentRepository _textContentRepository;
    private readonly ITranslationRepository _translationRepository;
    private readonly ILlmService _llmService;

    public TranslationUseCases(
        ITextContentRepository textContentRepository,
        ITranslationRepository translationRepository,
        ILlmService llmService)
    {
        _textContentRepository = textContentRepository;
        _translationRepository = translationRepository;
        _llmService = llmService;
    }

    public async Task<AvailableLanguagesResponse> GetAvailableLanguagesAsync(string paperId, CancellationToken cancellationToken = default)
    {
        var languages = await _translationRepository.GetAvailableLanguagesAsync(paperId, cancellationToken);
        return new AvailableLanguagesResponse { Languages = languages };
    }

    public async Task<TranslationResponse?> GetTranslationAsync(string paperId, string language, CancellationToken cancellationToken = default)
    {
        var translation = await _translationRepository.GetByPaperIdAndLanguageAsync(paperId, language, cancellationToken);
        if (translation == null) return null;

        return MapToResponse(translation);
    }

    public async Task<TranslationResponse?> CreateTranslationAsync(string paperId, CreateTranslationRequest request, CancellationToken cancellationToken = default)
    {
        // Check if translation already exists
        var existing = await _translationRepository.GetByPaperIdAndLanguageAsync(paperId, request.Language, cancellationToken);
        if (existing != null)
        {
            return MapToResponse(existing);
        }

        // Get text content
        var textContent = await _textContentRepository.GetByPaperIdAsync(paperId, cancellationToken);
        if (textContent == null) return null;

        // Create translation using LLM
        var translation = await _llmService.TranslateAsync(textContent, paperId, request.Language, cancellationToken);

        // Save translation
        await _translationRepository.CreateAsync(translation, cancellationToken);

        return MapToResponse(translation);
    }

    private static TranslationResponse MapToResponse(Translation translation) => new()
    {
        Id = translation.Id,
        PaperId = translation.PaperId,
        Language = translation.Language,
        Sections = translation.Sections.Select(s => new TranslatedSectionDto
        {
            SectionId = s.SectionId,
            TranslatedTitle = s.TranslatedTitle,
            Paragraphs = s.Paragraphs.Select(p => new TranslatedParagraphDto
            {
                ParagraphId = p.ParagraphId,
                TranslatedContent = p.TranslatedContent
            }).ToList()
        }).ToList()
    };
}
