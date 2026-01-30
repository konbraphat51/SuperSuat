using SuperSuat.Application.DTOs;
using SuperSuat.Application.Interfaces;
using SuperSuat.Domain.Entities;

namespace SuperSuat.Application.UseCases;

public class HighlightPresetUseCases
{
    private readonly IHighlightColorPresetRepository _presetRepository;

    public HighlightPresetUseCases(IHighlightColorPresetRepository presetRepository)
    {
        _presetRepository = presetRepository;
    }

    public async Task<PresetListResponse> GetPresetsAsync(string userId, CancellationToken cancellationToken = default)
    {
        var presets = await _presetRepository.GetByUserIdAsync(userId, cancellationToken);
        return new PresetListResponse
        {
            Presets = presets.Select(MapToResponse).ToList()
        };
    }

    public async Task<PresetResponse> CreatePresetAsync(string userId, CreatePresetRequest request, CancellationToken cancellationToken = default)
    {
        var preset = new HighlightColorPreset
        {
            Id = Guid.NewGuid().ToString(),
            UserId = userId,
            Name = request.Name,
            Color = request.Color,
            IsDefault = false,
            CreatedAt = DateTime.UtcNow
        };

        await _presetRepository.CreateAsync(preset, cancellationToken);
        return MapToResponse(preset);
    }

    public async Task<PresetResponse?> UpdatePresetAsync(string presetId, string userId, UpdatePresetRequest request, CancellationToken cancellationToken = default)
    {
        var preset = await _presetRepository.GetByIdAsync(presetId, userId, cancellationToken);
        if (preset == null) return null;

        if (request.Name != null)
            preset.Name = request.Name;

        if (request.Color != null)
            preset.Color = request.Color;

        await _presetRepository.UpdateAsync(preset, cancellationToken);
        return MapToResponse(preset);
    }

    public async Task DeletePresetAsync(string presetId, string userId, CancellationToken cancellationToken = default)
    {
        await _presetRepository.DeleteAsync(presetId, userId, cancellationToken);
    }

    public async Task<PresetResponse?> SetDefaultPresetAsync(string presetId, string userId, CancellationToken cancellationToken = default)
    {
        var preset = await _presetRepository.GetByIdAsync(presetId, userId, cancellationToken);
        if (preset == null) return null;

        // Clear existing default
        await _presetRepository.ClearDefaultAsync(userId, cancellationToken);

        // Set new default
        preset.IsDefault = true;
        await _presetRepository.UpdateAsync(preset, cancellationToken);

        return MapToResponse(preset);
    }

    private static PresetResponse MapToResponse(HighlightColorPreset p) => new()
    {
        Id = p.Id,
        Name = p.Name,
        Color = p.Color,
        IsDefault = p.IsDefault
    };
}
