using SuperSuat.Application.DTOs;
using SuperSuat.Application.Interfaces;
using SuperSuat.Domain.Entities;

namespace SuperSuat.Application.UseCases;

public class GetPaperDetailUseCase
{
    private readonly IPaperRepository _paperRepository;
    private readonly ITextContentRepository _textContentRepository;
    private readonly IFigureRepository _figureRepository;
    private readonly ITableRepository _tableRepository;
    private readonly IEquationRepository _equationRepository;

    public GetPaperDetailUseCase(
        IPaperRepository paperRepository,
        ITextContentRepository textContentRepository,
        IFigureRepository figureRepository,
        ITableRepository tableRepository,
        IEquationRepository equationRepository)
    {
        _paperRepository = paperRepository;
        _textContentRepository = textContentRepository;
        _figureRepository = figureRepository;
        _tableRepository = tableRepository;
        _equationRepository = equationRepository;
    }

    public async Task<PaperDetailResponse?> ExecuteAsync(string paperId, CancellationToken cancellationToken = default)
    {
        var paper = await _paperRepository.GetByIdAsync(paperId, cancellationToken);
        if (paper == null) return null;

        var textContentTask = _textContentRepository.GetByPaperIdAsync(paperId, cancellationToken);
        var figuresTask = _figureRepository.GetByPaperIdAsync(paperId, cancellationToken);
        var tablesTask = _tableRepository.GetByPaperIdAsync(paperId, cancellationToken);
        var equationsTask = _equationRepository.GetByPaperIdAsync(paperId, cancellationToken);

        await Task.WhenAll(textContentTask, figuresTask, tablesTask, equationsTask);

        var textContent = await textContentTask;
        var figures = await figuresTask;
        var tables = await tablesTask;
        var equations = await equationsTask;

        return new PaperDetailResponse
        {
            Id = paper.Id,
            Title = paper.Title,
            Authors = paper.Authors,
            Description = paper.Description,
            Tags = paper.Tags,
            OriginalUrl = paper.OriginalUrl,
            CreatedAt = paper.CreatedAt,
            UpdatedAt = paper.UpdatedAt,
            Content = MapTextContent(textContent),
            Figures = figures.Select(MapFigure).ToList(),
            Tables = tables.Select(MapTable).ToList(),
            Equations = equations.Select(MapEquation).ToList()
        };
    }

    private static TextContentDto MapTextContent(TextContent? content)
    {
        if (content == null) return new TextContentDto();

        return new TextContentDto
        {
            Sections = content.Sections.Select(s => new SectionDto
            {
                Id = s.Id,
                Title = s.Title,
                Level = s.Level,
                Order = s.Order,
                Paragraphs = s.Paragraphs.Select(p => new ParagraphDto
                {
                    Id = p.Id,
                    Content = p.Content,
                    Order = p.Order,
                    Type = p.Type.ToString()
                }).ToList()
            }).ToList()
        };
    }

    private static FigureDto MapFigure(Figure f) => new()
    {
        Id = f.Id,
        Caption = f.Caption,
        ImageUrl = f.ImageUrl,
        Order = f.Order
    };

    private static TableDto MapTable(Table t) => new()
    {
        Id = t.Id,
        Caption = t.Caption,
        Content = t.Content,
        Order = t.Order
    };

    private static EquationDto MapEquation(Equation e) => new()
    {
        Id = e.Id,
        LatexContent = e.LatexContent,
        Order = e.Order
    };
}
