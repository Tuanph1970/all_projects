using Application.DTOs;
using Application.Features.Problems.Commands;
using Application.Features.Problems.Queries;
using MediatR;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Presentation.Extensions;
using Presentation.Models.Requests;
using System.Security.Claims;

namespace Presentation.Controllers;

[ApiController]
[Route("mathematic/v1/api/[controller]")]
[Authorize]
public class ProblemController : ControllerBase
{
    private readonly ISender _mediator;
    private readonly ILogger<ProblemController> _logger;

    public ProblemController(ISender mediator, ILogger<ProblemController> logger)
    {
        _mediator = mediator;
        _logger = logger;
    }

    /// <summary>
    /// Submit a new mathematical problem for solving
    /// </summary>
    /// <param name="request">Problem submission details with image</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>Problem result with solution (if successful)</returns>
    [HttpPost]
    [Consumes("multipart/form-data")]
    public async Task<ActionResult<ProblemResult>> SubmitProblem(
        [FromForm] SubmitProblemRequest request,
        CancellationToken cancellationToken)
    {
        var userId = User.GetUserId();
        _logger.LogInformation("User {UserId} submitting problem", userId);

        var command = new SubmitProblemCommand
        {
            UserId = userId,
            ImageFile = request.ImageFile,
            Category = request.Category,
            Description = request.Description
        };

        var result = await _mediator.Send(command, cancellationToken);

        if (!result.Success)
        {
            return BadRequest(result);
        }

        return Ok(result);
    }

    /// <summary>
    /// Get all problems for the authenticated user with pagination and filters
    /// </summary>
    /// <param name="request">Query parameters for pagination and filtering</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>Paginated list of problems</returns>
    [HttpGet]
    public async Task<ActionResult<PaginatedResult<ProblemDto>>> GetUserProblems(
        [FromQuery] GetProblemsRequest request,
        CancellationToken cancellationToken)
    {
        var userId = User.GetUserId();
        _logger.LogInformation("User {UserId} retrieving problems", userId);

        // Validate and limit page size
        var limit = Math.Min(request.Limit, 100);

        var query = new GetUserProblemsQuery
        {
            UserId = userId,
            Page = request.Page,
            Limit = limit,
            Category = request.Category,
            Status = request.Status,
            SearchQuery = request.SearchQuery
        };

        var result = await _mediator.Send(query, cancellationToken);
        return Ok(result);
    }

    /// <summary>
    /// Get a specific problem by ID
    /// </summary>
    /// <param name="id">Problem ID</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>Problem details with solution (if available)</returns>
    [HttpGet("{id}")]
    public async Task<ActionResult<ProblemDto>> GetProblemById(
        Guid id,
        CancellationToken cancellationToken)
    {
        var userId = User.GetUserId();
        _logger.LogInformation("User {UserId} retrieving problem {ProblemId}", userId, id);

        var query = new GetProblemByIdQuery
        {
            ProblemId = id,
            UserId = userId
        };

        var result = await _mediator.Send(query, cancellationToken);

        if (result == null)
        {
            return NotFound(new { message = $"Problem with ID {id} not found" });
        }

        return Ok(result);
    }

    /// <summary>
    /// Delete a problem
    /// </summary>
    /// <param name="id">Problem ID to delete</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>Success status</returns>
    [HttpDelete("{id}")]
    public async Task<ActionResult> DeleteProblem(
        Guid id,
        CancellationToken cancellationToken)
    {
        var userId = User.GetUserId();
        _logger.LogInformation("User {UserId} deleting problem {ProblemId}", userId, id);

        var command = new DeleteProblemCommand
        {
            ProblemId = id,
            UserId = userId
        };

        var result = await _mediator.Send(command, cancellationToken);
        return Ok(new { message = "Problem deleted successfully" });
    }

    /// <summary>
    /// Retry solving a failed or incomplete problem
    /// </summary>
    /// <param name="id">Problem ID to retry</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>Updated problem result with new solution attempt</returns>
    [HttpPost("{id}/retry")]
    public async Task<ActionResult<ProblemResult>> RetryProblem(
        Guid id,
        CancellationToken cancellationToken)
    {
        var userId = User.GetUserId();
        _logger.LogInformation("User {UserId} retrying problem {ProblemId}", userId, id);

        var command = new RetryProblemCommand
        {
            ProblemId = id,
            UserId = userId
        };

        var result = await _mediator.Send(command, cancellationToken);

        if (!result.Success)
        {
            return BadRequest(result);
        }

        return Ok(result);
    }
}
