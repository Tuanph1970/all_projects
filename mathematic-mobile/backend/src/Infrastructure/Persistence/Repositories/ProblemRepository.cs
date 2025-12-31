using Application.Common.Interfaces;
using Domain.Entities;
using Domain.Enums;
using Microsoft.EntityFrameworkCore;

namespace Infrastructure.Persistence.Repositories;

public class ProblemRepository : Repository<Problem>, IProblemRepository
{
    public ProblemRepository(ApplicationDbContext context) : base(context)
    {
    }

    public async Task<IEnumerable<Problem>> GetUserProblemsAsync(
        Guid userId,
        int skip,
        int take,
        string? category = null,
        ProblemStatus? status = null,
        string? searchQuery = null,
        CancellationToken cancellationToken = default)
    {
        var query = _dbSet
            .Include(p => p.Solution)
            .Where(p => p.UserId == userId);

        // Apply filters
        if (!string.IsNullOrEmpty(category))
        {
            query = query.Where(p => p.Category == category);
        }

        if (status.HasValue)
        {
            query = query.Where(p => p.Status == status.Value);
        }

        if (!string.IsNullOrEmpty(searchQuery))
        {
            query = query.Where(p =>
                p.Description != null && p.Description.Contains(searchQuery) ||
                p.Category.Contains(searchQuery));
        }

        // Order by newest first
        query = query.OrderByDescending(p => p.CreatedAt);

        // Apply pagination
        return await query
            .Skip(skip)
            .Take(take)
            .ToListAsync(cancellationToken);
    }

    public async Task<int> GetUserProblemsCountAsync(
        Guid userId,
        string? category = null,
        ProblemStatus? status = null,
        string? searchQuery = null,
        CancellationToken cancellationToken = default)
    {
        var query = _dbSet.Where(p => p.UserId == userId);

        // Apply same filters as GetUserProblemsAsync
        if (!string.IsNullOrEmpty(category))
        {
            query = query.Where(p => p.Category == category);
        }

        if (status.HasValue)
        {
            query = query.Where(p => p.Status == status.Value);
        }

        if (!string.IsNullOrEmpty(searchQuery))
        {
            query = query.Where(p =>
                p.Description != null && p.Description.Contains(searchQuery) ||
                p.Category.Contains(searchQuery));
        }

        return await query.CountAsync(cancellationToken);
    }

    public async Task<Problem?> GetByIdWithSolutionAsync(Guid id, CancellationToken cancellationToken = default)
    {
        return await _dbSet
            .Include(p => p.Solution)
            .FirstOrDefaultAsync(p => p.Id == id, cancellationToken);
    }
}
