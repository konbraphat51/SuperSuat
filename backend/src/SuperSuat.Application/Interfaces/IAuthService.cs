namespace SuperSuat.Application.Interfaces;

public class UserClaims
{
    public string UserId { get; set; } = string.Empty;
    public string Email { get; set; } = string.Empty;
    public string? Name { get; set; }
}

public interface IAuthService
{
    Task<UserClaims?> ValidateTokenAsync(string token, CancellationToken cancellationToken = default);
    Task<string?> GetUserIdAsync(string token, CancellationToken cancellationToken = default);
}
