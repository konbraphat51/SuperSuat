namespace SuperSuat.Domain.Entities;

public class Figure
{
    public string Id { get; set; } = string.Empty;
    public string PaperId { get; set; } = string.Empty;
    public string Caption { get; set; } = string.Empty;
    public string ImageUrl { get; set; } = string.Empty;
    public int Order { get; set; }
}
