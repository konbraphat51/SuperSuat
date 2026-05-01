using Amazon.S3;
using Amazon.S3.Model;
using SuperSuat.Application.Interfaces;

namespace SuperSuat.Infrastructure.Services;

public class S3StorageService : IStorageService
{
    private readonly IAmazonS3 _s3Client;
    private readonly string _bucketName;

    public S3StorageService(IAmazonS3 s3Client, string bucketName = "supersuat-storage")
    {
        _s3Client = s3Client;
        _bucketName = bucketName;
    }

    public async Task<string> UploadAsync(byte[] data, string key, string contentType, CancellationToken cancellationToken = default)
    {
        using var stream = new MemoryStream(data);

        var request = new PutObjectRequest
        {
            BucketName = _bucketName,
            Key = key,
            InputStream = stream,
            ContentType = contentType
        };

        await _s3Client.PutObjectAsync(request, cancellationToken);

        return $"s3://{_bucketName}/{key}";
    }

    public async Task<string> GetUrlAsync(string key, CancellationToken cancellationToken = default)
    {
        var request = new GetPreSignedUrlRequest
        {
            BucketName = _bucketName,
            Key = key,
            Expires = DateTime.UtcNow.AddHours(1)
        };

        return await Task.FromResult(_s3Client.GetPreSignedURL(request));
    }

    public async Task DeleteAsync(string key, CancellationToken cancellationToken = default)
    {
        var request = new DeleteObjectRequest
        {
            BucketName = _bucketName,
            Key = key
        };

        await _s3Client.DeleteObjectAsync(request, cancellationToken);
    }
}
