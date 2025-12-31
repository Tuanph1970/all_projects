using Microsoft.AspNetCore.Http;

namespace Application.Common.Interfaces;

public interface IFileStorageService
{
    Task<string> UploadImageAsync(IFormFile file, CancellationToken cancellationToken = default);
    Task<bool> DeleteImageAsync(string imageUrl, CancellationToken cancellationToken = default);
    Task<string> GetImageUrlAsync(string fileName, CancellationToken cancellationToken = default);
}
