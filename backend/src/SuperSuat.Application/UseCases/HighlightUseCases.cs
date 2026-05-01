using SuperSuat.Application.DTOs;
using SuperSuat.Application.Interfaces;
using SuperSuat.Domain.Entities;

namespace SuperSuat.Application.UseCases;

public class HighlightUseCases
{
    private readonly IHighlightRepository _highlightRepository;

    public HighlightUseCases(IHighlightRepository highlightRepository)
    {
        _highlightRepository = highlightRepository;
    }

    public async Task<HighlightListResponse> GetHighlightsAsync(string paperId, string userId, CancellationToken cancellationToken = default)
    {
        var highlights = await _highlightRepository.GetByPaperIdAsync(paperId, userId, cancellationToken);
        return new HighlightListResponse
        {
            Highlights = highlights.Select(MapToResponse).ToList()
        };
    }

    public async Task<HighlightResponse> CreateHighlightAsync(string paperId, string userId, CreateHighlightRequest request, CancellationToken cancellationToken = default)
    {
        var highlight = new Highlight
        {
            Id = Guid.NewGuid().ToString(),
            PaperId = paperId,
            UserId = userId,
            ParagraphId = request.ParagraphId,
            StartOffset = request.StartOffset,
            EndOffset = request.EndOffset,
            Color = request.Color,
            Note = request.Note,
            CreatedAt = DateTime.UtcNow
        };

        await _highlightRepository.CreateAsync(highlight, cancellationToken);
        return MapToResponse(highlight);
    }

    public async Task<HighlightResponse?> UpdateHighlightAsync(string highlightId, string userId, UpdateHighlightRequest request, CancellationToken cancellationToken = default)
    {
        var highlight = await _highlightRepository.GetByIdAsync(highlightId, userId, cancellationToken);
        if (highlight == null) return null;

        if (request.Color != null)
            highlight.Color = request.Color;

        if (request.Note != null)
            highlight.Note = request.Note;

        await _highlightRepository.UpdateAsync(highlight, cancellationToken);
        return MapToResponse(highlight);
    }

    public async Task DeleteHighlightAsync(string highlightId, string userId, string paperId, CancellationToken cancellationToken = default)
    {
        await _highlightRepository.DeleteAsync(highlightId, userId, paperId, cancellationToken);
    }

    private static HighlightResponse MapToResponse(Highlight h) => new()
    {
        Id = h.Id,
        PaperId = h.PaperId,
        ParagraphId = h.ParagraphId,
        StartOffset = h.StartOffset,
        EndOffset = h.EndOffset,
        Color = h.Color,
        Note = h.Note,
        CreatedAt = h.CreatedAt
    };
}
