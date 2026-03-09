# 🧪 Priority 1 Testing Guide

**Quick Start Guide for Testing Priority 1 Implementation**

---

## ✅ What's Already Working

Based on our verification, these items are **already complete**:

1. ✅ All ML/OCR Service utility files exist
2. ✅ API endpoints are aligned (frontend ↔ backend)
3. ✅ Model download scripts ready
4. ✅ Docker configuration in place

---

## 🎯 Quick Test (5 minutes)

### Step 1: Run Verification Script

```bash
cd /home/tuanph/TuanPH/all_projects/mathematic-mobile

# Run the verification
./test-priority-1.sh
```

**Expected Output:**
```
✅ image_processing.py exists
✅ math_parser.py exists
✅ settings.py exists
✅ middleware.py exists
✅ exceptions.py exists
✅ download_models.py exists
✅ Auth uses /api/v1/auth
✅ Problem uses /api/v1/problems
✅ Frontend uses /api/v1
```

---

## 🔧 Fix the Only Blocker: EF Core Migrations

### Option A: Auto-Create Database (Quickest for Testing)

Add this code to enable automatic database creation:

**File: `backend/microservices/auth-service/Program.cs`**

Add before `app.Run()`:

```csharp
// Auto-create database (for development/testing)
using var scope = app.Services.CreateScope();
var authDb = scope.ServiceProvider.GetRequiredService<AuthDbContext>();
await authDb.Database.EnsureCreatedAsync();
Console.WriteLine("✅ Auth Database created/verified");
```

**File: `backend/microservices/problem-service/Program.cs`**

Add before `app.Run()`:

```csharp
// Auto-create database (for development/testing)
using var scope = app.Services.CreateScope();
var problemDb = scope.ServiceProvider.GetRequiredService<ProblemDbContext>();
await problemDb.Database.EnsureCreatedAsync();
Console.WriteLine("✅ Problem Database created/verified");
```

### Option B: Create Proper Migrations (Recommended for Production)

```bash
# Install EF Core tools (if not already installed)
dotnet tool install --global dotnet-ef

# Create migrations
cd /home/tuanph/TuanPH/all_projects/mathematic-mobile/backend/scripts
./create-migrations.sh
```

---

## 🚀 Test Services Locally

### 1. Start MySQL Database

```bash
# Using Docker (recommended)
docker run -d \
  --name math-mysql-test \
  -e MYSQL_ROOT_PASSWORD=Mysql_2025 \
  -e MYSQL_DATABASE=MathematicsSolverDb \
  -e MYSQL_USER=mathematic_user \
  -e MYSQL_PASSWORD=Mysql_2025 \
  -p 3310:3306 \
  mysql:8.0

# Wait for MySQL to start
sleep 10

# Test connection
docker exec -it math-mysql-test mysql -umathematic_user -pMysql_2025 MathematicsSolverDb -e "SELECT 1;"
```

### 2. Test Auth Service

```bash
cd /home/tuanph/TuanPH/all_projects/mathematic-mobile/backend/microservices/auth-service

# Start the service
dotnet run
```

**Expected Output:**
```
✅ Auth Database created/verified
Now listening on: http://0.0.0.0:8001
Application started. Press Ctrl+C to shut down.
```

**In another terminal, test the service:**

```bash
# Health check
curl http://localhost:8001/health

# Expected: {"status":"healthy","service":"auth-service",...}

# Test registration
curl -X POST http://localhost:8001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "Test123!",
    "fullName": "Test User"
  }'

# Expected: Success response with user data
```

### 3. Test Problem Service

```bash
cd /home/tuanph/TuanPH/all_projects/mathematic-mobile/backend/microservices/problem-service

# Start the service
dotnet run
```

**Expected Output:**
```
✅ Problem Database created/verified
Now listening on: http://0.0.0.0:8002
Application started. Press Ctrl+C to shut down.
```

**In another terminal, test the service:**

```bash
# Health check
curl http://localhost:8002/health

# Expected: {"status":"healthy","service":"problem-service",...}
```

### 4. Test ML/OCR Service

```bash
cd /home/tuanph/TuanPH/all_projects/mathematic-mobile/llmOCR

# Activate virtual environment
source venv/bin/activate  # or create one: python3 -m venv venv && source venv/bin/activate

# Install dependencies (if not already done)
pip install -r requirements.txt

# Start the service
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8002
```

**Expected Output:**
```
INFO:     Started server process
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8002
```

**Test the service:**

```bash
# Health check
curl http://localhost:8002/health

# Expected: {"status":"healthy","service":"math-llm-ocr",...}

# Get service info
curl http://localhost:8002/info
```

---

## ✅ Success Checklist

Priority 1 is working when you can:

- [ ] Run `./test-priority-1.sh` with all tests passing
- [ ] Start Auth Service without errors
- [ ] Start Problem Service without errors
- [ ] Start ML Service without errors
- [ ] Call `GET /health` on all services successfully
- [ ] Register a new user via Auth Service
- [ ] See database tables created automatically

---

## 🐛 Troubleshooting

### Issue: "dotnet-ef command not found"

**Solution:**
```bash
dotnet tool install --global dotnet-ef
```

### Issue: "Port already in use"

**Solution:**
```bash
# Find process using the port
lsof -i :8001
lsof -i :8002

# Kill the process
kill -9 <PID>
```

### Issue: "Cannot connect to database"

**Solutions:**
1. Check if MySQL is running: `docker ps | grep mysql`
2. Verify connection string in appsettings.json
3. Check database credentials match

### Issue: "ModuleNotFoundError: No module named..."

**Solution:**
```bash
cd llmOCR
source venv/bin/activate
pip install -r requirements.txt
```

---

## 📊 Test Results Template

Use this template to document your test results:

```markdown
## Test Results - [Date]

**Tester:** [Your Name]

### File Structure Test
- [ ] All ML service files exist
- [ ] All backend controllers exist
- [ ] All frontend services exist

### Service Startup Test
- [ ] Auth Service starts successfully
- [ ] Problem Service starts successfully
- [ ] ML Service starts successfully

### API Endpoint Test
- [ ] Auth health endpoint works
- [ ] Problem health endpoint works
- [ ] ML health endpoint works
- [ ] User registration works
- [ ] API endpoints respond correctly

### Issues Found
[List any issues encountered]

### Next Steps
[What needs to be fixed or tested next]
```

---

## 🎉 After Successful Testing

Once all tests pass:

1. ✅ **Priority 1 is COMPLETE**
2. 📝 Update `project_status.md` to reflect completion
3. ➡️ **Move to Priority 2 items**

---

Good luck with testing! 🚀
