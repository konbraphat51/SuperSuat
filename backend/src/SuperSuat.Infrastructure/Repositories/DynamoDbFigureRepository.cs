using Amazon.DynamoDBv2;
using Amazon.DynamoDBv2.Model;
using SuperSuat.Application.Interfaces;
using SuperSuat.Domain.Entities;

namespace SuperSuat.Infrastructure.Repositories;

public class DynamoDbFigureRepository : IFigureRepository
{
    private readonly IAmazonDynamoDB _dynamoDb;
    private readonly string _tableName;

    public DynamoDbFigureRepository(IAmazonDynamoDB dynamoDb, string tableName = "supersuat-papers")
    {
        _dynamoDb = dynamoDb;
        _tableName = tableName;
    }

    public async Task<List<Figure>> GetByPaperIdAsync(string paperId, CancellationToken cancellationToken = default)
    {
        var request = new QueryRequest
        {
            TableName = _tableName,
            KeyConditionExpression = "PK = :pk AND begins_with(SK, :sk)",
            ExpressionAttributeValues = new Dictionary<string, AttributeValue>
            {
                { ":pk", new AttributeValue { S = $"PAPER#{paperId}" } },
                { ":sk", new AttributeValue { S = "FIGURE#" } }
            }
        };

        var response = await _dynamoDb.QueryAsync(request, cancellationToken);
        return response.Items.Select(MapToFigure).OrderBy(f => f.Order).ToList();
    }

    public async Task<Figure> CreateAsync(Figure figure, CancellationToken cancellationToken = default)
    {
        var item = new Dictionary<string, AttributeValue>
        {
            { "PK", new AttributeValue { S = $"PAPER#{figure.PaperId}" } },
            { "SK", new AttributeValue { S = $"FIGURE#{figure.Order:D3}" } },
            { "figureId", new AttributeValue { S = figure.Id } },
            { "paperId", new AttributeValue { S = figure.PaperId } },
            { "caption", new AttributeValue { S = figure.Caption } },
            { "imageUrl", new AttributeValue { S = figure.ImageUrl } },
            { "order", new AttributeValue { N = figure.Order.ToString() } }
        };

        var request = new PutItemRequest
        {
            TableName = _tableName,
            Item = item
        };

        await _dynamoDb.PutItemAsync(request, cancellationToken);
        return figure;
    }

    public async Task CreateBatchAsync(List<Figure> figures, CancellationToken cancellationToken = default)
    {
        foreach (var figure in figures)
        {
            await CreateAsync(figure, cancellationToken);
        }
    }

    private static Figure MapToFigure(Dictionary<string, AttributeValue> item)
    {
        return new Figure
        {
            Id = item["figureId"].S,
            PaperId = item["paperId"].S,
            Caption = item["caption"].S,
            ImageUrl = item["imageUrl"].S,
            Order = int.Parse(item["order"].N)
        };
    }
}
