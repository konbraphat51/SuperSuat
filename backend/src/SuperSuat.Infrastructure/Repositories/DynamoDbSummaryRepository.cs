using Amazon.DynamoDBv2;
using Amazon.DynamoDBv2.Model;
using SuperSuat.Application.Interfaces;
using SuperSuat.Domain.Entities;
using System.Text.Json;

namespace SuperSuat.Infrastructure.Repositories;

public class DynamoDbSummaryRepository : ISummaryRepository
{
    private readonly IAmazonDynamoDB _dynamoDb;
    private readonly string _tableName;

    public DynamoDbSummaryRepository(IAmazonDynamoDB dynamoDb, string tableName = "supersuat-summaries")
    {
        _dynamoDb = dynamoDb;
        _tableName = tableName;
    }

    public async Task<Summary?> GetByPaperIdAndLanguageAsync(string paperId, string language, CancellationToken cancellationToken = default)
    {
        var request = new GetItemRequest
        {
            TableName = _tableName,
            Key = new Dictionary<string, AttributeValue>
            {
                { "PK", new AttributeValue { S = $"PAPER#{paperId}" } },
                { "SK", new AttributeValue { S = $"SUMMARY#{language}" } }
            }
        };

        var response = await _dynamoDb.GetItemAsync(request, cancellationToken);
        if (!response.IsItemSet)
            return null;

        return MapToSummary(response.Item);
    }

    public async Task<Summary> CreateAsync(Summary summary, CancellationToken cancellationToken = default)
    {
        var item = new Dictionary<string, AttributeValue>
        {
            { "PK", new AttributeValue { S = $"PAPER#{summary.PaperId}" } },
            { "SK", new AttributeValue { S = $"SUMMARY#{summary.Language}" } },
            { "summaryId", new AttributeValue { S = summary.Id } },
            { "paperId", new AttributeValue { S = summary.PaperId } },
            { "language", new AttributeValue { S = summary.Language } },
            { "wholeSummary", new AttributeValue { S = summary.WholeSummary } },
            { "createdAt", new AttributeValue { S = summary.CreatedAt.ToString("O") } }
        };

        if (summary.ChapterSummaries != null && summary.ChapterSummaries.Count > 0)
        {
            item["chapterSummaries"] = new AttributeValue { S = JsonSerializer.Serialize(summary.ChapterSummaries) };
        }

        var request = new PutItemRequest
        {
            TableName = _tableName,
            Item = item
        };

        await _dynamoDb.PutItemAsync(request, cancellationToken);
        return summary;
    }

    private static Summary MapToSummary(Dictionary<string, AttributeValue> item)
    {
        List<ChapterSummary>? chapterSummaries = null;
        if (item.TryGetValue("chapterSummaries", out var cs))
        {
            chapterSummaries = JsonSerializer.Deserialize<List<ChapterSummary>>(cs.S);
        }

        return new Summary
        {
            Id = item["summaryId"].S,
            PaperId = item["paperId"].S,
            Language = item["language"].S,
            WholeSummary = item["wholeSummary"].S,
            ChapterSummaries = chapterSummaries ?? [],
            CreatedAt = DateTime.Parse(item["createdAt"].S)
        };
    }
}
