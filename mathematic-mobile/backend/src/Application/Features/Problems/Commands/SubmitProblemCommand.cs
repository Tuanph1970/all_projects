using Application.Common.Interfaces;
using Application.DTOs;
using Microsoft.AspNetCore.Http;

namespace Application.Features.Problems.Commands;

public class SubmitProblemCommand : ICommand<ProblemResult>
{
    public Guid UserId { get; set; }
    public IFormFile ImageFile { get; set; } = null!;
    public string Category { get; set; } = string.Empty;
    public string? Description { get; set; }
}
