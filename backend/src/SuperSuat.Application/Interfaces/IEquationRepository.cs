using SuperSuat.Domain.Entities;

namespace SuperSuat.Application.Interfaces;

public interface IEquationRepository
{
    Task<List<Equation>> GetByPaperIdAsync(string paperId, CancellationToken cancellationToken = default);
    Task<Equation> CreateAsync(Equation equation, CancellationToken cancellationToken = default);
    Task CreateBatchAsync(List<Equation> equations, CancellationToken cancellationToken = default);
}
