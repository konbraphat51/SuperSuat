using Amazon.DynamoDBv2;
using Amazon.DynamoDBv2.Model;
using SuperSuat.Application.Interfaces;
using SuperSuat.Domain.Entities;

namespace SuperSuat.Infrastructure.Repositories;

public class DynamoDbTableRepository : ITableRepository
{
    private readonly IAmazonDynamoDB _dynamoDb;
    private readonly string _tableName;

    public DynamoDbTableRepository(IAmazonDynamoDB dynamoDb, string tableName = "supersuat-papers")
    {
        _dynamoDb = dynamoDb;
        _tableName = tableName;
    }

    public async Task<List<Table>> GetByPaperIdAsync(string paperId, CancellationToken cancellationToken = default)
    {
        var request = new QueryRequest
        {
            TableName = _tableName,
            KeyConditionExpression = "PK = :pk AND begins_with(SK, :sk)",
            ExpressionAttributeValues = new Dictionary<string, AttributeValue>
            {
                { ":pk", new AttributeValue { S = $"PAPER#{paperId}" } },
                { ":sk", new AttributeValue { S = "TABLE#" } }
            }
        };

        var response = await _dynamoDb.QueryAsync(request, cancellationToken);
        return response.Items.Select(MapToTable).OrderBy(t => t.Order).ToList();
    }

    public async Task<Table> CreateAsync(Table table, CancellationToken cancellationToken = default)
    {
        var item = new Dictionary<string, AttributeValue>
        {
            { "PK", new AttributeValue { S = $"PAPER#{table.PaperId}" } },
            { "SK", new AttributeValue { S = $"TABLE#{table.Order:D3}" } },
            { "tableId", new AttributeValue { S = table.Id } },
            { "paperId", new AttributeValue { S = table.PaperId } },
            { "caption", new AttributeValue { S = table.Caption } },
            { "content", new AttributeValue { S = table.Content } },
            { "order", new AttributeValue { N = table.Order.ToString() } }
        };

        var request = new PutItemRequest
        {
            TableName = _tableName,
            Item = item
        };

        await _dynamoDb.PutItemAsync(request, cancellationToken);
        return table;
    }

    public async Task CreateBatchAsync(List<Table> tables, CancellationToken cancellationToken = default)
    {
        foreach (var table in tables)
        {
            await CreateAsync(table, cancellationToken);
        }
    }

    private static Table MapToTable(Dictionary<string, AttributeValue> item)
    {
        return new Table
        {
            Id = item["tableId"].S,
            PaperId = item["paperId"].S,
            Caption = item["caption"].S,
            Content = item["content"].S,
            Order = int.Parse(item["order"].N)
        };
    }
}
