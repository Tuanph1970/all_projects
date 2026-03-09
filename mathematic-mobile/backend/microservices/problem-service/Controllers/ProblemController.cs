using MediatR;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using ProblemService.Application.Features.Problems.Commands;
using ProblemService.Application.Features.Problems.Queries;
using ProblemService.Domain.Entities;

namespace ProblemService.Controllers;

[ApiController]
[Route("api/v1/problems")]
public class ProblemController : ControllerBase
{
    private readonly ISender _sender;
    private readonly IConfiguration _configuration;

    public ProblemController(ISender sender, IConfiguration configuration)
    {
        _sender = sender;
        _configuration = configuration;
    }

    private Guid? GetUserId()
    {
        var claim = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)
                    ?? User.FindFirst("sub");
        return claim != null && Guid.TryParse(claim.Value, out var id) ? id : null;
    }

    [Authorize]
    [HttpPost]
    public async Task<IActionResult> CreateProblem([FromBody] CreateProblemRequest request)
    {
        var userId = GetUserId();
        if (userId == null) return Unauthorized(new { success = false, message = "Invalid token" });

        var dto = await _sender.Send(new CreateProblemCommand(userId.Value, request.Title, request.Description, request.Category, request.Difficulty));
        return Created($"/api/v1/problems/{dto.Id}", new { success = true, message = "Problem created successfully", data = dto });
    }

    [Authorize]
    [HttpGet]
    public async Task<IActionResult> GetProblems([FromQuery] int page = 1, [FromQuery] int pageSize = 10, [FromQuery] string? status = null)
    {
        var userId = GetUserId();
        if (userId == null) return Unauthorized(new { success = false, message = "Invalid token" });

        var result = await _sender.Send(new GetUserProblemsQuery(userId.Value, page, pageSize, status));
        return Ok(new { success = true, data = result });
    }

    [Authorize]
    [HttpGet("{id:guid}")]
    public async Task<IActionResult> GetProblem(Guid id)
    {
        var userId = GetUserId();
        if (userId == null) return Unauthorized(new { success = false, message = "Invalid token" });

        var problem = await _sender.Send(new GetProblemByIdQuery(id));

        if (problem.UserId != userId)
            return Forbid();

        return Ok(new { success = true, data = problem });
    }

    [Authorize]
    [HttpPut("{id:guid}")]
    public async Task<IActionResult> UpdateProblem(Guid id, [FromBody] UpdateProblemRequest request)
    {
        var userId = GetUserId();
        if (userId == null) return Unauthorized(new { success = false, message = "Invalid token" });

        await _sender.Send(new UpdateProblemCommand(id, userId.Value, request.Title, request.Description, request.Category, request.Difficulty));
        return Ok(new { success = true, message = "Problem updated successfully" });
    }

    [Authorize]
    [HttpDelete("{id:guid}")]
    public async Task<IActionResult> DeleteProblem(Guid id)
    {
        var userId = GetUserId();
        if (userId == null) return Unauthorized(new { success = false, message = "Invalid token" });

        await _sender.Send(new DeleteProblemCommand(id, userId.Value));
        return Ok(new { success = true, message = "Problem deleted successfully" });
    }

    [Authorize]
    [HttpPost("{id:guid}/upload")]
    public async Task<IActionResult> UploadImage(Guid id, IFormFile file)
    {
        var userId = GetUserId();
        if (userId == null) return Unauthorized(new { success = false, message = "Invalid token" });

        var uploadPath = _configuration["Storage:UploadPath"]
            ?? Environment.GetEnvironmentVariable("STORAGE_UPLOAD_PATH")
            ?? "/app/uploads";

        var fileName = await _sender.Send(new UploadImageCommand(id, userId.Value, file, uploadPath));
        return Ok(new { success = true, message = "Image uploaded successfully", data = new { imagePath = fileName } });
    }

    // Internal endpoint for solution service to update problem status
    [HttpPut("{id:guid}/status")]
    public async Task<IActionResult> UpdateStatus(Guid id, [FromBody] StatusUpdateRequest update)
    {
        var serviceToken = Request.Headers["X-Service-Token"].FirstOrDefault();
        var expectedToken = Environment.GetEnvironmentVariable("INTERNAL_SERVICE_TOKEN") ?? "internal-service-token";

        if (serviceToken != expectedToken)
            return Unauthorized(new { success = false, message = "Invalid service token" });

        if (!Enum.TryParse<ProblemStatus>(update.Status, true, out var status))
            return BadRequest(new { success = false, message = "Invalid status value" });

        await _sender.Send(new UpdateProblemStatusCommand(id, status, update.ExtractedText));
        return Ok(new { success = true, message = "Status updated successfully" });
    }
}

// Request DTOs (inline)
public record CreateProblemRequest(string Title, string? Description, string? Category, string? Difficulty);
public record UpdateProblemRequest(string? Title, string? Description, string? Category, string? Difficulty);
public record StatusUpdateRequest(string Status, string? ExtractedText = null);
