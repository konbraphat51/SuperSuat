using Moq;
using SuperSuat.Application.DTOs;
using SuperSuat.Application.Interfaces;
using SuperSuat.Application.UseCases;
using SuperSuat.Domain.Entities;
using SuperSuat.Domain.Enums;

namespace SuperSuat.Application.Tests;

public class GetPaperListUseCaseTests
{
    [Fact]
    public async Task ExecuteAsync_ShouldReturnPaperList()
    {
        // Arrange
        var mockRepo = new Mock<IPaperRepository>();
        var papers = new List<Paper>
        {
            new()
            {
                Id = "1",
                Title = "Test Paper",
                Authors = ["Author 1"],
                Description = "Test description",
                Tags = ["tag1"],
                CreatedAt = DateTime.UtcNow,
                UpdatedAt = DateTime.UtcNow
            }
        };
        mockRepo.Setup(r => r.GetAllAsync(It.IsAny<PaperFilter>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((papers, (string?)null));

        var useCase = new GetPaperListUseCase(mockRepo.Object);

        // Act
        var result = await useCase.ExecuteAsync(new PaperFilter());

        // Assert
        Assert.NotNull(result);
        Assert.Single(result.Papers);
        Assert.Equal("Test Paper", result.Papers[0].Title);
    }
}

public class UpdatePaperMetaUseCaseTests
{
    [Fact]
    public async Task ExecuteAsync_ShouldUpdatePaper()
    {
        // Arrange
        var mockRepo = new Mock<IPaperRepository>();
        var paper = new Paper
        {
            Id = "1",
            Title = "Original Title",
            Authors = ["Author 1"],
            Description = "Original description",
            Tags = ["tag1"],
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        };
        mockRepo.Setup(r => r.GetByIdAsync("1", It.IsAny<CancellationToken>()))
            .ReturnsAsync(paper);
        mockRepo.Setup(r => r.UpdateAsync(It.IsAny<Paper>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((Paper p, CancellationToken _) => p);

        var useCase = new UpdatePaperMetaUseCase(mockRepo.Object);

        // Act
        var result = await useCase.ExecuteAsync("1", new UpdatePaperMetaRequest
        {
            Title = "New Title"
        });

        // Assert
        Assert.NotNull(result);
        Assert.Equal("New Title", result.Title);
    }

    [Fact]
    public async Task ExecuteAsync_ShouldReturnNull_WhenPaperNotFound()
    {
        // Arrange
        var mockRepo = new Mock<IPaperRepository>();
        mockRepo.Setup(r => r.GetByIdAsync("1", It.IsAny<CancellationToken>()))
            .ReturnsAsync((Paper?)null);

        var useCase = new UpdatePaperMetaUseCase(mockRepo.Object);

        // Act
        var result = await useCase.ExecuteAsync("1", new UpdatePaperMetaRequest { Title = "New Title" });

        // Assert
        Assert.Null(result);
    }
}

public class HighlightUseCasesTests
{
    [Fact]
    public async Task GetHighlightsAsync_ShouldReturnHighlightList()
    {
        // Arrange
        var mockRepo = new Mock<IHighlightRepository>();
        var highlights = new List<Highlight>
        {
            new()
            {
                Id = "h1",
                PaperId = "p1",
                UserId = "u1",
                ParagraphId = "para1",
                StartOffset = 0,
                EndOffset = 10,
                Color = "#FFEB3B",
                CreatedAt = DateTime.UtcNow
            }
        };
        mockRepo.Setup(r => r.GetByPaperIdAsync("p1", "u1", It.IsAny<CancellationToken>()))
            .ReturnsAsync(highlights);

        var useCase = new HighlightUseCases(mockRepo.Object);

        // Act
        var result = await useCase.GetHighlightsAsync("p1", "u1");

        // Assert
        Assert.NotNull(result);
        Assert.Single(result.Highlights);
        Assert.Equal("#FFEB3B", result.Highlights[0].Color);
    }

    [Fact]
    public async Task CreateHighlightAsync_ShouldCreateHighlight()
    {
        // Arrange
        var mockRepo = new Mock<IHighlightRepository>();
        mockRepo.Setup(r => r.CreateAsync(It.IsAny<Highlight>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((Highlight h, CancellationToken _) => h);

        var useCase = new HighlightUseCases(mockRepo.Object);

        // Act
        var result = await useCase.CreateHighlightAsync("p1", "u1", new CreateHighlightRequest
        {
            ParagraphId = "para1",
            StartOffset = 0,
            EndOffset = 10,
            Color = "#FF0000"
        });

        // Assert
        Assert.NotNull(result);
        Assert.Equal("p1", result.PaperId);
        Assert.Equal("#FF0000", result.Color);
    }
}

