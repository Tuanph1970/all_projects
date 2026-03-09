using MediatR;
using ProblemService.Application.Common.Exceptions;
using ProblemService.Application.Common.Interfaces;
using ProblemService.Application.Features.Problems.DTOs;
using ProblemService.Application.Features.Problems.Extensions;

namespace ProblemService.Application.Features.Problems.Queries;

public record GetProblemByIdQuery(Guid ProblemId) : IRequest<ProblemDto>;

public class GetProblemByIdQueryHandler : IRequestHandler<GetProblemByIdQuery, ProblemDto>
{
    private readonly IUnitOfWork _uow;

    public GetProblemByIdQueryHandler(IUnitOfWork uow) => _uow = uow;

    public async Task<ProblemDto> Handle(GetProblemByIdQuery request, CancellationToken cancellationToken)
    {
        var problem = await _uow.Problems.GetByIdAsync(request.ProblemId, cancellationToken)
            ?? throw new NotFoundException(nameof(Domain.Entities.Problem), request.ProblemId);

        return problem.ToDto();
    }
}
