using Amazon.DynamoDBv2;
using Amazon.DynamoDBv2.Model;
using SuperSuat.Application.Interfaces;
using SuperSuat.Domain.Entities;
using System.Text.Json;

namespace SuperSuat.Infrastructure.Repositories;

public class DynamoDbTranslationRepository : ITranslationRepository
{
    private readonly IAmazonDynamoDB _dynamoDb;
    private readonly string _tableName;

    public DynamoDbTranslationRepository(IAmazonDynamoDB dynamoDb, string tableName = "supersuat-translations")
    {
        _dynamoDb = dynamoDb;
        _tableName = tableName;
    }

    public async Task<Translation?> GetByPaperIdAndLanguageAsync(string paperId, string language, CancellationToken cancellationToken = default)
    {
        var request = new GetItemRequest
        {
            TableName = _tableName,
            Key = new Dictionary<string, AttributeValue>
            {
                { "PK", new AttributeValue { S = $"PAPER#{paperId}" } },
                { "SK", new AttributeValue { S = $"LANG#{language}" } }
            }
        };

        var response = await _dynamoDb.GetItemAsync(request, cancellationToken);
        if (!response.IsItemSet)
            return null;

        return MapToTranslation(response.Item);
    }

    public async Task<List<string>> GetAvailableLanguagesAsync(string paperId, CancellationToken cancellationToken = default)
    {
        var request = new QueryRequest
        {
            TableName = _tableName,
            KeyConditionExpression = "PK = :pk",
            ExpressionAttributeValues = new Dictionary<string, AttributeValue>
            {
                { ":pk", new AttributeValue { S = $"PAPER#{paperId}" } }
            },
            ProjectionExpression = "SK"
        };

        var response = await _dynamoDb.QueryAsync(request, cancellationToken);
        return response.Items
            .Select(i => i["SK"].S.Replace("LANG#", ""))
            .ToList();
    }

    public async Task<Translation> CreateAsync(Translation translation, CancellationToken cancellationToken = default)
    {
        var sectionsJson = JsonSerializer.Serialize(translation.Sections);

        var item = new Dictionary<string, AttributeValue>
        {
            { "PK", new AttributeValue { S = $"PAPER#{translation.PaperId}" } },
            { "SK", new AttributeValue { S = $"LANG#{translation.Language}" } },
            { "translationId", new AttributeValue { S = translation.Id } },
            { "paperId", new AttributeValue { S = translation.PaperId } },
            { "language", new AttributeValue { S = translation.Language } },
            { "sections", new AttributeValue { S = sectionsJson } },
            { "createdAt", new AttributeValue { S = translation.CreatedAt.ToString("O") } }
        };

        var request = new PutItemRequest
        {
            TableName = _tableName,
            Item = item
        };

        await _dynamoDb.PutItemAsync(request, cancellationToken);
        return translation;
    }

    private static Translation MapToTranslation(Dictionary<string, AttributeValue> item)
    {
        var sections = JsonSerializer.Deserialize<List<TranslatedSection>>(item["sections"].S) ?? [];

        return new Translation
        {
            Id = item["translationId"].S,
            PaperId = item["paperId"].S,
            Language = item["language"].S,
            Sections = sections,
            CreatedAt = DateTime.Parse(item["createdAt"].S)
        };
    }
}
