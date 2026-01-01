using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using ProblemService.DTOs;
using ProblemService.Services;

namespace ProblemService.Controllers;

[ApiController]
[Route("api/v1/problems")]
public class ProblemController : ControllerBase
{
    private readonly IProblemManagementService _problemService;
    private readonly ILogger<ProblemController> _logger;

    public ProblemController(IProblemManagementService problemService, ILogger<ProblemController> logger)
    {
        _problemService = problemService;
        _logger = logger;
    }

    private int? GetUserId()
    {
        var userIdClaim = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)
            ?? User.FindFirst("sub");

        if (userIdClaim != null && int.TryParse(userIdClaim.Value, out var userId))
        {
            return userId;
        }
        return null;
    }

    [Authorize]
    [HttpPost]
    public async Task<IActionResult> CreateProblem([FromBody] CreateProblemRequest request)
    {
        var userId = GetUserId();
        if (userId == null)
        {
            return Unauthorized(new { success = false, message = "Invalid token" });
        }

        var (success, message, response) = await _problemService.CreateProblemAsync(userId.Value, request);

        if (!success)
        {
            return BadRequest(new { success = false, message });
        }

        return Created($"/api/v1/problems/{response!.Id}", new { success = true, message, data = response });
    }

    [Authorize]
    [HttpGet]
    public async Task<IActionResult> GetProblems(
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 10,
        [FromQuery] string? status = null)
    {
        var userId = GetUserId();
        if (userId == null)
        {
            return Unauthorized(new { success = false, message = "Invalid token" });
        }

        var response = await _problemService.GetUserProblemsAsync(userId.Value, page, pageSize, status);
        return Ok(new { success = true, data = response });
    }

    [Authorize]
    [HttpGet("{id}")]
    public async Task<IActionResult> GetProblem(int id)
    {
        var userId = GetUserId();
        if (userId == null)
        {
            return Unauthorized(new { success = false, message = "Invalid token" });
        }

        var problem = await _problemService.GetProblemByIdAsync(id);
        if (problem == null)
        {
            return NotFound(new { success = false, message = "Problem not found" });
        }

        if (problem.UserId != userId)
        {
            return Forbid();
        }

        return Ok(new { success = true, data = problem });
    }

    [Authorize]
    [HttpPut("{id}")]
    public async Task<IActionResult> UpdateProblem(int id, [FromBody] UpdateProblemRequest request)
    {
        var userId = GetUserId();
        if (userId == null)
        {
            return Unauthorized(new { success = false, message = "Invalid token" });
        }

        var (success, message) = await _problemService.UpdateProblemAsync(id, userId.Value, request);

        if (!success)
        {
            return BadRequest(new { success = false, message });
        }

        return Ok(new { success = true, message });
    }

    [Authorize]
    [HttpDelete("{id}")]
    public async Task<IActionResult> DeleteProblem(int id)
    {
        var userId = GetUserId();
        if (userId == null)
        {
            return Unauthorized(new { success = false, message = "Invalid token" });
        }

        var (success, message) = await _problemService.DeleteProblemAsync(id, userId.Value);

        if (!success)
        {
            return BadRequest(new { success = false, message });
        }

        return Ok(new { success = true, message });
    }

    [Authorize]
    [HttpPost("{id}/upload")]
    public async Task<IActionResult> UploadImage(int id, IFormFile file)
    {
        var userId = GetUserId();
        if (userId == null)
        {
            return Unauthorized(new { success = false, message = "Invalid token" });
        }

        if (file == null || file.Length == 0)
        {
            return BadRequest(new { success = false, message = "No file uploaded" });
        }

        var (success, message, imagePath) = await _problemService.UploadImageAsync(id, userId.Value, file);

        if (!success)
        {
            return BadRequest(new { success = false, message });
        }

        return Ok(new { success = true, message, data = new { imagePath } });
    }

    // Internal endpoint for solution service to update status
    [HttpPut("{id}/status")]
    public async Task<IActionResult> UpdateStatus(int id, [FromBody] ProblemStatusUpdate update)
    {
        // In production, validate internal service token
        var serviceToken = Request.Headers["X-Service-Token"].FirstOrDefault();
        var expectedToken = Environment.GetEnvironmentVariable("INTERNAL_SERVICE_TOKEN") ?? "internal-service-token";

        if (serviceToken != expectedToken)
        {
            return Unauthorized(new { success = false, message = "Invalid service token" });
        }

        var statusUpdate = update with { ProblemId = id };
        var (success, message) = await _problemService.UpdateProblemStatusAsync(statusUpdate);

        if (!success)
        {
            return BadRequest(new { success = false, message });
        }

        return Ok(new { success = true, message });
    }
}
