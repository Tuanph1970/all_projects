using Microsoft.EntityFrameworkCore;
using ProblemService.Data;
using ProblemService.DTOs;
using ProblemService.Models;

namespace ProblemService.Services;

public interface IProblemManagementService
{
    Task<(bool Success, string Message, ProblemResponse? Response)> CreateProblemAsync(int userId, CreateProblemRequest request);
    Task<ProblemResponse?> GetProblemByIdAsync(int problemId);
    Task<ProblemListResponse> GetUserProblemsAsync(int userId, int page, int pageSize, string? status);
    Task<(bool Success, string Message)> UpdateProblemAsync(int problemId, int userId, UpdateProblemRequest request);
    Task<(bool Success, string Message)> DeleteProblemAsync(int problemId, int userId);
    Task<(bool Success, string Message, string? ImagePath)> UploadImageAsync(int problemId, int userId, IFormFile file);
    Task<(bool Success, string Message)> UpdateProblemStatusAsync(ProblemStatusUpdate update);
    Task<(bool Success, string Message)> SendToSolutionServiceAsync(int problemId, int userId);
}

public class ProblemManagementService : IProblemManagementService
{
    private readonly ProblemDbContext _context;
    private readonly ILogger<ProblemManagementService> _logger;
    private readonly IConfiguration _configuration;
    private readonly ISolutionServiceClient _solutionServiceClient;

    public ProblemManagementService(
        ProblemDbContext context,
        ILogger<ProblemManagementService> logger,
        IConfiguration configuration,
        ISolutionServiceClient solutionServiceClient)
    {
        _context = context;
        _logger = logger;
        _configuration = configuration;
        _solutionServiceClient = solutionServiceClient;
    }

    public async Task<(bool Success, string Message, ProblemResponse? Response)> CreateProblemAsync(int userId, CreateProblemRequest request)
    {
        try
        {
            var problem = new Problem
            {
                UserId = userId,
                Title = request.Title,
                Description = request.Description,
                Category = request.Category ?? "General",
                Difficulty = request.Difficulty ?? "Medium",
                Status = ProblemStatus.Pending,
                CreatedAt = DateTime.UtcNow
            };

            _context.Problems.Add(problem);
            await _context.SaveChangesAsync();

            // Add history entry
            _context.ProblemHistories.Add(new ProblemHistory
            {
                ProblemId = problem.Id,
                UserId = userId,
                Action = "Created",
                Details = $"Problem created: {request.Title}"
            });
            await _context.SaveChangesAsync();

            _logger.LogInformation("Problem created: {ProblemId} by user {UserId}", problem.Id, userId);

            return (true, "Problem created successfully", MapToResponse(problem));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error creating problem for user {UserId}", userId);
            return (false, "Failed to create problem", null);
        }
    }

    public async Task<ProblemResponse?> GetProblemByIdAsync(int problemId)
    {
        var problem = await _context.Problems.FindAsync(problemId);
        return problem == null ? null : MapToResponse(problem);
    }

    public async Task<ProblemListResponse> GetUserProblemsAsync(int userId, int page, int pageSize, string? status)
    {
        var query = _context.Problems.Where(p => p.UserId == userId);

        if (!string.IsNullOrEmpty(status) && Enum.TryParse<ProblemStatus>(status, true, out var statusEnum))
        {
            query = query.Where(p => p.Status == statusEnum);
        }

        var totalCount = await query.CountAsync();

        var problems = await query
            .OrderByDescending(p => p.CreatedAt)
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync();

        return new ProblemListResponse(
            problems.Select(MapToResponse).ToList(),
            totalCount,
            page,
            pageSize
        );
    }

    public async Task<(bool Success, string Message)> UpdateProblemAsync(int problemId, int userId, UpdateProblemRequest request)
    {
        var problem = await _context.Problems.FindAsync(problemId);
        if (problem == null)
        {
            return (false, "Problem not found");
        }

        if (problem.UserId != userId)
        {
            return (false, "Unauthorized to update this problem");
        }

        if (!string.IsNullOrEmpty(request.Title))
            problem.Title = request.Title;
        if (request.Description != null)
            problem.Description = request.Description;
        if (!string.IsNullOrEmpty(request.Category))
            problem.Category = request.Category;
        if (!string.IsNullOrEmpty(request.Difficulty))
            problem.Difficulty = request.Difficulty;

        problem.UpdatedAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();

        return (true, "Problem updated successfully");
    }

    public async Task<(bool Success, string Message)> DeleteProblemAsync(int problemId, int userId)
    {
        var problem = await _context.Problems.FindAsync(problemId);
        if (problem == null)
        {
            return (false, "Problem not found");
        }

        if (problem.UserId != userId)
        {
            return (false, "Unauthorized to delete this problem");
        }

        _context.Problems.Remove(problem);
        await _context.SaveChangesAsync();

        return (true, "Problem deleted successfully");
    }

