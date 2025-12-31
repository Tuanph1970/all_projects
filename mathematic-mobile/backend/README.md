# Mathematics Solver Backend API

A comprehensive .NET Core 8.0 Web API service implementing Clean Architecture principles with CQRS pattern for a mathematics problem-solving application.

## Architecture

This project follows **Clean Architecture** with **Domain-Driven Design (DDD)** principles:

- **Domain Layer**: Core business entities, value objects, and domain services
- **Application Layer**: Use cases, CQRS commands/queries, and application services
- **Infrastructure Layer**: Data access, external services, and cross-cutting concerns
- **Presentation Layer**: Web API controllers, middleware, and presentation logic

## Features

### Core Authentication System ✅
- User registration with validation
- JWT-based authentication
- Password hashing with BCrypt
- User management and profile handling
- Token validation and user claims

### Security Features
- JWT token authentication and authorization
- Password strength validation
- Secure password hashing with BCrypt
- Input validation and sanitization
- Global exception handling middleware

### Database
- Entity Framework Core with MySQL
- Code-First approach with migrations
- Repository pattern implementation
- Unit of Work pattern for transaction management

## Getting Started

### Prerequisites
- .NET 8.0 SDK
- MySQL Server
- Visual Studio 2022 or VS Code

### Installation

1. Clone the repository
```bash
git clone <repository-url>
cd backend
```

2. Update database connection string in `appsettings.json`:
```json
{
  "ConnectionStrings": {
    "DefaultConnection": "Server=localhost;Database=MathematicsSolver;User=root;Password=yourpassword;Port=3306;"
  }
}
```

3. Build the solution:
```bash
dotnet build
```

4. Run the application:
```bash
cd src/Presentation
dotnet run
```

The API will be available at:
- HTTP: `http://localhost:5000`
- HTTPS: `https://localhost:5001`
- Swagger UI: `https://localhost:5001/swagger`

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Authenticate user login

## Project Structure

```
src/
├── Domain/                     # Domain layer (entities, value objects)
│   ├── Entities/
│   │   ├── User.cs
│   │   ├── Problem.cs
│   │   └── Solution.cs
│   ├── ValueObjects/
│   │   └── SolutionStep.cs
│   ├── Enums/
│   │   └── ProblemStatus.cs
│   └── Common/
│       ├── BaseEntity.cs
│       └── ValueObject.cs
├── Application/                # Application layer (use cases)
│   ├── Features/
│   │   └── Authentication/
│   │       ├── Commands/
│   │       ├── Handlers/
│   │       └── Validators/
│   ├── Common/
│   │   ├── Interfaces/
│   │   ├── Behaviors/
│   │   └── Exceptions/
│   └── DTOs/
├── Infrastructure/             # Infrastructure layer (data access, external services)
│   ├── Persistence/
│   │   ├── Repositories/
│   │   ├── Configurations/
│   │   └── ApplicationDbContext.cs
│   └── Services/
│       ├── BCryptPasswordHasher.cs
│       └── JwtTokenGenerator.cs
└── Presentation/              # Presentation layer (controllers, middleware)
    ├── Controllers/
    │   └── AuthController.cs
    ├── Middleware/
    │   └── ExceptionHandlingMiddleware.cs
    └── Program.cs
```

## Technologies Used

- **.NET 8.0** - Web API framework
- **Entity Framework Core** - ORM for database operations
- **MySQL** - Primary database
- **MediatR** - CQRS and mediator pattern implementation
- **FluentValidation** - Input validation
- **JWT Bearer Authentication** - Token-based authentication
- **BCrypt.Net** - Password hashing
- **Swagger/OpenAPI** - API documentation
- **AutoMapper** - Object mapping (future implementation)

## Design Patterns

- **Clean Architecture** - Separation of concerns and dependency inversion
- **CQRS** - Command Query Responsibility Segregation
- **Repository Pattern** - Data access abstraction
- **Unit of Work** - Transaction management
- **Mediator Pattern** - Decoupled communication between components
- **Strategy Pattern** - Multiple authentication methods support
- **Factory Pattern** - Service and handler creation

## Development Guidelines

### Code Style
- Follow C# coding conventions
- Use meaningful names for variables and methods
- Implement proper error handling
- Write unit tests for business logic
- Document public APIs with XML comments

### Security Best Practices
- Never expose sensitive information in responses
- Validate all inputs
- Use parameterized queries to prevent SQL injection
- Implement proper authentication and authorization
- Log security events for monitoring

## Future Enhancements

The current implementation covers the Core Authentication System as specified in Phase 1.2 of the roadmap. Future phases will include:

- **Problem Management**: OCR integration and problem-solving workflow
- **ML Service Integration**: Connection to Python ML service
- **Real-time Features**: SignalR for real-time communication
- **Advanced Security**: OAuth integration and refresh tokens
- **Performance Optimization**: Caching and response optimization
- **Monitoring**: Application insights and health checks

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Support

For support and questions, please contact the development team or create an issue in the repository.