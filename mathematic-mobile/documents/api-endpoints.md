# API Endpoints Documentation - .NET Core Web API

## Overview

The .NET Core Web API service provides HTTP endpoints for authentication, problem submission, solution retrieval, and user management. It serves as the gateway between the mobile application and the Python ML service.

## Base Configuration

```csharp
// Program.cs - API Configuration
var builder = WebApplication.CreateBuilder(args);

// Add services
builder.Services.AddControllers();
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options => {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = builder.Configuration["Jwt:Issuer"],
            ValidAudience = builder.Configuration["Jwt:Audience"],
            IssuerSigningKey = new SymmetricSecurityKey(
                Encoding.UTF8.GetBytes(builder.Configuration["Jwt:SecretKey"]))
        };
    });

builder.Services.AddDbContext<ApplicationDbContext>(options =>
    options.UseMySql(builder.Configuration.GetConnectionString("DefaultConnection"),
        ServerVersion.AutoDetect(builder.Configuration.GetConnectionString("DefaultConnection"))));

builder.Services.AddStackExchangeRedisCache(options => {
    options.Configuration = builder.Configuration.GetConnectionString("Redis");
});

builder.Services.AddSignalR();
builder.Services.AddScoped<IMLServiceClient, MLServiceClient>();
builder.Services.AddScoped<IUserService, UserService>();
builder.Services.AddScoped<ISolutionService, SolutionService>();
```

## Authentication Endpoints

### POST /api/auth/register
Register a new user account.

**Request Body:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePassword123!",
  "firstName": "John",
  "lastName": "Doe",
  "grade": 10
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "userId": "123e4567-e89b-12d3-a456-426614174000",
    "username": "john_doe",
    "email": "john@example.com",
    "firstName": "John",
    "lastName": "Doe",
    "grade": 10,
    "createdAt": "2024-01-15T10:30:00Z"
  },
  "message": "User registered successfully"
}
```

**Implementation:**
```csharp
[ApiController]
[Route("api/[controller]")]
public class AuthController : ControllerBase
{
    private readonly IUserService _userService;
    private readonly IConfiguration _configuration;

