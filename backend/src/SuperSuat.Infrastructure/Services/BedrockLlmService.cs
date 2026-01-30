using Amazon.BedrockRuntime;
using Amazon.BedrockRuntime.Model;
using SuperSuat.Application.Interfaces;
using SuperSuat.Domain.Entities;
using SuperSuat.Domain.Enums;
using System.Text;
using System.Text.Json;

namespace SuperSuat.Infrastructure.Services;

public class BedrockLlmService : ILlmService
{
    private readonly IAmazonBedrockRuntime _bedrockRuntime;
    private readonly string _modelId;

    public BedrockLlmService(IAmazonBedrockRuntime bedrockRuntime, string modelId = "anthropic.claude-3-5-haiku-20241022-v1:0")
    {
        _bedrockRuntime = bedrockRuntime;
        _modelId = modelId;
    }

    public async Task<TextContent> ExtractTextAsync(byte[] pdfData, CancellationToken cancellationToken = default)
    {
        var pdfBase64 = Convert.ToBase64String(pdfData);

        var prompt = @"Extract the text content from this PDF document. 
Return the content as a structured JSON with sections and paragraphs.
For each paragraph, identify if it's regular text, an equation (return LaTeX), a figure reference, or a table reference.

Return JSON in this exact format:
{
    ""sections"": [
        {
            ""id"": ""sec-1"",
            ""title"": ""Section Title"",
            ""level"": 1,
            ""order"": 1,
            ""paragraphs"": [
                {
                    ""id"": ""para-1-1"",
                    ""content"": ""paragraph text or latex equation"",
                    ""order"": 1,
                    ""type"": ""Text""
                }
            ]
        }
    ]
}

Type can be: Text, Equation, FigureReference, TableReference";

        var response = await InvokeModelWithDocumentAsync(prompt, pdfBase64, "application/pdf", cancellationToken);

        try
        {
            // Extract JSON from response
            var jsonStart = response.IndexOf('{');
            var jsonEnd = response.LastIndexOf('}') + 1;
            if (jsonStart >= 0 && jsonEnd > jsonStart)
            {
                var json = response.Substring(jsonStart, jsonEnd - jsonStart);
                var result = JsonSerializer.Deserialize<TextContentExtraction>(json, new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true
                });

                if (result?.Sections != null)
                {
                    return new TextContent
                    {
                        Sections = result.Sections.Select(s => new Section
                        {
                            Id = s.Id ?? Guid.NewGuid().ToString(),
                            Title = s.Title ?? "",
                            Level = s.Level,
                            Order = s.Order,
                            Paragraphs = s.Paragraphs?.Select(p => new Paragraph
                            {
                                Id = p.Id ?? Guid.NewGuid().ToString(),
                                Content = p.Content ?? "",
                                Order = p.Order,
                                Type = Enum.TryParse<ParagraphType>(p.Type, true, out var type) ? type : ParagraphType.Text
                            }).ToList() ?? []
                        }).ToList()
                    };
                }
            }
        }
        catch (JsonException)
        {
            // If parsing fails, create a single section with the response as content
        }

