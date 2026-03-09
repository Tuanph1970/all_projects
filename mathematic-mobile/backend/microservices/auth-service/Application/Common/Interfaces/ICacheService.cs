using Microsoft.Extensions.Caching.Distributed;

namespace AuthService.Application.Common.Interfaces;

public interface ICacheService
{
    Task<T?> GetAsync<T>(string key, CancellationToken ct = default);
    Task SetAsync<T>(string key, T value, DistributedCacheEntryOptions? options = null, CancellationToken ct = default);
    Task RemoveAsync(string key, CancellationToken ct = default);
    Task<bool> ExistsAsync(string key, CancellationToken ct = default);
}

public static class CacheKeys
{
    private const string Prefix = "mathsolver:auth:";
    public static string UserById(Guid id) => $"{Prefix}user:{id}";
    public static string RefreshToken(string token) => $"{Prefix}refresh:{token}";
    public static string BlacklistedToken(string token) => $"{Prefix}blacklist:{token}";
}
