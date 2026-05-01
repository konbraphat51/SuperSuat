using SuperSuat.Domain.Entities;

namespace SuperSuat.Application.Interfaces;

public interface ISummaryRepository
{
    Task<Summary?> GetByPaperIdAndLanguageAsync(string paperId, string language, CancellationToken cancellationToken = default);
    Task<Summary> CreateAsync(Summary summary, CancellationToken cancellationToken = default);
}
