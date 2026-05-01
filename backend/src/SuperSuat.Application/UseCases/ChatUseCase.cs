using SuperSuat.Application.DTOs;
using SuperSuat.Application.Interfaces;

namespace SuperSuat.Application.UseCases;

public class ChatUseCase
{
    private readonly ITextContentRepository _textContentRepository;
    private readonly ILlmService _llmService;

    public ChatUseCase(
        ITextContentRepository textContentRepository,
        ILlmService llmService)
    {
        _textContentRepository = textContentRepository;
        _llmService = llmService;
    }

    public async Task<ChatResponse?> ExecuteAsync(string paperId, ChatRequest request, CancellationToken cancellationToken = default)
    {
        // Get text content for context
        var textContent = await _textContentRepository.GetByPaperIdAsync(paperId, cancellationToken);
        if (textContent == null) return null;

        // Build context from text content
        var context = BuildContext(textContent);

        // Send to LLM
        var response = await _llmService.ChatAsync(context, request.Message, cancellationToken);

        return new ChatResponse { Message = response };
    }

    private static string BuildContext(Domain.Entities.TextContent content)
    {
        var builder = new System.Text.StringBuilder();
        builder.AppendLine("Paper content:");
        builder.AppendLine();

        foreach (var section in content.Sections.OrderBy(s => s.Order))
        {
            builder.AppendLine($"## {section.Title}");
            builder.AppendLine();

            foreach (var paragraph in section.Paragraphs.OrderBy(p => p.Order))
            {
                builder.AppendLine(paragraph.Content);
                builder.AppendLine();
            }
        }

        return builder.ToString();
    }
}
