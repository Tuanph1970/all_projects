using Application.Common.Interfaces;
using Application.DTOs;
using Application.Features.Problems.Queries;
using Domain.Enums;
using Microsoft.Extensions.Logging;

namespace Application.Features.Problems.Handlers;

public class GetUserProblemsQueryHandler : IQueryHandler<GetUserProblemsQuery, PaginatedResult<ProblemDto>>
{
    private readonly IProblemRepository _problemRepository;
    private readonly ILogger<GetUserProblemsQueryHandler> _logger;

    public GetUserProblemsQueryHandler(
        IProblemRepository problemRepository,
        ILogger<GetUserProblemsQueryHandler> logger)
    {
        _problemRepository = problemRepository;
        _logger = logger;
    }

    public async Task<PaginatedResult<ProblemDto>> Handle(GetUserProblemsQuery request, CancellationToken cancellationToken)
    {
        _logger.LogInformation("Getting problems for user {UserId}, page {Page}, limit {Limit}",
            request.UserId, request.Page, request.Limit);

        // Parse status if provided
        ProblemStatus? status = null;
        if (!string.IsNullOrEmpty(request.Status) && Enum.TryParse<ProblemStatus>(request.Status, true, out var parsedStatus))
        {
            status = parsedStatus;
        }

        // Calculate skip
        var skip = (request.Page - 1) * request.Limit;

        // Get total count
        var totalCount = await _problemRepository.GetUserProblemsCountAsync(
            request.UserId,
            request.Category,
            status,
            request.SearchQuery,
            cancellationToken);

        // Get problems
        var problems = await _problemRepository.GetUserProblemsAsync(
            request.UserId,
            skip,
            request.Limit,
            request.Category,
            status,
            request.SearchQuery,
            cancellationToken);

        // Map to DTOs
        var problemDtos = problems.Select(p => new ProblemDto
        {
            Id = p.Id,
            UserId = p.UserId,
            ImageUrl = p.ImageUrl,
            Category = p.Category,
            Status = p.Status,
            Description = p.Description,
            CreatedAt = p.CreatedAt,
            UpdatedAt = p.UpdatedAt,
            Solution = p.Solution != null ? new SolutionDto
            {
                Id = p.Solution.Id,
                ProblemId = p.Solution.ProblemId,
                Steps = p.Solution.Steps,
                Confidence = p.Solution.Confidence,
                AdditionalNotes = p.Solution.AdditionalNotes,
                CreatedAt = p.Solution.CreatedAt
            } : null
        }).ToList();

        // Calculate pagination metadata
        var totalPages = (int)Math.Ceiling(totalCount / (double)request.Limit);

        return new PaginatedResult<ProblemDto>
        {
            Items = problemDtos,
            Page = request.Page,
            Limit = request.Limit,
            TotalCount = totalCount,
            TotalPages = totalPages,
            HasNextPage = request.Page < totalPages,
            HasPreviousPage = request.Page > 1
        };
    }
}
