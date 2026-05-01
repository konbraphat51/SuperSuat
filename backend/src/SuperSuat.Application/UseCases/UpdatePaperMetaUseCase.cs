using SuperSuat.Application.DTOs;
using SuperSuat.Application.Interfaces;
using SuperSuat.Domain.Entities;

namespace SuperSuat.Application.UseCases;

public class UpdatePaperMetaUseCase
{
    private readonly IPaperRepository _paperRepository;

    public UpdatePaperMetaUseCase(IPaperRepository paperRepository)
    {
        _paperRepository = paperRepository;
    }

    public async Task<Paper?> ExecuteAsync(string paperId, UpdatePaperMetaRequest request, CancellationToken cancellationToken = default)
    {
        var paper = await _paperRepository.GetByIdAsync(paperId, cancellationToken);
        if (paper == null) return null;

        if (request.Title != null)
            paper.Title = request.Title;

        if (request.Authors != null)
            paper.Authors = request.Authors;

        if (request.Description != null)
            paper.Description = request.Description;

        if (request.Tags != null)
            paper.Tags = request.Tags;

        if (request.OriginalUrl != null)
            paper.OriginalUrl = request.OriginalUrl;

        paper.UpdatedAt = DateTime.UtcNow;

        return await _paperRepository.UpdateAsync(paper, cancellationToken);
    }
}