    [HttpPost("register")]
    public async Task<IActionResult> Register([FromBody] RegisterRequest request)
    {
        try
        {
            // Validate input
            if (!ModelState.IsValid)
                return BadRequest(ModelState);

            // Check if user exists
            if (await _userService.UserExistsAsync(request.Email))
                return Conflict(new { message = "User already exists" });

            // Create user
            var user = await _userService.CreateUserAsync(request);
            
            var response = new
            {
                success = true,
                data = new
                {
                    userId = user.Id,
                    username = user.Username,
                    email = user.Email,
                    firstName = user.FirstName,
                    lastName = user.LastName,
                    grade = user.Grade,
                    createdAt = user.CreatedAt
                },
                message = "User registered successfully"
            };

            return CreatedAtAction(nameof(GetUser), new { id = user.Id }, response);
        }
        catch (Exception ex)
        {
            return StatusCode(500, new { message = "Registration failed", error = ex.Message });
        }
    }
}
```

### POST /api/auth/login
Authenticate user and return JWT token.

**Request Body:**
```json
{
  "email": "john@example.com",
  "password": "SecurePassword123!"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refreshToken": "def50200a1b2c3d4e5f6...",
    "expiresAt": "2024-01-15T18:30:00Z",
    "user": {
      "userId": "123e4567-e89b-12d3-a456-426614174000",
      "username": "john_doe",
      "email": "john@example.com",
      "firstName": "John",
      "lastName": "Doe",
      "grade": 10
    }
  },
  "message": "Login successful"
}
```

**Implementation:**
```csharp
[HttpPost("login")]
public async Task<IActionResult> Login([FromBody] LoginRequest request)
{
    try
    {
        // Validate credentials
        var user = await _userService.ValidateUserAsync(request.Email, request.Password);
        if (user == null)
            return Unauthorized(new { message = "Invalid credentials" });

        // Generate JWT token
        var token = GenerateJwtToken(user);
        var refreshToken = GenerateRefreshToken();

        // Save refresh token
        await _userService.SaveRefreshTokenAsync(user.Id, refreshToken);

        var response = new
        {
            success = true,
            data = new
            {
                token = token,
                refreshToken = refreshToken,
                expiresAt = DateTime.UtcNow.AddHours(24),
                user = new
                {
                    userId = user.Id,
                    username = user.Username,
                    email = user.Email,
                    firstName = user.FirstName,
                    lastName = user.LastName,
                    grade = user.Grade
                }
            },
            message = "Login successful"
        };

        return Ok(response);
    }
    catch (Exception ex)
    {
        return StatusCode(500, new { message = "Login failed", error = ex.Message });
    }
}
```

### POST /api/auth/refresh
Refresh JWT token using refresh token.

**Request Body:**
```json
{
  "refreshToken": "def50200a1b2c3d4e5f6..."
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expiresAt": "2024-01-15T18:30:00Z"
  },
  "message": "Token refreshed successfully"
}
```

## Solution Processing Endpoints

### POST /api/solution/solve
Submit a mathematical problem for solving.

**Request (Multipart Form Data):**
```
image: [image file]
grade: 10
subject: "algebra"
urgency: "normal"
```

**Response (202 Accepted):**
```json
{
  "success": true,
  "data": {
    "jobId": "987fcdeb-51a2-4567-8901-234567890123",
    "status": "processing",
    "estimatedTime": 30,
    "submittedAt": "2024-01-15T10:30:00Z"
  },
  "message": "Problem submitted for processing"
}
```

**Implementation:**
```csharp
[ApiController]
[Route("api/[controller]")]
[Authorize]
public class SolutionController : ControllerBase
{
    private readonly ISolutionService _solutionService;
    private readonly IMLServiceClient _mlServiceClient;
    private readonly IQueueService _queueService;

    [HttpPost("solve")]
    public async Task<IActionResult> SolveProblem([FromForm] SolveProblemRequest request)
    {
        try
        {
            var userId = User.FindFirst(ClaimTypes.NameIdentifier)?.Value;
            
            // Validate input
            if (request.Image == null || request.Image.Length == 0)
                return BadRequest(new { message = "Image is required" });

            // Create problem record
            var problem = new Problem
            {
                Id = Guid.NewGuid(),
                UserId = userId,
                Grade = request.Grade,
                Subject = request.Subject,
                Status = ProblemStatus.Processing,
                CreatedAt = DateTime.UtcNow
            };

            // Save image
            var imageUrl = await _fileService.SaveImageAsync(request.Image);
            problem.ImageUrl = imageUrl;

            // Save to database
            await _solutionService.CreateProblemAsync(problem);

            // Queue for ML processing
            var job = new SolutionJob
            {
                JobId = problem.Id,
                ImageUrl = imageUrl,
                Grade = request.Grade,
                Subject = request.Subject,
                UserId = userId,
                Priority = request.Urgency == "high" ? 1 : 5
            };

            await _queueService.QueueSolutionJobAsync(job);

            var response = new
            {
                success = true,
                data = new
                {
                    jobId = problem.Id,
                    status = problem.Status.ToString().ToLower(),
                    estimatedTime = CalculateEstimatedTime(request.Subject),
                    submittedAt = problem.CreatedAt
                },
                message = "Problem submitted for processing"
            };

            return Accepted(response);
        }
        catch (Exception ex)
        {
            return StatusCode(500, new { message = "Failed to submit problem", error = ex.Message });
        }
    }
}
```

### GET /api/solution/{jobId}
Get solution by job ID.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "jobId": "987fcdeb-51a2-4567-8901-234567890123",
    "status": "completed",
    "problem": {
      "text": "Solve for x: 2x + 5 = 11",
      "subject": "algebra",
      "grade": 10
    },
    "solution": {
      "steps": [
        {
          "step": 1,
          "description": "Subtract 5 from both sides",
          "equation": "2x + 5 - 5 = 11 - 5",
          "result": "2x = 6"
        },
        {
          "step": 2,
          "description": "Divide both sides by 2",
          "equation": "2x ÷ 2 = 6 ÷ 2",
          "result": "x = 3"
        }
      ],
      "finalAnswer": "x = 3",
      "confidence": 0.95,
      "explanation": "This is a linear equation that can be solved by isolating x."
    },
    "processingTime": 15.3,
    "generatedAt": "2024-01-15T10:30:45Z"
  }
}
```

