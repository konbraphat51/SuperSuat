using Amazon.DynamoDBv2;
using Amazon.DynamoDBv2.Model;
using SuperSuat.Application.Interfaces;
using SuperSuat.Domain.Entities;

namespace SuperSuat.Infrastructure.Repositories;

public class DynamoDbHighlightColorPresetRepository : IHighlightColorPresetRepository
{
    private readonly IAmazonDynamoDB _dynamoDb;
    private readonly string _tableName;

    public DynamoDbHighlightColorPresetRepository(IAmazonDynamoDB dynamoDb, string tableName = "supersuat-highlight-presets")
    {
        _dynamoDb = dynamoDb;
        _tableName = tableName;
    }

    public async Task<List<HighlightColorPreset>> GetByUserIdAsync(string userId, CancellationToken cancellationToken = default)
    {
        var request = new QueryRequest
        {
            TableName = _tableName,
            KeyConditionExpression = "PK = :pk",
            ExpressionAttributeValues = new Dictionary<string, AttributeValue>
            {
                { ":pk", new AttributeValue { S = $"USER#{userId}" } }
            }
        };

        var response = await _dynamoDb.QueryAsync(request, cancellationToken);
        return response.Items.Select(MapToPreset).ToList();
    }

    public async Task<HighlightColorPreset?> GetByIdAsync(string id, string userId, CancellationToken cancellationToken = default)
    {
        var request = new GetItemRequest
        {
            TableName = _tableName,
            Key = new Dictionary<string, AttributeValue>
            {
                { "PK", new AttributeValue { S = $"USER#{userId}" } },
                { "SK", new AttributeValue { S = $"PRESET#{id}" } }
            }
        };

        var response = await _dynamoDb.GetItemAsync(request, cancellationToken);
        if (!response.IsItemSet)
            return null;

        return MapToPreset(response.Item);
    }

    public async Task<HighlightColorPreset> CreateAsync(HighlightColorPreset preset, CancellationToken cancellationToken = default)
    {
        var item = new Dictionary<string, AttributeValue>
        {
            { "PK", new AttributeValue { S = $"USER#{preset.UserId}" } },
            { "SK", new AttributeValue { S = $"PRESET#{preset.Id}" } },
            { "presetId", new AttributeValue { S = preset.Id } },
            { "userId", new AttributeValue { S = preset.UserId } },
            { "name", new AttributeValue { S = preset.Name } },
            { "color", new AttributeValue { S = preset.Color } },
            { "isDefault", new AttributeValue { BOOL = preset.IsDefault } },
            { "createdAt", new AttributeValue { S = preset.CreatedAt.ToString("O") } }
        };

        var request = new PutItemRequest
        {
            TableName = _tableName,
            Item = item
        };

        await _dynamoDb.PutItemAsync(request, cancellationToken);
        return preset;
    }

    public async Task<HighlightColorPreset> UpdateAsync(HighlightColorPreset preset, CancellationToken cancellationToken = default)
    {
        return await CreateAsync(preset, cancellationToken);
    }

    public async Task DeleteAsync(string id, string userId, CancellationToken cancellationToken = default)
    {
        var request = new DeleteItemRequest
        {
            TableName = _tableName,
            Key = new Dictionary<string, AttributeValue>
            {
                { "PK", new AttributeValue { S = $"USER#{userId}" } },
                { "SK", new AttributeValue { S = $"PRESET#{id}" } }
            }
        };

        await _dynamoDb.DeleteItemAsync(request, cancellationToken);
    }

    public async Task ClearDefaultAsync(string userId, CancellationToken cancellationToken = default)
    {
        var presets = await GetByUserIdAsync(userId, cancellationToken);
        foreach (var preset in presets.Where(p => p.IsDefault))
        {
            preset.IsDefault = false;
            await UpdateAsync(preset, cancellationToken);
        }
    }

    private static HighlightColorPreset MapToPreset(Dictionary<string, AttributeValue> item)
    {
        return new HighlightColorPreset
        {
            Id = item["presetId"].S,
            UserId = item["userId"].S,
            Name = item["name"].S,
            Color = item["color"].S,
            IsDefault = item["isDefault"].BOOL ?? false,
            CreatedAt = DateTime.Parse(item["createdAt"].S)
        };
    }
}
