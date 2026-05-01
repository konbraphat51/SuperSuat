using SuperSuat.Domain.Entities;
using SuperSuat.Domain.Enums;

namespace SuperSuat.Domain.Tests;

public class PaperTests
{
    [Fact]
    public void Paper_ShouldInitializeWithDefaults()
    {
        var paper = new Paper();

        Assert.Empty(paper.Id);
        Assert.Empty(paper.Title);
        Assert.Empty(paper.Authors);
        Assert.Empty(paper.Description);
        Assert.Empty(paper.Tags);
    }

    [Fact]
    public void Paper_ShouldAllowSettingProperties()
    {
        var paper = new Paper
        {
            Id = "123",
            Title = "Test Paper",
            Authors = ["Author 1", "Author 2"],
            Description = "A test paper",
            Tags = ["AI", "ML"],
            OriginalUrl = "https://example.com",
            PdfUrl = "s3://bucket/paper.pdf",
            CreatedAt = new DateTime(2024, 1, 1),
            UpdatedAt = new DateTime(2024, 1, 2)
        };

        Assert.Equal("123", paper.Id);
        Assert.Equal("Test Paper", paper.Title);
        Assert.Equal(2, paper.Authors.Count);
        Assert.Equal("A test paper", paper.Description);
        Assert.Equal(2, paper.Tags.Count);
        Assert.Equal("https://example.com", paper.OriginalUrl);
        Assert.Equal("s3://bucket/paper.pdf", paper.PdfUrl);
    }
}

public class TextContentTests
{
    [Fact]
    public void TextContent_ShouldInitializeWithDefaults()
    {
        var content = new TextContent();

        Assert.Empty(content.Id);
        Assert.Empty(content.PaperId);
        Assert.Empty(content.Sections);
    }

    [Fact]
    public void Section_ShouldContainParagraphs()
    {
        var section = new Section
        {
            Id = "sec-1",
            Title = "Introduction",
            Level = 1,
            Order = 1,
            Paragraphs =
            [
                new Paragraph
                {
                    Id = "para-1",
                    Content = "First paragraph",
                    Order = 1,
                    Type = ParagraphType.Text
                },
                new Paragraph
                {
                    Id = "para-2",
                    Content = "\\frac{a}{b}",
                    Order = 2,
                    Type = ParagraphType.Equation
                }
            ]
        };

        Assert.Equal("Introduction", section.Title);
        Assert.Equal(2, section.Paragraphs.Count);
        Assert.Equal(ParagraphType.Text, section.Paragraphs[0].Type);
        Assert.Equal(ParagraphType.Equation, section.Paragraphs[1].Type);
    }
}

public class HighlightTests
{
    [Fact]
    public void Highlight_ShouldStoreOffsets()
    {
        var highlight = new Highlight
        {
            Id = "h1",
            PaperId = "p1",
            UserId = "u1",
            ParagraphId = "para1",
            StartOffset = 10,
            EndOffset = 50,
            Color = "#FFEB3B",
            Note = "Important point"
        };

        Assert.Equal(10, highlight.StartOffset);
        Assert.Equal(50, highlight.EndOffset);
        Assert.Equal("#FFEB3B", highlight.Color);
        Assert.Equal("Important point", highlight.Note);
    }
}

public class TranslationTests
{
    [Fact]
    public void Translation_ShouldHaveLanguageAndSections()
    {
        var translation = new Translation
        {
            Id = "t1",
            PaperId = "p1",
            Language = "ja",
            Sections =
            [
                new TranslatedSection
                {
                    SectionId = "sec-1",
                    TranslatedTitle = "はじめに",
                    Paragraphs =
                    [
                        new TranslatedParagraph
                        {
                            ParagraphId = "para-1",
                            TranslatedContent = "翻訳されたテキスト"
                        }
                    ]
                }
            ]
        };

        Assert.Equal("ja", translation.Language);
        Assert.Single(translation.Sections);
        Assert.Equal("はじめに", translation.Sections[0].TranslatedTitle);
    }
}
