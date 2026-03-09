using ProblemService.Domain.Entities;

namespace ProblemService.Application.Common.Interfaces;

public interface IProblemHistoryRepository
{
    void Add(ProblemHistory history);
}
