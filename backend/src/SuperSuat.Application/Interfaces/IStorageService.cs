namespace SuperSuat.Application.Interfaces;

public interface IStorageService
{
    Task<string> UploadAsync(byte[] data, string key, string contentType, CancellationToken cancellationToken = default);
    Task<string> GetUrlAsync(string key, CancellationToken cancellationToken = default);
    Task DeleteAsync(string key, CancellationToken cancellationToken = default);
}
