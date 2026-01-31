namespace SuperSuat.Domain.Entities;

public class Paper
{
    public string Id { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public List<string> Authors { get; set; } = [];
    public string Description { get; set; } = string.Empty;
    public List<string> Tags { get; set; } = [];
    public string? OriginalUrl { get; set; }
    public string? PdfUrl { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
}
