using Amazon.DynamoDBv2;
using Amazon.DynamoDBv2.Model;
using SuperSuat.Application.Interfaces;
using SuperSuat.Domain.Entities;
using SuperSuat.Domain.Enums;
using System.Text.Json;

namespace SuperSuat.Infrastructure.Repositories;

public class DynamoDbTextContentRepository : ITextContentRepository
{
    private readonly IAmazonDynamoDB _dynamoDb;
    private readonly string _tableName;

    public DynamoDbTextContentRepository(IAmazonDynamoDB dynamoDb, string tableName = "supersuat-papers")
    {
        _dynamoDb = dynamoDb;
        _tableName = tableName;
    }

    public async Task<TextContent?> GetByPaperIdAsync(string paperId, CancellationToken cancellationToken = default)
    {
        var request = new GetItemRequest
        {
            TableName = _tableName,
            Key = new Dictionary<string, AttributeValue>
            {
                { "PK", new AttributeValue { S = $"PAPER#{paperId}" } },
                { "SK", new AttributeValue { S = "CONTENT" } }
            }
        };

        var response = await _dynamoDb.GetItemAsync(request, cancellationToken);
        if (!response.IsItemSet)
            return null;

        return MapToTextContent(response.Item);
    }

    public async Task<TextContent> CreateAsync(TextContent content, CancellationToken cancellationToken = default)
    {
        var sectionsJson = JsonSerializer.Serialize(content.Sections);

        var item = new Dictionary<string, AttributeValue>
        {
            { "PK", new AttributeValue { S = $"PAPER#{content.PaperId}" } },
            { "SK", new AttributeValue { S = "CONTENT" } },
            { "contentId", new AttributeValue { S = content.Id } },
            { "paperId", new AttributeValue { S = content.PaperId } },
            { "sections", new AttributeValue { S = sectionsJson } }
        };

        var request = new PutItemRequest
        {
            TableName = _tableName,
            Item = item
        };

        await _dynamoDb.PutItemAsync(request, cancellationToken);
        return content;
    }

    public async Task<TextContent> UpdateAsync(TextContent content, CancellationToken cancellationToken = default)
    {
        return await CreateAsync(content, cancellationToken);
    }

    private static TextContent MapToTextContent(Dictionary<string, AttributeValue> item)
    {
        var sections = JsonSerializer.Deserialize<List<Section>>(item["sections"].S) ?? [];

        return new TextContent
        {
            Id = item["contentId"].S,
            PaperId = item["paperId"].S,
            Sections = sections
        };
    }
}