    public async Task<(bool Success, string Message, string? ImagePath)> UploadImageAsync(int problemId, int userId, IFormFile file)
    {
        var problem = await _context.Problems.FindAsync(problemId);
        if (problem == null)
        {
            return (false, "Problem not found", null);
        }

        if (problem.UserId != userId)
        {
            return (false, "Unauthorized to upload image for this problem", null);
        }

        var allowedExtensions = new[] { ".jpg", ".jpeg", ".png", ".bmp" };
        var extension = Path.GetExtension(file.FileName).ToLowerInvariant();
        if (!allowedExtensions.Contains(extension))
        {
            return (false, "Invalid file type. Allowed: jpg, jpeg, png, bmp", null);
        }

        var maxFileSize = 10 * 1024 * 1024; // 10MB
        if (file.Length > maxFileSize)
        {
            return (false, "File size exceeds 10MB limit", null);
        }

        try
        {
            var uploadPath = _configuration["Storage:UploadPath"] ?? "/app/uploads";
            Directory.CreateDirectory(uploadPath);

            var fileName = $"{problemId}_{Guid.NewGuid()}{extension}";
            var filePath = Path.Combine(uploadPath, fileName);

            using (var stream = new FileStream(filePath, FileMode.Create))
            {
                await file.CopyToAsync(stream);
            }

            problem.ImagePath = fileName;
            problem.Status = ProblemStatus.Processing;
            problem.UpdatedAt = DateTime.UtcNow;
            await _context.SaveChangesAsync();

            _logger.LogInformation("Image uploaded for problem {ProblemId}: {FileName}", problemId, fileName);

            return (true, "Image uploaded successfully", fileName);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error uploading image for problem {ProblemId}", problemId);
            return (false, "Failed to upload image", null);
        }
    }

    public async Task<(bool Success, string Message)> UpdateProblemStatusAsync(ProblemStatusUpdate update)
    {
        var problem = await _context.Problems.FindAsync(update.ProblemId);
        if (problem == null)
        {
            return (false, "Problem not found");
        }

        problem.Status = update.Status;
        if (update.ExtractedText != null)
        {
            problem.ExtractedText = update.ExtractedText;
        }
        if (update.Status == ProblemStatus.Solved)
        {
            problem.SolvedAt = DateTime.UtcNow;
        }
        problem.UpdatedAt = DateTime.UtcNow;

        await _context.SaveChangesAsync();
        return (true, "Status updated successfully");
    }

    public async Task<(bool Success, string Message)> SendToSolutionServiceAsync(int problemId, int userId)
    {
        try
        {
            var problem = await _context.Problems.FindAsync(problemId);
            if (problem == null)
            {
                return (false, "Problem not found");
            }

            if (problem.UserId != userId)
            {
                return (false, "Unauthorized to process this problem");
            }

            // Check if problem has an image
            if (string.IsNullOrEmpty(problem.ImagePath))
            {
                return (false, "No image uploaded for this problem");
            }

            // Update status to Processing
            problem.Status = ProblemStatus.Processing;
            problem.UpdatedAt = DateTime.UtcNow;
            await _context.SaveChangesAsync();

            // Send to Solution Service for processing
            var solutionRequest = new ProcessImageRequest
            {
                ProblemId = problemId,
                ImagePath = problem.ImagePath,
                UserId = userId
            };

            var solutionResponse = await _solutionServiceClient.ProcessImageAsync(solutionRequest);

            if (solutionResponse?.Success == true)
            {
                _logger.LogInformation("Problem {ProblemId} sent to Solution Service successfully", problemId);
                return (true, "Problem sent to Solution Service for processing");
            }
            else
            {
                _logger.LogWarning("Solution Service returned failure for problem {ProblemId}: {Message}", 
                    problemId, solutionResponse?.Message ?? "Unknown error");
                
                // Revert status
                problem.Status = ProblemStatus.Pending;
                await _context.SaveChangesAsync();
                
                return (false, solutionResponse?.Message ?? "Failed to process problem");
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error sending problem {ProblemId} to Solution Service", problemId);
            return (false, $"Failed to send to Solution Service: {ex.Message}");
        }
    }

    private static ProblemResponse MapToResponse(Problem problem)
    {
        return new ProblemResponse(
            problem.Id,
            problem.UserId,
            problem.Title,
            problem.Description,
            problem.ImagePath != null ? $"/uploads/{problem.ImagePath}" : null,
            problem.ExtractedText,
            problem.Category,
            problem.Difficulty,
            problem.Status.ToString(),
            problem.CreatedAt,
            problem.SolvedAt
        );
    }
}
