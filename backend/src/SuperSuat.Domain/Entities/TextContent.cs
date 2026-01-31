using SuperSuat.Domain.Enums;

namespace SuperSuat.Domain.Entities;

public class TextContent
{
    public string Id { get; set; } = string.Empty;
    public string PaperId { get; set; } = string.Empty;
    public List<Section> Sections { get; set; } = [];
}

public class Section
{
    public string Id { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public int Level { get; set; }
    public int Order { get; set; }
    public List<Paragraph> Paragraphs { get; set; } = [];
}

public class Paragraph
{
    public string Id { get; set; } = string.Empty;
    public string Content { get; set; } = string.Empty;
    public int Order { get; set; }
    public ParagraphType Type { get; set; }
}
