using SuperSuat.Domain.Entities;

namespace SuperSuat.Application.Interfaces;

public interface ITextContentRepository
{
    Task<TextContent?> GetByPaperIdAsync(string paperId, CancellationToken cancellationToken = default);
    Task<TextContent> CreateAsync(TextContent content, CancellationToken cancellationToken = default);
    Task<TextContent> UpdateAsync(TextContent content, CancellationToken cancellationToken = default);
}
