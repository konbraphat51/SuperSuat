namespace SuperSuat.Domain.Entities;

public class Summary
{
    public string Id { get; set; } = string.Empty;
    public string PaperId { get; set; } = string.Empty;
    public string Language { get; set; } = string.Empty;
    public string WholeSummary { get; set; } = string.Empty;
    public List<ChapterSummary> ChapterSummaries { get; set; } = [];
    public DateTime CreatedAt { get; set; }
}

public class ChapterSummary
{
    public string SectionId { get; set; } = string.Empty;
    public string Summary { get; set; } = string.Empty;
}
