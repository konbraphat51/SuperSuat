using Amazon.DynamoDBv2;
using Amazon.DynamoDBv2.DocumentModel;
using Amazon.DynamoDBv2.Model;
using SuperSuat.Application.Interfaces;
using SuperSuat.Domain.Entities;
using System.Text.Json;

namespace SuperSuat.Infrastructure.Repositories;

public class DynamoDbPaperRepository : IPaperRepository
{
    private readonly IAmazonDynamoDB _dynamoDb;
    private readonly string _tableName;
    private static readonly JsonSerializerOptions JsonOptions = new() { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };

    public DynamoDbPaperRepository(IAmazonDynamoDB dynamoDb, string tableName = "supersuat-papers")
    {
        _dynamoDb = dynamoDb;
        _tableName = tableName;
    }

    public async Task<Paper?> GetByIdAsync(string id, CancellationToken cancellationToken = default)
    {
        var request = new GetItemRequest
        {
            TableName = _tableName,
            Key = new Dictionary<string, AttributeValue>
            {
                { "PK", new AttributeValue { S = $"PAPER#{id}" } },
                { "SK", new AttributeValue { S = "METADATA" } }
            }
        };

        var response = await _dynamoDb.GetItemAsync(request, cancellationToken);
        if (!response.IsItemSet)
            return null;

        return MapToPaper(response.Item);
    }

    public async Task<(List<Paper> Papers, string? NextToken)> GetAllAsync(PaperFilter filter, CancellationToken cancellationToken = default)
    {
        var request = new QueryRequest
        {
            TableName = _tableName,
            IndexName = "GSI1",
            KeyConditionExpression = "GSI1PK = :pk",
            ExpressionAttributeValues = new Dictionary<string, AttributeValue>
            {
                { ":pk", new AttributeValue { S = "PAPERS" } }
            },
            ScanIndexForward = false, // Newest first
            Limit = filter.PageSize
        };

        if (!string.IsNullOrEmpty(filter.NextToken))
        {
            request.ExclusiveStartKey = JsonSerializer.Deserialize<Dictionary<string, AttributeValue>>(
                Convert.FromBase64String(filter.NextToken));
        }

        var response = await _dynamoDb.QueryAsync(request, cancellationToken);

        var papers = response.Items.Select(MapToPaper).ToList();

        // Apply filters in memory (for simplicity; could be done with filter expressions)
        if (filter.Tags != null && filter.Tags.Count > 0)
        {
            papers = papers.Where(p => p.Tags.Any(t => filter.Tags.Contains(t))).ToList();
        }

        if (filter.Authors != null && filter.Authors.Count > 0)
        {
            papers = papers.Where(p => p.Authors.Any(a => filter.Authors.Contains(a))).ToList();
        }

        if (filter.FromDate.HasValue)
        {
            papers = papers.Where(p => p.CreatedAt >= filter.FromDate.Value).ToList();
        }

        if (filter.ToDate.HasValue)
        {
            papers = papers.Where(p => p.CreatedAt <= filter.ToDate.Value).ToList();
        }

        string? nextToken = null;
        if (response.LastEvaluatedKey != null && response.LastEvaluatedKey.Count > 0)
        {
            nextToken = Convert.ToBase64String(
                JsonSerializer.SerializeToUtf8Bytes(response.LastEvaluatedKey));
        }

        return (papers, nextToken);
    }

    public async Task<Paper> CreateAsync(Paper paper, CancellationToken cancellationToken = default)
    {
        var item = new Dictionary<string, AttributeValue>
        {
            { "PK", new AttributeValue { S = $"PAPER#{paper.Id}" } },
            { "SK", new AttributeValue { S = "METADATA" } },
            { "paperId", new AttributeValue { S = paper.Id } },
            { "title", new AttributeValue { S = paper.Title } },
            { "authors", new AttributeValue { L = paper.Authors.Select(a => new AttributeValue { S = a }).ToList() } },
            { "description", new AttributeValue { S = paper.Description } },
            { "tags", new AttributeValue { L = paper.Tags.Select(t => new AttributeValue { S = t }).ToList() } },
            { "createdAt", new AttributeValue { S = paper.CreatedAt.ToString("O") } },
            { "updatedAt", new AttributeValue { S = paper.UpdatedAt.ToString("O") } },
            { "GSI1PK", new AttributeValue { S = "PAPERS" } },
            { "GSI1SK", new AttributeValue { S = $"{paper.CreatedAt:O}#{paper.Id}" } }
        };

        if (!string.IsNullOrEmpty(paper.OriginalUrl))
            item["originalUrl"] = new AttributeValue { S = paper.OriginalUrl };

        if (!string.IsNullOrEmpty(paper.PdfUrl))
            item["pdfUrl"] = new AttributeValue { S = paper.PdfUrl };

        var request = new PutItemRequest
        {
            TableName = _tableName,
            Item = item
        };

        await _dynamoDb.PutItemAsync(request, cancellationToken);
        return paper;
    }

    public async Task<Paper> UpdateAsync(Paper paper, CancellationToken cancellationToken = default)
    {
        return await CreateAsync(paper, cancellationToken);
    }

    public async Task DeleteAsync(string id, CancellationToken cancellationToken = default)
    {
        var request = new DeleteItemRequest
        {
            TableName = _tableName,
            Key = new Dictionary<string, AttributeValue>
            {
                { "PK", new AttributeValue { S = $"PAPER#{id}" } },
                { "SK", new AttributeValue { S = "METADATA" } }
            }
        };

        await _dynamoDb.DeleteItemAsync(request, cancellationToken);
    }

    private static Paper MapToPaper(Dictionary<string, AttributeValue> item)
    {
        return new Paper
        {
            Id = item["paperId"].S,
            Title = item["title"].S,
            Authors = item["authors"].L.Select(a => a.S).ToList(),
            Description = item["description"].S,
            Tags = item["tags"].L.Select(t => t.S).ToList(),
            OriginalUrl = item.TryGetValue("originalUrl", out var url) ? url.S : null,
            PdfUrl = item.TryGetValue("pdfUrl", out var pdf) ? pdf.S : null,
            CreatedAt = DateTime.Parse(item["createdAt"].S),
            UpdatedAt = DateTime.Parse(item["updatedAt"].S)
        };
    }
}
