using SuperSuat.Domain.Entities;

namespace SuperSuat.Application.Interfaces;

public interface ITranslationRepository
{
    Task<Translation?> GetByPaperIdAndLanguageAsync(string paperId, string language, CancellationToken cancellationToken = default);
    Task<List<string>> GetAvailableLanguagesAsync(string paperId, CancellationToken cancellationToken = default);
    Task<Translation> CreateAsync(Translation translation, CancellationToken cancellationToken = default);
}
