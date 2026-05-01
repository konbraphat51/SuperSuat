using SuperSuat.Domain.Entities;

namespace SuperSuat.Application.Interfaces;

public interface IHighlightRepository
{
    Task<List<Highlight>> GetByPaperIdAsync(string paperId, string userId, CancellationToken cancellationToken = default);
    Task<Highlight?> GetByIdAsync(string id, string userId, CancellationToken cancellationToken = default);
    Task<Highlight> CreateAsync(Highlight highlight, CancellationToken cancellationToken = default);
    Task<Highlight> UpdateAsync(Highlight highlight, CancellationToken cancellationToken = default);
    Task DeleteAsync(string id, string userId, string paperId, CancellationToken cancellationToken = default);
}
