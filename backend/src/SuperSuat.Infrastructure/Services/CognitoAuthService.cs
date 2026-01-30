using Amazon.CognitoIdentityProvider;
using Amazon.CognitoIdentityProvider.Model;
using SuperSuat.Application.Interfaces;
using System.IdentityModel.Tokens.Jwt;

namespace SuperSuat.Infrastructure.Services;

public class CognitoAuthService : IAuthService
{
    private readonly IAmazonCognitoIdentityProvider _cognitoClient;
    private readonly string _userPoolId;

    public CognitoAuthService(IAmazonCognitoIdentityProvider cognitoClient, string userPoolId)
    {
        _cognitoClient = cognitoClient;
        _userPoolId = userPoolId;
    }

    public async Task<UserClaims?> ValidateTokenAsync(string token, CancellationToken cancellationToken = default)
    {
        try
        {
            // Decode the JWT token
            var handler = new JwtSecurityTokenHandler();
            if (!handler.CanReadToken(token))
                return null;

            var jwtToken = handler.ReadJwtToken(token);

            // Extract claims
            var userId = jwtToken.Claims.FirstOrDefault(c => c.Type == "sub")?.Value;
            var email = jwtToken.Claims.FirstOrDefault(c => c.Type == "email")?.Value;
            var name = jwtToken.Claims.FirstOrDefault(c => c.Type == "name")?.Value;

            if (string.IsNullOrEmpty(userId))
                return null;

            // Verify the token by getting user info (this validates the token is still valid)
            try
            {
                var request = new GetUserRequest
                {
                    AccessToken = token
                };

                var response = await _cognitoClient.GetUserAsync(request, cancellationToken);

                return new UserClaims
                {
                    UserId = userId,
                    Email = email ?? response.UserAttributes.FirstOrDefault(a => a.Name == "email")?.Value ?? "",
                    Name = name ?? response.UserAttributes.FirstOrDefault(a => a.Name == "name")?.Value
                };
            }
            catch (NotAuthorizedException)
            {
                return null;
            }
        }
        catch
        {
            return null;
        }
    }

    public async Task<string?> GetUserIdAsync(string token, CancellationToken cancellationToken = default)
    {
        var claims = await ValidateTokenAsync(token, cancellationToken);
        return claims?.UserId;
    }
}
