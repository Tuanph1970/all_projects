using ProblemService.Application.Common.Interfaces;
using ProblemService.Domain.Entities;

namespace ProblemService.Infrastructure.Persistence.Repositories;

public class ProblemHistoryRepository : IProblemHistoryRepository
{
    private readonly ProblemDbContext _db;

    public ProblemHistoryRepository(ProblemDbContext db) => _db = db;

    public void Add(ProblemHistory history) => _db.ProblemHistories.Add(history);
}
