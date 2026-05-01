using Amazon.Lambda.APIGatewayEvents;
using Amazon.Lambda.Core;
using Amazon.Lambda.Serialization.SystemTextJson;
using Microsoft.Extensions.DependencyInjection;
using SuperSuat.Api;
using SuperSuat.Application.DTOs;
using SuperSuat.Application.Interfaces;
using SuperSuat.Application.UseCases;
using SuperSuat.Infrastructure;
using System.Net;
using System.Text.Json;

[assembly: LambdaSerializer(typeof(DefaultLambdaJsonSerializer))]

namespace SuperSuat.Api.Functions;

public class PaperFunctions
{
    private readonly IServiceProvider _serviceProvider;
    private readonly JsonSerializerOptions _jsonOptions = new() { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };

    public PaperFunctions()
    {
        var services = new ServiceCollection();
        services.AddInfrastructure();
        _serviceProvider = services.BuildServiceProvider();
    }

    public async Task<APIGatewayProxyResponse> GetPapers(APIGatewayProxyRequest request, ILambdaContext context)
    {
        try
        {
            var userId = await GetUserIdFromRequest(request);
            if (userId == null)
                return Unauthorized();

            var useCase = _serviceProvider.GetRequiredService<GetPaperListUseCase>();

            var filter = new PaperFilter
            {
                PageSize = GetQueryInt(request, "pageSize", 20),
                NextToken = request.QueryStringParameters?.GetValueOrDefault("nextToken")
            };

            if (request.QueryStringParameters?.TryGetValue("tags", out var tags) == true)
                filter.Tags = tags.Split(',').ToList();

            if (request.QueryStringParameters?.TryGetValue("authors", out var authors) == true)
                filter.Authors = authors.Split(',').ToList();

            var result = await useCase.ExecuteAsync(filter);

            return Ok(result);
        }
        catch (Exception ex)
        {
            context.Logger.LogError($"Error in GetPapers: {ex}");
            return InternalError(ex.Message);
        }
    }

    public async Task<APIGatewayProxyResponse> GetPaper(APIGatewayProxyRequest request, ILambdaContext context)
    {
        try
        {
            var userId = await GetUserIdFromRequest(request);
            if (userId == null)
                return Unauthorized();

            var paperId = request.PathParameters["paperId"];
            var useCase = _serviceProvider.GetRequiredService<GetPaperDetailUseCase>();

            var result = await useCase.ExecuteAsync(paperId);

            if (result == null)
                return NotFound("Paper not found");

            return Ok(result);
        }
        catch (Exception ex)
        {
            context.Logger.LogError($"Error in GetPaper: {ex}");
            return InternalError(ex.Message);
        }
    }

    public async Task<APIGatewayProxyResponse> UploadPaper(APIGatewayProxyRequest request, ILambdaContext context)
    {
        try
        {
            var userId = await GetUserIdFromRequest(request);
            if (userId == null)
                return Unauthorized();

            var useCase = _serviceProvider.GetRequiredService<UploadPaperUseCase>();

            // Get PDF from base64 encoded body
            byte[] pdfData;
            if (request.IsBase64Encoded)
            {
                pdfData = Convert.FromBase64String(request.Body);
            }
            else
            {
                return BadRequest("PDF must be base64 encoded");
            }

            var options = new ProcessingOptions();
            var paper = await useCase.ExecuteAsync(pdfData, options);

            return Created(paper);
        }
        catch (Exception ex)
        {
            context.Logger.LogError($"Error in UploadPaper: {ex}");
            return InternalError(ex.Message);
        }
    }

    public async Task<APIGatewayProxyResponse> UpdatePaper(APIGatewayProxyRequest request, ILambdaContext context)
    {
        try
        {
            var userId = await GetUserIdFromRequest(request);
            if (userId == null)
                return Unauthorized();

            var paperId = request.PathParameters["paperId"];
            var updateRequest = JsonSerializer.Deserialize<UpdatePaperMetaRequest>(request.Body, _jsonOptions);

            if (updateRequest == null)
                return BadRequest("Invalid request body");

            var useCase = _serviceProvider.GetRequiredService<UpdatePaperMetaUseCase>();
            var result = await useCase.ExecuteAsync(paperId, updateRequest);

            if (result == null)
                return NotFound("Paper not found");

            return Ok(result);
        }
        catch (Exception ex)
        {
            context.Logger.LogError($"Error in UpdatePaper: {ex}");
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

    private static int GetQueryInt(APIGatewayProxyRequest request, string key, int defaultValue)
    {
        if (request.QueryStringParameters?.TryGetValue(key, out var value) == true &&
            int.TryParse(value, out var result))
            return result;
        return defaultValue;
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
