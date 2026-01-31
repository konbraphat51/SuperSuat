using SuperSuat.Application.DTOs;
using SuperSuat.Application.Interfaces;

namespace SuperSuat.Application.UseCases;

public class GetPaperListUseCase
{
    private readonly IPaperRepository _paperRepository;

    public GetPaperListUseCase(IPaperRepository paperRepository)
    {
        _paperRepository = paperRepository;
    }

    public async Task<PaperListResponse> ExecuteAsync(PaperFilter filter, CancellationToken cancellationToken = default)
    {
        var (papers, nextToken) = await _paperRepository.GetAllAsync(filter, cancellationToken);

        return new PaperListResponse
        {
            Papers = papers.Select(PaperSummaryDto.FromPaper).ToList(),
            NextToken = nextToken
        };
    }
}
