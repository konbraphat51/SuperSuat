using Amazon.Lambda.APIGatewayEvents;
using Amazon.Lambda.Core;
using Microsoft.Extensions.DependencyInjection;
using SuperSuat.Api;
using SuperSuat.Application.DTOs;
using SuperSuat.Application.Interfaces;
using SuperSuat.Application.UseCases;
using SuperSuat.Infrastructure;
using System.Net;
using System.Text.Json;

namespace SuperSuat.Api.Functions;

public class TranslationFunctions
{
    private readonly IServiceProvider _serviceProvider;
    private readonly JsonSerializerOptions _jsonOptions = new() { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };

    public TranslationFunctions()
    {
        var services = new ServiceCollection();
        services.AddInfrastructure();
        _serviceProvider = services.BuildServiceProvider();
    }

    public async Task<APIGatewayProxyResponse> GetAvailableLanguages(APIGatewayProxyRequest request, ILambdaContext context)
    {
        try
        {
            var userId = await GetUserIdFromRequest(request);
            if (userId == null)
                return Unauthorized();

            var paperId = request.PathParameters["paperId"];
            var useCase = _serviceProvider.GetRequiredService<TranslationUseCases>();

            var result = await useCase.GetAvailableLanguagesAsync(paperId);
            return Ok(result);
        }
        catch (Exception ex)
        {
            context.Logger.LogError($"Error in GetAvailableLanguages: {ex}");
            return InternalError(ex.Message);
        }
    }

    public async Task<APIGatewayProxyResponse> GetTranslation(APIGatewayProxyRequest request, ILambdaContext context)
    {
        try
        {
            var userId = await GetUserIdFromRequest(request);
            if (userId == null)
                return Unauthorized();

            var paperId = request.PathParameters["paperId"];
            var language = request.PathParameters["language"];
            var useCase = _serviceProvider.GetRequiredService<TranslationUseCases>();

            var result = await useCase.GetTranslationAsync(paperId, language);

            if (result == null)
                return NotFound("Translation not found");

            return Ok(result);
        }
        catch (Exception ex)
        {
            context.Logger.LogError($"Error in GetTranslation: {ex}");
            return InternalError(ex.Message);
        }
    }

    public async Task<APIGatewayProxyResponse> CreateTranslation(APIGatewayProxyRequest request, ILambdaContext context)
    {
        try
        {
            var userId = await GetUserIdFromRequest(request);
            if (userId == null)
                return Unauthorized();

            var paperId = request.PathParameters["paperId"];
            var createRequest = JsonSerializer.Deserialize<CreateTranslationRequest>(request.Body, _jsonOptions);

            if (createRequest == null)
                return BadRequest("Invalid request body");

            var useCase = _serviceProvider.GetRequiredService<TranslationUseCases>();
            var result = await useCase.CreateTranslationAsync(paperId, createRequest);

            if (result == null)
                return NotFound("Paper not found");

            return Created(result);
        }
        catch (Exception ex)
        {
            context.Logger.LogError($"Error in CreateTranslation: {ex}");
            return InternalError(ex.Message);
        }
    }

    private async Task<string?> GetUserIdFromRequest(APIGatewayProxyRequest request)
    {
        var token = request.Headers?.GetValueOrDefault("Authorization")?.Replace("Bearer ", "");
        if (string.IsNullOrEmpty(token))
            return null;

        var authService = _serviceProvider.GetRequiredService<IAuthService>();
        return await authService.GetUserIdAsync(token);
    }

    private APIGatewayProxyResponse Ok(object body) => new()
    {
        StatusCode = (int)HttpStatusCode.OK,
        Body = JsonSerializer.Serialize(body, _jsonOptions),
        Headers = new Dictionary<string, string>
        {
            { "Content-Type", "application/json" },
            { "Access-Control-Allow-Origin", "*" }
        }
    };

    private APIGatewayProxyResponse Created(object body) => new()
    {
        StatusCode = (int)HttpStatusCode.Created,
        Body = JsonSerializer.Serialize(body, _jsonOptions),
        Headers = new Dictionary<string, string>
        {
            { "Content-Type", "application/json" },
            { "Access-Control-Allow-Origin", "*" }
        }
    };

    private static APIGatewayProxyResponse Unauthorized() => new()
    {
        StatusCode = (int)HttpStatusCode.Unauthorized,
        Body = JsonSerializer.Serialize(new ErrorResponse { Error = "Unauthorized" }),
        Headers = new Dictionary<string, string>
        {
            { "Content-Type", "application/json" },
            { "Access-Control-Allow-Origin", "*" }
        }
    };

    private static APIGatewayProxyResponse NotFound(string message) => new()
    {
        StatusCode = (int)HttpStatusCode.NotFound,
        Body = JsonSerializer.Serialize(new ErrorResponse { Error = message }),
        Headers = new Dictionary<string, string>
        {
            { "Content-Type", "application/json" },
            { "Access-Control-Allow-Origin", "*" }
        }
    };

    private static APIGatewayProxyResponse BadRequest(string message) => new()
    {
        StatusCode = (int)HttpStatusCode.BadRequest,
        Body = JsonSerializer.Serialize(new ErrorResponse { Error = message }),
        Headers = new Dictionary<string, string>
        {
            { "Content-Type", "application/json" },
            { "Access-Control-Allow-Origin", "*" }
        }
    };

    private static APIGatewayProxyResponse InternalError(string message) => new()
    {
        StatusCode = (int)HttpStatusCode.InternalServerError,
        Body = JsonSerializer.Serialize(new ErrorResponse { Error = "Internal server error", Details = message }),
        Headers = new Dictionary<string, string>
        {
            { "Content-Type", "application/json" },
            { "Access-Control-Allow-Origin", "*" }
        }
    };
}
