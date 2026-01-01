# Mathematics Solver Backend - Microservices Architecture

A scalable microservices-based backend for a mathematics problem-solving application.

## Architecture

```
                    ┌─────────────────┐
                    │  Traefik Gateway │
                    │    (Port 8003)   │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Auth Service │  │ Problem Service │  │ Solution Service│
│   (.NET 9.0)  │  │   (.NET 9.0)    │  │ (Python/FastAPI)│
│   Port 8001   │  │   Port 8002     │  │   Port 8003     │
└───────────────┘  └─────────────────┘  └─────────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
               ┌────▼────┐      ┌─────▼────┐
               │  MySQL  │      │  Redis   │
               │  :3310  │      │  :6380   │
               └─────────┘      └──────────┘
```

## Services

### Auth Service (.NET 9.0)
- User registration and login
- JWT token generation and validation
- Password hashing with BCrypt
- User profile management

### Problem Service (.NET 9.0)
- Problem submission (text/image)
- Problem history and status tracking
- User problem management
- Integration with Solution Service

### Solution Service (Python/FastAPI)
- OCR for image-based math problems (Tesseract)
- Mathematical equation solving (SymPy)
- Step-by-step solution generation
- AI/ML integration ready (OpenAI, Anthropic)

## Quick Start

### Prerequisites
- Docker & Docker Compose
- 4GB+ RAM recommended

### Run All Services
```bash
cd backend
docker compose up -d --build
```

### Verify Services
```bash
# Check container status
docker ps --filter "name=math_"

# Test auth service
curl -X POST http://localhost:8003/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"Test12345","fullName":"Test User"}'

# Test problem creation (with JWT token)
curl -X POST http://localhost:8003/api/v1/problems \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Solve equation","description":"x^2 + 5x + 6 = 0"}'

# Test solution service
curl -X POST http://localhost:8003/api/v1/solutions/solve \
  -H "Content-Type: application/json" \
  -d '{"problem_id":1,"problem_text":"x^2 + 5*x + 6 = 0","user_id":1}'
```

## API Endpoints

All endpoints are accessed through Traefik gateway on port 8003.

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/auth/register | Register new user |
| POST | /api/v1/auth/login | User login |
| POST | /api/v1/auth/refresh | Refresh token |
| GET | /api/v1/users/profile | Get user profile |

### Problems
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/problems | List user problems |
| POST | /api/v1/problems | Create problem |
| GET | /api/v1/problems/{id} | Get problem details |
| DELETE | /api/v1/problems/{id} | Delete problem |

### Solutions
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/solutions/solve | Solve a problem |
| POST | /api/v1/solutions/ocr | Extract text from image |
| GET | /api/v1/solutions/{id} | Get solution details |

## Configuration

### Environment Variables (.env)
```env
# Database
DB_NAME=MathematicsSolverDb
DB_USER=mathematic_user
DB_PASSWORD=Mysql_2025
MYSQL_ROOT_PASSWORD=Mysql_2025

# Ports
GATEWAY_PORT=8003
MATH_DB_PORT=3310
MATH_REDIS_PORT=6380
TRAEFIK_DASHBOARD_PORT=8083

# JWT
JWT_SECRET_KEY=your-super-secret-key-minimum-32-chars

# AI Services (optional)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

## Project Structure

```
backend/
├── docker-compose.yml          # Main compose file
├── .env                        # Environment variables
├── .env.example                # Example env file
├── microservices/
│   ├── auth-service/           # .NET Authentication service
│   │   ├── Controllers/
│   │   ├── Models/
│   │   ├── Services/
│   │   ├── Data/
│   │   ├── DTOs/
│   │   ├── Program.cs
│   │   └── Dockerfile
│   ├── problem-service/        # .NET Problem management
│   │   ├── Controllers/
│   │   ├── Models/
│   │   ├── Services/
│   │   ├── Data/
│   │   ├── DTOs/
│   │   ├── Program.cs
│   │   └── Dockerfile
│   └── solution-service/       # Python ML/AI service
│       ├── app/
│       │   ├── main.py
│       │   ├── services/
│       │   └── database.py
│       ├── requirements.txt
│       └── Dockerfile
└── scripts/                    # Database scripts
```

## Development

### Adding New Microservices
1. Create directory under `microservices/`
2. Add Dockerfile
3. Add service to `docker-compose.yml`
4. Configure Traefik labels for routing

### Traefik Routing
Each service uses unique router prefixes to avoid conflicts:
- `math-auth` - Auth service routes
- `math-problem` - Problem service routes
- `math-solution` - Solution service routes

### Shared Database
All services connect to the same MySQL database. Each service manages its own tables.

## Monitoring

### Traefik Dashboard
Access at `http://localhost:8083`

### Service Health Checks
```bash
# Auth service
curl http://localhost:8003/api/v1/auth/health

# Problem service (internal)
docker exec math_problem_service curl http://localhost:8002/health

# Solution service (internal)
docker exec math_solution_service curl http://localhost:8003/health
```

## Technologies

- **Gateway**: Traefik v2.11
- **Auth/Problem Services**: .NET 9.0, Entity Framework Core, Pomelo MySQL
- **Solution Service**: Python 3.11, FastAPI, SymPy, Tesseract OCR
- **Database**: MySQL 8.0
- **Cache**: Redis 7

## License

MIT License
