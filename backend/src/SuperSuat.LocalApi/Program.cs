using SuperSuat.Application.DTOs;
using SuperSuat.Application.Interfaces;
using SuperSuat.Application.UseCases;
using SuperSuat.Infrastructure;
using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);

// Add services
builder.Services.AddInfrastructure();
builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyMethod()
              .AllowAnyHeader();
    });
});

var app = builder.Build();

app.UseCors();

var jsonOptions = new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };

// For local development, bypass auth
string GetUserId() => "local-user";

// Papers API
app.MapGet("/papers", async (HttpContext ctx, GetPaperListUseCase useCase) =>
{
    var filter = new PaperFilter
    {
        PageSize = int.TryParse(ctx.Request.Query["pageSize"], out var ps) ? ps : 20,
        NextToken = ctx.Request.Query["nextToken"].FirstOrDefault()
    };
    var result = await useCase.ExecuteAsync(filter);
    return Results.Ok(result);
});

app.MapGet("/papers/{paperId}", async (string paperId, GetPaperDetailUseCase useCase) =>
{
    var result = await useCase.ExecuteAsync(paperId);
    return result == null ? Results.NotFound() : Results.Ok(result);
});

app.MapPost("/papers", async (HttpRequest request, UploadPaperUseCase useCase) =>
{
    using var ms = new MemoryStream();
    await request.Body.CopyToAsync(ms);
    var pdfData = ms.ToArray();
    var paper = await useCase.ExecuteAsync(pdfData, new ProcessingOptions());
    return Results.Created($"/papers/{paper.Id}", paper);
});

app.MapPut("/papers/{paperId}", async (string paperId, UpdatePaperMetaRequest req, UpdatePaperMetaUseCase useCase) =>
{
    var result = await useCase.ExecuteAsync(paperId, req);
    return result == null ? Results.NotFound() : Results.Ok(result);
});

// Translations API
app.MapGet("/papers/{paperId}/translations/languages", async (string paperId, TranslationUseCases useCase) =>
{
    var result = await useCase.GetAvailableLanguagesAsync(paperId);
    return Results.Ok(result);
});

app.MapGet("/papers/{paperId}/translations/{language}", async (string paperId, string language, TranslationUseCases useCase) =>
{
    var result = await useCase.GetTranslationAsync(paperId, language);
    return result == null ? Results.NotFound() : Results.Ok(result);
});

app.MapPost("/papers/{paperId}/translations", async (string paperId, CreateTranslationRequest req, TranslationUseCases useCase) =>
{
    var result = await useCase.CreateTranslationAsync(paperId, req);
    return result == null ? Results.NotFound() : Results.Created($"/papers/{paperId}/translations/{req.Language}", result);
});

// Summaries API
app.MapGet("/papers/{paperId}/summaries/{language}", async (string paperId, string language, SummaryUseCases useCase) =>
{
    var result = await useCase.GetSummaryAsync(paperId, language);
    return result == null ? Results.NotFound() : Results.Ok(result);
});

app.MapPost("/papers/{paperId}/summaries", async (string paperId, CreateSummaryRequest req, SummaryUseCases useCase) =>
{
    var result = await useCase.CreateSummaryAsync(paperId, req);
    return result == null ? Results.NotFound() : Results.Created($"/papers/{paperId}/summaries/{req.Language}", result);
});

// Highlights API
app.MapGet("/papers/{paperId}/highlights", async (string paperId, HighlightUseCases useCase) =>
{
    var result = await useCase.GetHighlightsAsync(paperId, GetUserId());
    return Results.Ok(result);
});

app.MapPost("/papers/{paperId}/highlights", async (string paperId, CreateHighlightRequest req, HighlightUseCases useCase) =>
{
    var result = await useCase.CreateHighlightAsync(paperId, GetUserId(), req);
    return Results.Created($"/papers/{paperId}/highlights/{result.Id}", result);
});

app.MapPut("/papers/{paperId}/highlights/{highlightId}", async (string paperId, string highlightId, UpdateHighlightRequest req, HighlightUseCases useCase) =>
{
    var result = await useCase.UpdateHighlightAsync(highlightId, GetUserId(), req);
    return result == null ? Results.NotFound() : Results.Ok(result);
});

app.MapDelete("/papers/{paperId}/highlights/{highlightId}", async (string paperId, string highlightId, HighlightUseCases useCase) =>
{
    await useCase.DeleteHighlightAsync(highlightId, GetUserId(), paperId);
    return Results.NoContent();
});

// Highlight Presets API
app.MapGet("/highlight-presets", async (HighlightPresetUseCases useCase) =>
{
    var result = await useCase.GetPresetsAsync(GetUserId());
    return Results.Ok(result);
});

app.MapPost("/highlight-presets", async (CreatePresetRequest req, HighlightPresetUseCases useCase) =>
{
    var result = await useCase.CreatePresetAsync(GetUserId(), req);
    return Results.Created($"/highlight-presets/{result.Id}", result);
});

app.MapPut("/highlight-presets/{presetId}", async (string presetId, UpdatePresetRequest req, HighlightPresetUseCases useCase) =>
{
    var result = await useCase.UpdatePresetAsync(presetId, GetUserId(), req);
    return result == null ? Results.NotFound() : Results.Ok(result);
});

app.MapDelete("/highlight-presets/{presetId}", async (string presetId, HighlightPresetUseCases useCase) =>
{
    await useCase.DeletePresetAsync(presetId, GetUserId());
    return Results.NoContent();
});

app.MapPut("/highlight-presets/{presetId}/default", async (string presetId, HighlightPresetUseCases useCase) =>
{
    var result = await useCase.SetDefaultPresetAsync(presetId, GetUserId());
    return result == null ? Results.NotFound() : Results.Ok(result);
});

// Chat API
app.MapPost("/papers/{paperId}/chat", async (string paperId, ChatRequest req, ChatUseCase useCase) =>
{
    var result = await useCase.ExecuteAsync(paperId, req);
    return result == null ? Results.NotFound() : Results.Ok(result);
});

// Health check
app.MapGet("/health", () => Results.Ok(new { status = "healthy" }));

app.Run();
