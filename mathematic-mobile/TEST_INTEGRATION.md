# Integration Testing Guide

## Step-by-Step Integration Test

### 1. Start All Services

```bash
# Terminal 1: Start MySQL
docker run --name test-mysql \
  -e MYSQL_ROOT_PASSWORD=Mysql@2025 \
  -e MYSQL_DATABASE=MathematicsSolverDb \
  -p 3306:3306 -d mysql:8.0

# Wait for MySQL to be ready (30 seconds)
sleep 30

# Terminal 2: Start Python ML Service
cd llmOCR
uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --reload

# Terminal 3: Start .NET Backend
cd backend/src/Presentation
dotnet run

# Terminal 4: Start React Native Frontend
cd frontend
npx expo start
```

### 2. Test Backend API (via Swagger)

Visit: `http://localhost:8001/swagger`

#### 2.1 Register User
```json
POST /api/auth/register
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "Test123!",
  "confirmPassword": "Test123!"
}

Response: { "token": "eyJ...", "user": {...} }
```

#### 2.2 Login
```json
POST /api/auth/login
{
  "username": "testuser",
  "password": "Test123!"
}

Response: { "token": "eyJ...", "user": {...} }
```

**Copy the JWT token for next steps**

#### 2.3 Submit Problem
```
POST /api/problem
Authorization: Bearer {your-jwt-token}
Content-Type: multipart/form-data

FormData:
  ImageFile: [Select a JPG/PNG image file]
  Category: "Algebra"
  Description: "Solve for x"
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Problem submitted successfully",
  "problem": {
    "id": "guid-here",
    "userId": "guid-here",
    "imageUrl": "http://localhost:8001/uploads/images/abc123.jpg",
    "category": "Algebra",
    "status": "Completed",  // or "Processing" if ML is slow
    "description": "Solve for x",
    "createdAt": "2025-01-22T...",
    "solution": {
      "id": "guid-here",
      "steps": [
        {
          "stepNumber": 1,
          "description": "Step 1 text",
          "formula": null,
          "explanation": null
        }
      ],
      "confidence": 0.85,
      "additionalNotes": "Final Answer: x = 5"
    }
  }
}
```

### 3. Verify Integration Points

#### 3.1 Check Image Upload
```bash
# Image should exist in uploads directory
ls backend/src/Presentation/uploads/images/
# Should show the uploaded file
```

#### 3.2 Check ML Service Logs
```bash
# In Terminal 2 (ML service), you should see:
INFO:     [POST] /solution/ocr-solve
INFO:     Processing image from URL: http://localhost:8001/uploads/images/abc123.jpg
INFO:     OCR completed with confidence: 0.95
INFO:     Solution generated with 3 steps
```

#### 3.3 Check Database
```bash
# Connect to MySQL
docker exec -it test-mysql mysql -uroot -pMysql@2025 MathematicsSolverDb

# Check records
SELECT Id, Status, Category FROM Problems;
SELECT Id, ProblemId, Confidence FROM Solutions;
```

### 4. Test Frontend Integration

#### 4.1 On Mobile Device/Emulator
1. Open the app
2. Register/Login with the same credentials
3. Navigate to **Camera** tab
4. Take a photo of a math problem
5. Wait for processing overlay
6. Should see success alert with "View Solution" button
7. Click "View Solution"
8. Should navigate to Solution screen with steps

#### 4.2 Expected Frontend Flow
```
CameraScreen.takePicture()
  → dispatch(submitProblem({ imageUri, category, description }))
  → problemService.submitProblem()
  → POST http://localhost:8001/api/problem
  → Backend processes (see step 2.3)
  → Response received
  → Redux state updated
  → Alert shown
  → Navigation to Solution screen
```

### 5. Common Issues & Solutions

#### Issue: "Failed to submit problem"
**Causes:**
- Backend not running
- Wrong API URL in frontend
- JWT token expired

**Solutions:**
```bash
# Check backend is running
curl http://localhost:8001/api/health

# Check frontend API URL
# frontend/src/services/apiClient.js should have:
baseURL: 'http://YOUR_IP:8001/api'  # Not localhost if using physical device
```

#### Issue: "ML service not responding"
**Causes:**
- ML service not started
- Models not loaded yet
- Python dependencies missing

**Solutions:**
```bash
# Check ML service health
curl http://localhost:8002/health

# Check ML service logs for errors
# Wait 30-60 seconds for models to load
```

#### Issue: "Image upload fails"
**Causes:**
- Uploads directory doesn't exist
- No write permissions
- File too large (>10MB)

**Solutions:**
```bash
# Create directory and set permissions
mkdir -p backend/src/Presentation/uploads/images
chmod 777 backend/src/Presentation/uploads/images
```

#### Issue: "Database connection failed"
**Causes:**
- MySQL not running
- Wrong connection string
- Database not created

**Solutions:**
```bash
# Check MySQL is running
docker ps | grep test-mysql

# Check database exists
docker exec test-mysql mysql -uroot -pMysql@2025 -e "SHOW DATABASES;"
```

### 6. Success Criteria

✅ User can register and login
✅ Backend returns JWT token
✅ User can submit problem via Swagger
✅ Image is saved to uploads directory
✅ ML service is called and returns solution
✅ Solution is saved to database
✅ Frontend camera captures and submits image
✅ User sees success message
✅ User can view solution on Solution screen

---

## Quick Verification Script

```bash
#!/bin/bash

echo "Testing Backend Health..."
curl -f http://localhost:8001/api/auth/login || echo "❌ Backend not responding"

echo "\nTesting ML Service Health..."
curl -f http://localhost:8002/health || echo "❌ ML Service not responding"

echo "\nTesting MySQL Connection..."
docker exec test-mysql mysql -uroot -pMysql@2025 -e "SELECT 1;" || echo "❌ MySQL not responding"

echo "\n✅ All services are up!"
```

Save as `test-services.sh`, make executable, and run:
```bash
chmod +x test-services.sh
./test-services.sh
```
