using System.Text.Json;
using Microsoft.Extensions.Caching.Distributed;
using Microsoft.Extensions.Logging;
using AuthService.Application.Common.Interfaces;

namespace AuthService.Infrastructure.Services;

public class RedisCacheService : ICacheService
{
    private readonly IDistributedCache _cache;
    private readonly ILogger<RedisCacheService> _logger;
    private static readonly JsonSerializerOptions _json = new() { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };

    public RedisCacheService(IDistributedCache cache, ILogger<RedisCacheService> logger)
    { _cache = cache; _logger = logger; }

    public async Task<T?> GetAsync<T>(string key, CancellationToken ct = default)
    {
        try
        {
            var value = await _cache.GetStringAsync(key, ct);
            return string.IsNullOrEmpty(value) ? default : JsonSerializer.Deserialize<T>(value, _json);
        }
        catch (Exception ex) { _logger.LogError(ex, "Cache GET failed for {Key}", key); return default; }
    }

    public async Task SetAsync<T>(string key, T value, DistributedCacheEntryOptions? options = null, CancellationToken ct = default)
    {
        try
        {
            var serialized = JsonSerializer.Serialize(value, _json);
            await _cache.SetStringAsync(key, serialized, options ?? new DistributedCacheEntryOptions
            { AbsoluteExpirationRelativeToNow = TimeSpan.FromMinutes(30) }, ct);
        }
        catch (Exception ex) { _logger.LogError(ex, "Cache SET failed for {Key}", key); }
    }

    public async Task RemoveAsync(string key, CancellationToken ct = default)
    {
        try { await _cache.RemoveAsync(key, ct); }
        catch (Exception ex) { _logger.LogError(ex, "Cache REMOVE failed for {Key}", key); }
    }

    public async Task<bool> ExistsAsync(string key, CancellationToken ct = default)
    {
        try { return !string.IsNullOrEmpty(await _cache.GetStringAsync(key, ct)); }
        catch { return false; }
    }
}