**Implementation:**
```csharp
[HttpGet("{jobId}")]
public async Task<IActionResult> GetSolution(Guid jobId)
{
    try
    {
        var userId = User.FindFirst(ClaimTypes.NameIdentifier)?.Value;
        
        // Get problem and solution
        var problem = await _solutionService.GetProblemByIdAsync(jobId);
        if (problem == null)
            return NotFound(new { message = "Problem not found" });

        // Check ownership
        if (problem.UserId != userId)
            return Forbid();

        var solution = await _solutionService.GetSolutionByProblemIdAsync(jobId);

        var response = new
        {
            success = true,
            data = new
            {
                jobId = problem.Id,
                status = problem.Status.ToString().ToLower(),
                problem = new
                {
                    text = problem.ExtractedText,
                    subject = problem.Subject,
                    grade = problem.Grade
                },
                solution = solution != null ? new
                {
                    steps = solution.Steps,
                    finalAnswer = solution.FinalAnswer,
                    confidence = solution.Confidence,
                    explanation = solution.Explanation
                } : null,
                processingTime = solution?.ProcessingTime,
                generatedAt = solution?.GeneratedAt
            }
        };

        return Ok(response);
    }
    catch (Exception ex)
    {
        return StatusCode(500, new { message = "Failed to get solution", error = ex.Message });
    }
}
```

### GET /api/solution/history
Get user's solution history with pagination.

**Query Parameters:**
- `page`: Page number (default: 1)
- `pageSize`: Items per page (default: 20, max: 100)
- `subject`: Filter by subject (optional)
- `status`: Filter by status (optional)

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "jobId": "987fcdeb-51a2-4567-8901-234567890123",
        "problemText": "Solve for x: 2x + 5 = 11",
        "subject": "algebra",
        "status": "completed",
        "confidence": 0.95,
        "submittedAt": "2024-01-15T10:30:00Z",
        "completedAt": "2024-01-15T10:30:45Z"
      }
    ],
    "pagination": {
      "currentPage": 1,
      "pageSize": 20,
      "totalItems": 45,
      "totalPages": 3,
      "hasNext": true,
      "hasPrevious": false
    }
  }
}
```

## User Management Endpoints

### GET /api/user/profile
Get current user's profile.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "userId": "123e4567-e89b-12d3-a456-426614174000",
    "username": "john_doe",
    "email": "john@example.com",
    "firstName": "John",
    "lastName": "Doe",
    "grade": 10,
    "stats": {
      "problemsSolved": 45,
      "averageConfidence": 0.87,
      "subjectBreakdown": {
        "algebra": 20,
        "calculus": 15,
        "geometry": 10
      }
    },
    "createdAt": "2024-01-01T00:00:00Z",
    "lastActive": "2024-01-15T10:30:00Z"
  }
}
```

### PUT /api/user/profile
Update user profile.

**Request Body:**
```json
{
  "firstName": "John",
  "lastName": "Doe",
  "grade": 11
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "userId": "123e4567-e89b-12d3-a456-426614174000",
    "username": "john_doe",
    "email": "john@example.com",
    "firstName": "John",
    "lastName": "Doe",
    "grade": 11,
    "updatedAt": "2024-01-15T10:30:00Z"
  },
  "message": "Profile updated successfully"
}
```

