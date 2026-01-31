using SuperSuat.Domain.Entities;

namespace SuperSuat.Application.Interfaces;

public class PaperFilter
{
    public List<string>? Tags { get; set; }
    public List<string>? Authors { get; set; }
    public DateTime? FromDate { get; set; }
    public DateTime? ToDate { get; set; }
    public string? SearchText { get; set; }
    public int PageSize { get; set; } = 20;
    public string? NextToken { get; set; }
}

public interface IPaperRepository
{
    Task<Paper?> GetByIdAsync(string id, CancellationToken cancellationToken = default);
    Task<(List<Paper> Papers, string? NextToken)> GetAllAsync(PaperFilter filter, CancellationToken cancellationToken = default);
    Task<Paper> CreateAsync(Paper paper, CancellationToken cancellationToken = default);
    Task<Paper> UpdateAsync(Paper paper, CancellationToken cancellationToken = default);
    Task DeleteAsync(string id, CancellationToken cancellationToken = default);
}