        return new TextContent
        {
            Sections =
            [
                new Section
                {
                    Id = Guid.NewGuid().ToString(),
                    Title = "Content",
                    Level = 1,
                    Order = 1,
                    Paragraphs =
                    [
                        new Paragraph
                        {
                            Id = Guid.NewGuid().ToString(),
                            Content = response,
                            Order = 1,
                            Type = ParagraphType.Text
                        }
                    ]
                }
            ]
        };
    }

    public async Task<(Paper paper, List<Figure> figures, List<Table> tables, List<Equation> equations)> ExtractMetadataAndMediaAsync(
        byte[] pdfData, string paperId, CancellationToken cancellationToken = default)
    {
        var pdfBase64 = Convert.ToBase64String(pdfData);

        var prompt = @"Extract metadata, figures, tables, and equations from this PDF document.

Return JSON in this exact format:
{
    ""title"": ""Paper Title"",
    ""authors"": [""Author 1"", ""Author 2""],
    ""description"": ""A short description of the paper"",
    ""tags"": [""tag1"", ""tag2""],
    ""originalUrl"": ""https://..."",
    ""figures"": [
        {
            ""id"": ""fig-1"",
            ""caption"": ""Figure caption"",
            ""order"": 1
        }
    ],
    ""tables"": [
        {
            ""id"": ""tbl-1"",
            ""caption"": ""Table caption"",
            ""content"": ""markdown table content"",
            ""order"": 1
        }
    ],
    ""equations"": [
        {
            ""id"": ""eq-1"",
            ""latexContent"": ""\\frac{a}{b}"",
            ""order"": 1
        }
    ]
}";

        var response = await InvokeModelWithDocumentAsync(prompt, pdfBase64, "application/pdf", cancellationToken);

        try
        {
            var jsonStart = response.IndexOf('{');
            var jsonEnd = response.LastIndexOf('}') + 1;
            if (jsonStart >= 0 && jsonEnd > jsonStart)
            {
                var json = response.Substring(jsonStart, jsonEnd - jsonStart);
                var result = JsonSerializer.Deserialize<MetadataExtraction>(json, new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true
                });

                if (result != null)
                {
                    var paper = new Paper
                    {
                        Id = paperId,
                        Title = result.Title ?? "Untitled",
                        Authors = result.Authors ?? [],
                        Description = result.Description ?? "",
                        Tags = result.Tags ?? [],
                        OriginalUrl = result.OriginalUrl
                    };

                    var figures = result.Figures?.Select(f => new Figure
                    {
                        Id = f.Id ?? Guid.NewGuid().ToString(),
                        PaperId = paperId,
                        Caption = f.Caption ?? "",
                        ImageUrl = "", // Will be set later if image extraction is needed
                        Order = f.Order
                    }).ToList() ?? [];

                    var tables = result.Tables?.Select(t => new Table
                    {
                        Id = t.Id ?? Guid.NewGuid().ToString(),
                        PaperId = paperId,
                        Caption = t.Caption ?? "",
                        Content = t.Content ?? "",
                        Order = t.Order
                    }).ToList() ?? [];

                    var equations = result.Equations?.Select(e => new Equation
                    {
                        Id = e.Id ?? Guid.NewGuid().ToString(),
                        PaperId = paperId,
                        LatexContent = e.LatexContent ?? "",
                        Order = e.Order
                    }).ToList() ?? [];

                    return (paper, figures, tables, equations);
                }
            }
        }
        catch (JsonException)
        {
            // Continue with defaults
        }

        return (new Paper { Id = paperId, Title = "Untitled" }, [], [], []);
    }

    public async Task<Translation> TranslateAsync(TextContent content, string paperId, string targetLanguage, CancellationToken cancellationToken = default)
    {
        var contentJson = JsonSerializer.Serialize(content.Sections);

        var prompt = $@"Translate the following paper content to {targetLanguage}.
Keep the same structure and return JSON with translated titles and paragraphs.

Original content:
{contentJson}

Return JSON in this exact format:
{{
    ""sections"": [
        {{
            ""sectionId"": ""original-section-id"",
            ""translatedTitle"": ""Translated title"",
            ""paragraphs"": [
                {{
                    ""paragraphId"": ""original-paragraph-id"",
                    ""translatedContent"": ""Translated content""
                }}
            ]
        }}
    ]
}}";

        var response = await InvokeModelAsync(prompt, cancellationToken);

        try
        {
            var jsonStart = response.IndexOf('{');
            var jsonEnd = response.LastIndexOf('}') + 1;
            if (jsonStart >= 0 && jsonEnd > jsonStart)
            {
                var json = response.Substring(jsonStart, jsonEnd - jsonStart);
                var result = JsonSerializer.Deserialize<TranslationExtraction>(json, new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true
                });

                if (result?.Sections != null)
                {
                    return new Translation
                    {
                        Id = Guid.NewGuid().ToString(),
                        PaperId = paperId,
                        Language = targetLanguage,
                        Sections = result.Sections.Select(s => new TranslatedSection
                        {
                            SectionId = s.SectionId ?? "",
                            TranslatedTitle = s.TranslatedTitle ?? "",
                            Paragraphs = s.Paragraphs?.Select(p => new TranslatedParagraph
                            {
                                ParagraphId = p.ParagraphId ?? "",
                                TranslatedContent = p.TranslatedContent ?? ""
                            }).ToList() ?? []
                        }).ToList(),
                        CreatedAt = DateTime.UtcNow
                    };
                }
            }
        }
        catch (JsonException)
        {
            // Continue with empty translation
        }

        return new Translation
        {
            Id = Guid.NewGuid().ToString(),
            PaperId = paperId,
            Language = targetLanguage,
            Sections = [],
            CreatedAt = DateTime.UtcNow
        };
    }

    public async Task<Summary> SummarizeAsync(TextContent content, string paperId, SummaryOptions options, CancellationToken cancellationToken = default)
    {
        var contentText = BuildTextFromContent(content);

        var prompt = options.IncludeChapterSummaries
            ? $@"Summarize the following paper in {options.Language}. Provide both an overall summary and chapter-by-chapter summaries.

Paper content:
{contentText}

Return JSON in this exact format:
{{
    ""wholeSummary"": ""Overall summary of the paper"",
    ""chapterSummaries"": [
        {{
            ""sectionId"": ""section-id"",
            ""summary"": ""Summary of this section""
        }}
    ]
}}"
            : $@"Summarize the following paper in {options.Language}.

Paper content:
{contentText}

Return JSON in this exact format:
{{
    ""wholeSummary"": ""Overall summary of the paper""
}}";

        var response = await InvokeModelAsync(prompt, cancellationToken);

        try
        {
            var jsonStart = response.IndexOf('{');
            var jsonEnd = response.LastIndexOf('}') + 1;
            if (jsonStart >= 0 && jsonEnd > jsonStart)
            {
                var json = response.Substring(jsonStart, jsonEnd - jsonStart);
                var result = JsonSerializer.Deserialize<SummaryExtraction>(json, new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true
                });

                if (result != null)
                {
                    return new Summary
                    {
                        Id = Guid.NewGuid().ToString(),
                        PaperId = paperId,
                        Language = options.Language,
                        WholeSummary = result.WholeSummary ?? "",
                        ChapterSummaries = result.ChapterSummaries?.Select(c => new ChapterSummary
                        {
                            SectionId = c.SectionId ?? "",
                            Summary = c.Summary ?? ""
                        }).ToList() ?? [],
                        CreatedAt = DateTime.UtcNow
                    };
                }
            }
        }
        catch (JsonException)
        {
            // Continue with response as summary
        }

        return new Summary
        {
            Id = Guid.NewGuid().ToString(),
            PaperId = paperId,
            Language = options.Language,
            WholeSummary = response,
            ChapterSummaries = [],
            CreatedAt = DateTime.UtcNow
        };
    }

    public async Task<string> ChatAsync(string paperContext, string message, CancellationToken cancellationToken = default)
    {
        var prompt = $@"You are a helpful assistant answering questions about a research paper.
Here is the paper content:

{paperContext}

User question: {message}

Please provide a helpful and accurate answer based on the paper content.";

        return await InvokeModelAsync(prompt, cancellationToken);
    }

    private async Task<string> InvokeModelAsync(string prompt, CancellationToken cancellationToken)
    {
        var payload = new
        {
            anthropic_version = "bedrock-2023-05-31",
            max_tokens = 4096,
            messages = new[]
            {
                new
                {
                    role = "user",
                    content = prompt
                }
            }
        };

        var request = new InvokeModelRequest
        {
            ModelId = _modelId,
            ContentType = "application/json",
            Accept = "application/json",
            Body = new MemoryStream(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(payload)))
        };

        var response = await _bedrockRuntime.InvokeModelAsync(request, cancellationToken);

        using var reader = new StreamReader(response.Body);
        var responseJson = await reader.ReadToEndAsync(cancellationToken);
        var responseObj = JsonSerializer.Deserialize<BedrockResponse>(responseJson);

        return responseObj?.Content?.FirstOrDefault()?.Text ?? "";
    }

    private async Task<string> InvokeModelWithDocumentAsync(string prompt, string documentBase64, string mediaType, CancellationToken cancellationToken)
    {
        var payload = new
        {
            anthropic_version = "bedrock-2023-05-31",
            max_tokens = 8192,
            messages = new[]
            {
                new
                {
                    role = "user",
                    content = new object[]
                    {
                        new
                        {
                            type = "document",
                            source = new
                            {
                                type = "base64",
                                media_type = mediaType,
                                data = documentBase64
                            }
                        },
                        new
                        {
                            type = "text",
                            text = prompt
                        }
                    }
                }
            }
        };

        var request = new InvokeModelRequest
        {
            ModelId = _modelId,
            ContentType = "application/json",
            Accept = "application/json",
            Body = new MemoryStream(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(payload)))
        };

        var response = await _bedrockRuntime.InvokeModelAsync(request, cancellationToken);

        using var reader = new StreamReader(response.Body);
        var responseJson = await reader.ReadToEndAsync(cancellationToken);
        var responseObj = JsonSerializer.Deserialize<BedrockResponse>(responseJson);

        return responseObj?.Content?.FirstOrDefault()?.Text ?? "";
    }

    private static string BuildTextFromContent(TextContent content)
    {
        var sb = new StringBuilder();
        foreach (var section in content.Sections.OrderBy(s => s.Order))
        {
            sb.AppendLine($"## {section.Title}");
            foreach (var para in section.Paragraphs.OrderBy(p => p.Order))
            {
                sb.AppendLine(para.Content);
            }
            sb.AppendLine();
        }
        return sb.ToString();
    }

    // Internal classes for JSON deserialization
    private class BedrockResponse
    {
        public List<ContentItem>? Content { get; set; }
    }

    private class ContentItem
    {
        public string? Text { get; set; }
    }

    private class TextContentExtraction
    {
        public List<SectionExtraction>? Sections { get; set; }
    }

    private class SectionExtraction
    {
        public string? Id { get; set; }
        public string? Title { get; set; }
        public int Level { get; set; }
        public int Order { get; set; }
        public List<ParagraphExtraction>? Paragraphs { get; set; }
    }

    private class ParagraphExtraction
    {
        public string? Id { get; set; }
        public string? Content { get; set; }
        public int Order { get; set; }
        public string? Type { get; set; }
    }

    private class MetadataExtraction
    {
        public string? Title { get; set; }
        public List<string>? Authors { get; set; }
        public string? Description { get; set; }
        public List<string>? Tags { get; set; }
        public string? OriginalUrl { get; set; }
        public List<FigureExtraction>? Figures { get; set; }
        public List<TableExtraction>? Tables { get; set; }
        public List<EquationExtraction>? Equations { get; set; }
    }

    private class FigureExtraction
    {
        public string? Id { get; set; }
        public string? Caption { get; set; }
        public int Order { get; set; }
    }

    private class TableExtraction
    {
        public string? Id { get; set; }
        public string? Caption { get; set; }
        public string? Content { get; set; }
        public int Order { get; set; }
    }

    private class EquationExtraction
    {
        public string? Id { get; set; }
        public string? LatexContent { get; set; }
        public int Order { get; set; }
    }

    private class TranslationExtraction
    {
        public List<TranslatedSectionExtraction>? Sections { get; set; }
    }

    private class TranslatedSectionExtraction
    {
        public string? SectionId { get; set; }
        public string? TranslatedTitle { get; set; }
        public List<TranslatedParagraphExtraction>? Paragraphs { get; set; }
    }

    private class TranslatedParagraphExtraction
    {
        public string? ParagraphId { get; set; }
        public string? TranslatedContent { get; set; }
    }

    private class SummaryExtraction
    {
        public string? WholeSummary { get; set; }
        public List<ChapterSummaryExtraction>? ChapterSummaries { get; set; }
    }

    private class ChapterSummaryExtraction
    {
        public string? SectionId { get; set; }
        public string? Summary { get; set; }
    }
}
