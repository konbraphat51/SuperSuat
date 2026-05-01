using SuperSuat.Domain.Entities;

namespace SuperSuat.Application.Interfaces;

public interface IHighlightColorPresetRepository
{
    Task<List<HighlightColorPreset>> GetByUserIdAsync(string userId, CancellationToken cancellationToken = default);
    Task<HighlightColorPreset?> GetByIdAsync(string id, string userId, CancellationToken cancellationToken = default);
    Task<HighlightColorPreset> CreateAsync(HighlightColorPreset preset, CancellationToken cancellationToken = default);
    Task<HighlightColorPreset> UpdateAsync(HighlightColorPreset preset, CancellationToken cancellationToken = default);
    Task DeleteAsync(string id, string userId, CancellationToken cancellationToken = default);
    Task ClearDefaultAsync(string userId, CancellationToken cancellationToken = default);
}
