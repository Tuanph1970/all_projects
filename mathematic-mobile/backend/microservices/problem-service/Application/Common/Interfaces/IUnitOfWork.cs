namespace ProblemService.Application.Common.Interfaces;

public interface IUnitOfWork
{
    IProblemRepository Problems { get; }
    IProblemHistoryRepository ProblemHistories { get; }
    Task<int> SaveChangesAsync(CancellationToken ct = default);
}
