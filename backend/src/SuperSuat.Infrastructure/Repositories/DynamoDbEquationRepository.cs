using Amazon.DynamoDBv2;
using Amazon.DynamoDBv2.Model;
using SuperSuat.Application.Interfaces;
using SuperSuat.Domain.Entities;

namespace SuperSuat.Infrastructure.Repositories;

public class DynamoDbEquationRepository : IEquationRepository
{
    private readonly IAmazonDynamoDB _dynamoDb;
    private readonly string _tableName;

    public DynamoDbEquationRepository(IAmazonDynamoDB dynamoDb, string tableName = "supersuat-papers")
    {
        _dynamoDb = dynamoDb;
        _tableName = tableName;
    }

    public async Task<List<Equation>> GetByPaperIdAsync(string paperId, CancellationToken cancellationToken = default)
    {
        var request = new QueryRequest
        {
            TableName = _tableName,
            KeyConditionExpression = "PK = :pk AND begins_with(SK, :sk)",
            ExpressionAttributeValues = new Dictionary<string, AttributeValue>
            {
                { ":pk", new AttributeValue { S = $"PAPER#{paperId}" } },
                { ":sk", new AttributeValue { S = "EQUATION#" } }
            }
        };

        var response = await _dynamoDb.QueryAsync(request, cancellationToken);
        return response.Items.Select(MapToEquation).OrderBy(e => e.Order).ToList();
    }

    public async Task<Equation> CreateAsync(Equation equation, CancellationToken cancellationToken = default)
    {
        var item = new Dictionary<string, AttributeValue>
        {
            { "PK", new AttributeValue { S = $"PAPER#{equation.PaperId}" } },
            { "SK", new AttributeValue { S = $"EQUATION#{equation.Order:D3}" } },
            { "equationId", new AttributeValue { S = equation.Id } },
            { "paperId", new AttributeValue { S = equation.PaperId } },
            { "latexContent", new AttributeValue { S = equation.LatexContent } },
            { "order", new AttributeValue { N = equation.Order.ToString() } }
        };

        var request = new PutItemRequest
        {
            TableName = _tableName,
            Item = item
        };

        await _dynamoDb.PutItemAsync(request, cancellationToken);
        return equation;
    }

    public async Task CreateBatchAsync(List<Equation> equations, CancellationToken cancellationToken = default)
    {
        foreach (var equation in equations)
        {
            await CreateAsync(equation, cancellationToken);
        }
    }

    private static Equation MapToEquation(Dictionary<string, AttributeValue> item)
    {
        return new Equation
        {
            Id = item["equationId"].S,
            PaperId = item["paperId"].S,
            LatexContent = item["latexContent"].S,
            Order = int.Parse(item["order"].N)
        };
    }
}
