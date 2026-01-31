using SuperSuat.Domain.Entities;

namespace SuperSuat.Application.Interfaces;

public interface IFigureRepository
{
    Task<List<Figure>> GetByPaperIdAsync(string paperId, CancellationToken cancellationToken = default);
    Task<Figure> CreateAsync(Figure figure, CancellationToken cancellationToken = default);
    Task CreateBatchAsync(List<Figure> figures, CancellationToken cancellationToken = default);
}