## Feedback Endpoints

### POST /api/feedback/solution/{solutionId}
Submit feedback for a solution.

**Request Body:**
```json
{
  "rating": 4,
  "feedback": "Good explanation but could be clearer",
  "corrections": [
    {
      "step": 2,
      "correction": "Should mention that we're dividing by the coefficient of x"
    }
  ],
  "helpful": true
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "feedbackId": "456e7890-e12b-34d5-a678-901234567890",
    "solutionId": "987fcdeb-51a2-4567-8901-234567890123",
    "rating": 4,
    "submittedAt": "2024-01-15T10:30:00Z"
  },
  "message": "Feedback submitted successfully"
}
```

**Implementation:**
```csharp
[ApiController]
[Route("api/[controller]")]
[Authorize]
public class FeedbackController : ControllerBase
{
    private readonly IFeedbackService _feedbackService;
    private readonly IQueueService _queueService;

    [HttpPost("solution/{solutionId}")]
    public async Task<IActionResult> SubmitSolutionFeedback(Guid solutionId, [FromBody] SolutionFeedbackRequest request)
    {
        try
        {
            var userId = User.FindFirst(ClaimTypes.NameIdentifier)?.Value;

            // Validate solution exists and user has access
            var solution = await _solutionService.GetSolutionByIdAsync(solutionId);
            if (solution == null || solution.Problem.UserId != userId)
                return NotFound(new { message = "Solution not found" });

            // Create feedback record
            var feedback = new SolutionFeedback
            {
                Id = Guid.NewGuid(),
                SolutionId = solutionId,
                UserId = userId,
                Rating = request.Rating,
                Comments = request.Feedback,
                Corrections = request.Corrections,
                IsHelpful = request.Helpful,
                SubmittedAt = DateTime.UtcNow
            };

            await _feedbackService.CreateFeedbackAsync(feedback);

            // Queue for ML service processing
            await _queueService.QueueFeedbackJobAsync(new FeedbackJob
            {
                FeedbackId = feedback.Id,
                SolutionId = solutionId,
                ProblemText = solution.Problem.ExtractedText,
                GeneratedSolution = solution.StepByStepSolution,
                UserFeedback = request
            });

            var response = new
            {
                success = true,
                data = new
                {
                    feedbackId = feedback.Id,
                    solutionId = solutionId,
                    rating = feedback.Rating,
                    submittedAt = feedback.SubmittedAt
                },
                message = "Feedback submitted successfully"
            };

            return Created($"/api/feedback/{feedback.Id}", response);
        }
        catch (Exception ex)
        {
            return StatusCode(500, new { message = "Failed to submit feedback", error = ex.Message });
        }
    }
}
```

## File Management Endpoints

### POST /api/files/upload
Upload image file for problem solving.

**Request (Multipart Form Data):**
```
file: [image file]
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "fileId": "789e0123-e45f-67g8-h901-234567890123",
    "fileName": "math_problem.jpg",
    "fileUrl": "https://storage.example.com/images/789e0123-e45f-67g8-h901-234567890123.jpg",
    "fileSize": 204800,
    "contentType": "image/jpeg",
    "uploadedAt": "2024-01-15T10:30:00Z"
  },
  "message": "File uploaded successfully"
}
```

