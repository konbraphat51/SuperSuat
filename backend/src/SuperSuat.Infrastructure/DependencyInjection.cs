using Amazon.BedrockRuntime;
using Amazon.CognitoIdentityProvider;
using Amazon.DynamoDBv2;
using Amazon.S3;
using Microsoft.Extensions.DependencyInjection;
using SuperSuat.Application.Interfaces;
using SuperSuat.Application.UseCases;
using SuperSuat.Infrastructure.Repositories;
using SuperSuat.Infrastructure.Services;

namespace SuperSuat.Infrastructure;

public static class DependencyInjection
{
    public static IServiceCollection AddInfrastructure(this IServiceCollection services, InfrastructureOptions? options = null)
    {
        options ??= new InfrastructureOptions();

        // AWS Clients
        services.AddSingleton<IAmazonDynamoDB>(_ => new AmazonDynamoDBClient());
        services.AddSingleton<IAmazonS3>(_ => new AmazonS3Client());
        services.AddSingleton<IAmazonBedrockRuntime>(_ => new AmazonBedrockRuntimeClient());
        services.AddSingleton<IAmazonCognitoIdentityProvider>(_ => new AmazonCognitoIdentityProviderClient());

        // Repositories
        services.AddSingleton<IPaperRepository>(sp =>
            new DynamoDbPaperRepository(sp.GetRequiredService<IAmazonDynamoDB>(), options.PapersTableName));
        services.AddSingleton<ITextContentRepository>(sp =>
            new DynamoDbTextContentRepository(sp.GetRequiredService<IAmazonDynamoDB>(), options.PapersTableName));
        services.AddSingleton<IFigureRepository>(sp =>
            new DynamoDbFigureRepository(sp.GetRequiredService<IAmazonDynamoDB>(), options.PapersTableName));
        services.AddSingleton<ITableRepository>(sp =>
            new DynamoDbTableRepository(sp.GetRequiredService<IAmazonDynamoDB>(), options.PapersTableName));
        services.AddSingleton<IEquationRepository>(sp =>
            new DynamoDbEquationRepository(sp.GetRequiredService<IAmazonDynamoDB>(), options.PapersTableName));
        services.AddSingleton<ITranslationRepository>(sp =>
            new DynamoDbTranslationRepository(sp.GetRequiredService<IAmazonDynamoDB>(), options.TranslationsTableName));
        services.AddSingleton<ISummaryRepository>(sp =>
            new DynamoDbSummaryRepository(sp.GetRequiredService<IAmazonDynamoDB>(), options.SummariesTableName));
        services.AddSingleton<IHighlightRepository>(sp =>
            new DynamoDbHighlightRepository(sp.GetRequiredService<IAmazonDynamoDB>(), options.HighlightsTableName));
        services.AddSingleton<IHighlightColorPresetRepository>(sp =>
            new DynamoDbHighlightColorPresetRepository(sp.GetRequiredService<IAmazonDynamoDB>(), options.HighlightPresetsTableName));

        // Services
        services.AddSingleton<ILlmService>(sp =>
            new BedrockLlmService(sp.GetRequiredService<IAmazonBedrockRuntime>(), options.BedrockModelId));
        services.AddSingleton<IStorageService>(sp =>
            new S3StorageService(sp.GetRequiredService<IAmazonS3>(), options.S3BucketName));
        services.AddSingleton<IAuthService>(sp =>
            new CognitoAuthService(sp.GetRequiredService<IAmazonCognitoIdentityProvider>(), options.CognitoUserPoolId));
        services.AddSingleton<IPdfProcessingService, PdfProcessingService>();

        // Use Cases
        services.AddSingleton<GetPaperListUseCase>();
        services.AddSingleton<GetPaperDetailUseCase>();
        services.AddSingleton<UploadPaperUseCase>();
        services.AddSingleton<UpdatePaperMetaUseCase>();
        services.AddSingleton<TranslationUseCases>();
        services.AddSingleton<SummaryUseCases>();
        services.AddSingleton<HighlightUseCases>();
        services.AddSingleton<HighlightPresetUseCases>();
        services.AddSingleton<ChatUseCase>();

        return services;
    }
}

public class InfrastructureOptions
{
    public string PapersTableName { get; set; } = Environment.GetEnvironmentVariable("PAPERS_TABLE") ?? "supersuat-papers";
    public string TranslationsTableName { get; set; } = Environment.GetEnvironmentVariable("TRANSLATIONS_TABLE") ?? "supersuat-translations";
    public string SummariesTableName { get; set; } = Environment.GetEnvironmentVariable("SUMMARIES_TABLE") ?? "supersuat-summaries";
    public string HighlightsTableName { get; set; } = Environment.GetEnvironmentVariable("HIGHLIGHTS_TABLE") ?? "supersuat-highlights";
    public string HighlightPresetsTableName { get; set; } = Environment.GetEnvironmentVariable("HIGHLIGHT_PRESETS_TABLE") ?? "supersuat-highlight-presets";
    public string S3BucketName { get; set; } = Environment.GetEnvironmentVariable("S3_BUCKET") ?? "supersuat-storage";
    public string BedrockModelId { get; set; } = Environment.GetEnvironmentVariable("BEDROCK_MODEL_ID") ?? "anthropic.claude-3-5-haiku-20241022-v1:0";
    public string CognitoUserPoolId { get; set; } = Environment.GetEnvironmentVariable("COGNITO_USER_POOL_ID") ?? "";
}
