using SuperSuat.Domain.Entities;

namespace SuperSuat.Application.Interfaces;

public interface ITableRepository
{
    Task<List<Table>> GetByPaperIdAsync(string paperId, CancellationToken cancellationToken = default);
    Task<Table> CreateAsync(Table table, CancellationToken cancellationToken = default);
    Task CreateBatchAsync(List<Table> tables, CancellationToken cancellationToken = default);
}