**Implementation:**
```csharp
[ApiController]
[Route("api/[controller]")]
[Authorize]
public class FilesController : ControllerBase
{
    private readonly IFileService _fileService;

    [HttpPost("upload")]
    public async Task<IActionResult> UploadFile(IFormFile file)
    {
        try
        {
            // Validate file
            if (file == null || file.Length == 0)
                return BadRequest(new { message = "No file provided" });

            // Validate file type
            var allowedTypes = new[] { "image/jpeg", "image/png", "image/webp" };
            if (!allowedTypes.Contains(file.ContentType))
                return BadRequest(new { message = "Invalid file type" });

            // Validate file size (max 10MB)
            if (file.Length > 10 * 1024 * 1024)
                return BadRequest(new { message = "File too large" });

            // Upload file
            var uploadResult = await _fileService.UploadImageAsync(file);

            var response = new
            {
                success = true,
                data = new
                {
                    fileId = uploadResult.FileId,
                    fileName = file.FileName,
                    fileUrl = uploadResult.FileUrl,
                    fileSize = file.Length,
                    contentType = file.ContentType,
                    uploadedAt = DateTime.UtcNow
                },
                message = "File uploaded successfully"
            };

            return Ok(response);
        }
        catch (Exception ex)
        {
            return StatusCode(500, new { message = "File upload failed", error = ex.Message });
        }
    }
}
```

## Real-time Communication (SignalR)

### Connection Hub
Real-time notifications for solution processing updates.

**Implementation:**
```csharp
[Authorize]
public class NotificationHub : Hub
{
    public async Task JoinUserGroup(string userId)
    {
        await Groups.AddToGroupAsync(Context.ConnectionId, $"user_{userId}");
    }

    public async Task LeaveUserGroup(string userId)
    {
        await Groups.RemoveFromGroupAsync(Context.ConnectionId, $"user_{userId}");
    }

    public override async Task OnDisconnectedAsync(Exception exception)
    {
        // Clean up user groups
        var userId = Context.User?.FindFirst(ClaimTypes.NameIdentifier)?.Value;
        if (userId != null)
        {
            await Groups.RemoveFromGroupAsync(Context.ConnectionId, $"user_{userId}");
        }
        
        await base.OnDisconnectedAsync(exception);
    }
}

// Service for sending notifications
public class NotificationService : INotificationService
{
    private readonly IHubContext<NotificationHub> _hubContext;

    public async Task NotifySolutionCompleted(string userId, Guid jobId, SolutionResult result)
    {
        await _hubContext.Clients.Group($"user_{userId}").SendAsync("SolutionCompleted", new
        {
            jobId = jobId,
            status = "completed",
            confidence = result.Confidence,
            processingTime = result.ProcessingTime,
            completedAt = DateTime.UtcNow
        });
    }

    public async Task NotifySolutionProgress(string userId, Guid jobId, string stage, int progress)
    {
        await _hubContext.Clients.Group($"user_{userId}").SendAsync("SolutionProgress", new
        {
            jobId = jobId,
            stage = stage,
            progress = progress,
            updatedAt = DateTime.UtcNow
        });
    }
}
```

## Health Check Endpoints

### GET /api/health
Service health check endpoint.

**Response (200 OK):**
```json
{
  "status": "Healthy",
  "checks": {
    "database": {
      "status": "Healthy",
      "responseTime": 45
    },
    "redis": {
      "status": "Healthy",
      "responseTime": 12
    },
    "ml_service": {
      "status": "Healthy",
      "responseTime": 234,
      "lastCheck": "2024-01-15T10:30:00Z"
    },
    "rabbitmq": {
      "status": "Healthy",
      "responseTime": 23
    }
  },
  "totalDuration": 314,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Implementation:**
```csharp
// Startup configuration
builder.Services.AddHealthChecks()
    .AddDbContext<ApplicationDbContext>("database")
    .AddMySql(builder.Configuration.GetConnectionString("DefaultConnection"), "database")
    .AddRedis(builder.Configuration.GetConnectionString("Redis"), "redis")
    .AddCheck<MLServiceHealthCheck>("ml_service")
    .AddRabbitMQ(builder.Configuration.GetConnectionString("RabbitMQ"), name: "rabbitmq");

// Custom health check for ML service
public class MLServiceHealthCheck : IHealthCheck
{
    private readonly IMLServiceClient _mlServiceClient;

