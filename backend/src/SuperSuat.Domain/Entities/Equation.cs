namespace SuperSuat.Domain.Entities;

public class Equation
{
    public string Id { get; set; } = string.Empty;
    public string PaperId { get; set; } = string.Empty;
    public string LatexContent { get; set; } = string.Empty;
    public int Order { get; set; }
}
