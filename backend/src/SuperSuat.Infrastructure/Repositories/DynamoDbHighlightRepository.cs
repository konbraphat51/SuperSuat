using Amazon.DynamoDBv2;
using Amazon.DynamoDBv2.Model;
using SuperSuat.Application.Interfaces;
using SuperSuat.Domain.Entities;

namespace SuperSuat.Infrastructure.Repositories;

public class DynamoDbHighlightRepository : IHighlightRepository
{
    private readonly IAmazonDynamoDB _dynamoDb;
    private readonly string _tableName;

    public DynamoDbHighlightRepository(IAmazonDynamoDB dynamoDb, string tableName = "supersuat-highlights")
    {
        _dynamoDb = dynamoDb;
        _tableName = tableName;
    }

    public async Task<List<Highlight>> GetByPaperIdAsync(string paperId, string userId, CancellationToken cancellationToken = default)
    {
        var request = new QueryRequest
        {
            TableName = _tableName,
            KeyConditionExpression = "PK = :pk",
            ExpressionAttributeValues = new Dictionary<string, AttributeValue>
            {
                { ":pk", new AttributeValue { S = $"USER#{userId}#PAPER#{paperId}" } }
            }
        };

        var response = await _dynamoDb.QueryAsync(request, cancellationToken);
        return response.Items.Select(MapToHighlight).ToList();
    }

    public async Task<Highlight?> GetByIdAsync(string id, string userId, CancellationToken cancellationToken = default)
    {
        // We need to scan since we don't have paperId
        var request = new ScanRequest
        {
            TableName = _tableName,
            FilterExpression = "highlightId = :id AND begins_with(PK, :userPrefix)",
            ExpressionAttributeValues = new Dictionary<string, AttributeValue>
            {
                { ":id", new AttributeValue { S = id } },
                { ":userPrefix", new AttributeValue { S = $"USER#{userId}#" } }
            }
        };

        var response = await _dynamoDb.ScanAsync(request, cancellationToken);
        if (response.Items.Count == 0)
            return null;

        return MapToHighlight(response.Items[0]);
    }

    public async Task<Highlight> CreateAsync(Highlight highlight, CancellationToken cancellationToken = default)
    {
        var item = new Dictionary<string, AttributeValue>
        {
            { "PK", new AttributeValue { S = $"USER#{highlight.UserId}#PAPER#{highlight.PaperId}" } },
            { "SK", new AttributeValue { S = $"HIGHLIGHT#{highlight.Id}" } },
            { "highlightId", new AttributeValue { S = highlight.Id } },
            { "paperId", new AttributeValue { S = highlight.PaperId } },
            { "userId", new AttributeValue { S = highlight.UserId } },
            { "paragraphId", new AttributeValue { S = highlight.ParagraphId } },
            { "startOffset", new AttributeValue { N = highlight.StartOffset.ToString() } },
            { "endOffset", new AttributeValue { N = highlight.EndOffset.ToString() } },
            { "color", new AttributeValue { S = highlight.Color } },
            { "createdAt", new AttributeValue { S = highlight.CreatedAt.ToString("O") } }
        };

        if (!string.IsNullOrEmpty(highlight.Note))
            item["note"] = new AttributeValue { S = highlight.Note };

        var request = new PutItemRequest
        {
            TableName = _tableName,
            Item = item
        };

        await _dynamoDb.PutItemAsync(request, cancellationToken);
        return highlight;
    }

    public async Task<Highlight> UpdateAsync(Highlight highlight, CancellationToken cancellationToken = default)
    {
        return await CreateAsync(highlight, cancellationToken);
    }

    public async Task DeleteAsync(string id, string userId, string paperId, CancellationToken cancellationToken = default)
    {
        var request = new DeleteItemRequest
        {
            TableName = _tableName,
            Key = new Dictionary<string, AttributeValue>
            {
                { "PK", new AttributeValue { S = $"USER#{userId}#PAPER#{paperId}" } },
                { "SK", new AttributeValue { S = $"HIGHLIGHT#{id}" } }
            }
        };

        await _dynamoDb.DeleteItemAsync(request, cancellationToken);
    }

    private static Highlight MapToHighlight(Dictionary<string, AttributeValue> item)
    {
        return new Highlight
        {
            Id = item["highlightId"].S,
            PaperId = item["paperId"].S,
            UserId = item["userId"].S,
            ParagraphId = item["paragraphId"].S,
            StartOffset = int.Parse(item["startOffset"].N),
            EndOffset = int.Parse(item["endOffset"].N),
            Color = item["color"].S,
            Note = item.TryGetValue("note", out var note) ? note.S : null,
            CreatedAt = DateTime.Parse(item["createdAt"].S)
        };
    }
}