    public async Task<HealthCheckResult> CheckHealthAsync(HealthCheckContext context, 
        CancellationToken cancellationToken = default)
    {
        try
        {
            var healthResult = await _mlServiceClient.CheckHealthAsync();
            
            if (healthResult.IsHealthy)
            {
                return HealthCheckResult.Healthy("ML Service is healthy", 
                    new Dictionary<string, object>
                    {
                        ["responseTime"] = healthResult.ResponseTime,
                        ["lastCheck"] = DateTime.UtcNow
                    });
            }

            return HealthCheckResult.Unhealthy("ML Service is unhealthy", 
                new Exception(healthResult.ErrorMessage));
        }
        catch (Exception ex)
        {
            return HealthCheckResult.Unhealthy("Failed to connect to ML Service", ex);
        }
    }
}
```

## Error Handling & Response Format

### Global Exception Handler

**Implementation:**
```csharp
public class GlobalExceptionMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<GlobalExceptionMiddleware> _logger;

    public async Task InvokeAsync(HttpContext context)
    {
        try
        {
            await _next(context);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "An unhandled exception occurred");
            await HandleExceptionAsync(context, ex);
        }
    }

    private static async Task HandleExceptionAsync(HttpContext context, Exception exception)
    {
        context.Response.ContentType = "application/json";

        var response = new
        {
            success = false,
            error = new
            {
                message = GetErrorMessage(exception),
                code = GetErrorCode(exception),
                timestamp = DateTime.UtcNow,
                traceId = context.TraceIdentifier
            }
        };

        context.Response.StatusCode = GetStatusCode(exception);

        var jsonResponse = JsonSerializer.Serialize(response, new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase
        });

        await context.Response.WriteAsync(jsonResponse);
    }

    private static string GetErrorMessage(Exception exception)
    {
        return exception switch
        {
            ValidationException => exception.Message,
            UnauthorizedAccessException => "Unauthorized access",
            NotFoundException => "Resource not found",
            MLServiceException => "ML processing service unavailable",
            _ => "An internal server error occurred"
        };
    }

    private static int GetStatusCode(Exception exception)
    {
        return exception switch
        {
            ValidationException => 400,
            UnauthorizedAccessException => 401,
            NotFoundException => 404,
            MLServiceException => 503,
            _ => 500
        };
    }
}
```

## API Security Implementation

### Rate Limiting

```csharp
// Configure rate limiting
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = 429;
    options.GlobalLimiter = PartitionedRateLimiter.Create<HttpContext, string>(httpContext =>
        RateLimitPartition.GetFixedWindowLimiter(
            partitionKey: httpContext.User.Identity?.Name ?? httpContext.Request.Headers.Host.ToString(),
            factory: partition => new FixedWindowRateLimiterOptions
            {
                AutoReplenishment = true,
                PermitLimit = 100,
                Window = TimeSpan.FromMinutes(1)
            }));
});

// Apply rate limiting to endpoints
[EnableRateLimiting("DefaultPolicy")]
[HttpPost("solve")]
public async Task<IActionResult> SolveProblem([FromForm] SolveProblemRequest request)
{
    // Implementation
}
```

### Input Validation

```csharp
public class SolveProblemRequest
{
    [Required]
    public IFormFile Image { get; set; }

    [Range(1, 12)]
    public int Grade { get; set; }

    [Required]
    [StringLength(50)]
    public string Subject { get; set; }

    [RegularExpression("^(low|normal|high)$")]
    public string Urgency { get; set; } = "normal";
}

public class RegisterRequest
{
    [Required]
    [StringLength(50, MinimumLength = 3)]
    public string Username { get; set; }

    [Required]
    [EmailAddress]
    public string Email { get; set; }

    [Required]
    [StringLength(100, MinimumLength = 8)]
    [RegularExpression(@"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\da-zA-Z]).{8,}$")]
    public string Password { get; set; }

    [Required]
    [StringLength(50)]
    public string FirstName { get; set; }

    [Required]
    [StringLength(50)]
    public string LastName { get; set; }

    [Range(1, 12)]
    public int Grade { get; set; }
}
```