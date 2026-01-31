namespace SuperSuat.Domain.Entities;

public class Translation
{
    public string Id { get; set; } = string.Empty;
    public string PaperId { get; set; } = string.Empty;
    public string Language { get; set; } = string.Empty;
    public List<TranslatedSection> Sections { get; set; } = [];
    public DateTime CreatedAt { get; set; }
}

public class TranslatedSection
{
    public string SectionId { get; set; } = string.Empty;
    public string TranslatedTitle { get; set; } = string.Empty;
    public List<TranslatedParagraph> Paragraphs { get; set; } = [];
}

public class TranslatedParagraph
{
    public string ParagraphId { get; set; } = string.Empty;
    public string TranslatedContent { get; set; } = string.Empty;
}
