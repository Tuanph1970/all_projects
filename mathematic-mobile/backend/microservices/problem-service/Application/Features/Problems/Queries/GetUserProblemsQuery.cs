using MediatR;
using ProblemService.Application.Common.Interfaces;
using ProblemService.Application.Features.Problems.DTOs;
using ProblemService.Application.Features.Problems.Extensions;
using ProblemService.Domain.Entities;

namespace ProblemService.Application.Features.Problems.Queries;

public record GetUserProblemsQuery(Guid UserId, int Page, int PageSize, string? Status) : IRequest<ProblemListDto>;

public class GetUserProblemsQueryHandler : IRequestHandler<GetUserProblemsQuery, ProblemListDto>
{
    private readonly IUnitOfWork _uow;

    public GetUserProblemsQueryHandler(IUnitOfWork uow) => _uow = uow;

    public async Task<ProblemListDto> Handle(GetUserProblemsQuery request, CancellationToken cancellationToken)
    {
        ProblemStatus? statusFilter = null;
        if (!string.IsNullOrEmpty(request.Status) && Enum.TryParse<ProblemStatus>(request.Status, true, out var s))
            statusFilter = s;

        var (items, total) = await _uow.Problems.GetByUserIdAsync(request.UserId, request.Page, request.PageSize, statusFilter, cancellationToken);

        return new ProblemListDto(
            items.Select(p => p.ToDto()).ToList(),
            total,
            request.Page,
            request.PageSize
        );
    }
}
