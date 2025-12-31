# Postman Testing Guide

## Quick Start

### Step 1: Import Files into Postman

1. Open Postman
2. Click **Import** button (top left)
3. Select **File** tab
4. Import both files:
   - `Mathematics_Solver_API.postman_collection.json`
   - `Mathematics_Solver_API.postman_environment.json`

### Step 2: Select Environment

1. In the top-right corner, click the environment dropdown
2. Select **"Mathematics Solver - Development"**
3. Verify `base_url` is set to `http://localhost:8001/api`

### Step 3: Start Backend Services

Before testing, ensure all services are running:

```bash
# Terminal 1: Start MySQL
docker run --name test-mysql \
  -e MYSQL_ROOT_PASSWORD=Mysql@2025 \
  -e MYSQL_DATABASE=MathematicsSolverDb \
  -p 3306:3306 -d mysql:8.0

# Wait 30 seconds for MySQL to initialize
sleep 30

# Terminal 2: Start Backend API
cd backend/src/Presentation
dotnet run

# Terminal 3: Start Python ML Service
cd llmOCR
uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --reload
```

---

## Testing Workflow

### Phase 1: Authentication Tests

#### 1.1 Register User
- **Folder**: Authentication
- **Request**: Register User
- **Action**: Click **Send**
- **Expected Result**:
  - Status: `200 OK`
  - Response includes `token` and `user` object
  - `auth_token` automatically saved to environment

#### 1.2 Login User
- **Folder**: Authentication
- **Request**: Login User
- **Action**: Click **Send**
- **Expected Result**:
  - Status: `200 OK`
  - Response includes `token` and `user` object
  - `auth_token` updated in environment

**Note**: All subsequent requests will automatically use the saved `auth_token`

---

### Phase 2: Problem Management Tests

#### 2.1 Submit Problem
- **Folder**: Problems
- **Request**: Submit Problem
- **Action**:
  1. Click **Body** tab
  2. Under `ImageFile`, click **Select Files**
  3. Choose a JPG/PNG image of a math problem
  4. Click **Send**
- **Expected Result**:
  - Status: `200 OK`
  - Response includes problem details with `id`, `imageUrl`, `status`
  - `problem_id` automatically saved to environment
  - Solution data included (or status shows "Processing")

**Expected Response Structure**:
```json
{
  "success": true,
  "message": "Problem submitted successfully",
  "problem": {
    "id": "guid-here",
    "userId": "guid-here",
    "imageUrl": "http://localhost:8001/uploads/images/abc123.jpg",
    "category": "Algebra",
    "status": "Completed",
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

#### 2.2 Get User Problems
- **Folder**: Problems
- **Request**: Get User Problems
- **Action**: Click **Send**
- **Expected Result**:
  - Status: `200 OK`
  - Paginated list of problems
  - Includes filtering options (category, status, search)

**Query Parameters** (optional):
- `page`: Page number (default: 1)
- `pageSize`: Items per page (default: 10)
- `category`: Filter by category (e.g., "Algebra")
- `status`: Filter by status (0=Pending, 1=Processing, 2=Completed, 3=Failed)
- `searchQuery`: Text search in descriptions

#### 2.3 Get Problem By ID
- **Folder**: Problems
- **Request**: Get Problem By ID
- **Action**: Click **Send** (uses saved `problem_id`)
- **Expected Result**:
  - Status: `200 OK`
  - Detailed problem with solution

#### 2.4 Delete Problem
- **Folder**: Problems
- **Request**: Delete Problem
- **Action**: Click **Send** (uses saved `problem_id`)
- **Expected Result**:
  - Status: `204 No Content`
  - Problem removed from database

#### 2.5 Retry Problem
- **Folder**: Problems
- **Request**: Retry Problem
- **Action**:
  1. Submit a new problem first (2.1)
  2. Click **Send** on Retry request
- **Expected Result**:
  - Status: `200 OK`
  - New solution generated
  - Updated problem status

---

### Phase 3: Health Check

#### 3.1 API Health
- **Folder**: Health Check
- **Request**: API Health
- **Action**: Click **Send**
- **Expected Result**:
  - Status: `200 OK`
  - Response: `"Healthy"` or status object

---

## Automated Test Scripts

Each request includes automated test scripts that:

✅ **Validate Response Status**: Checks for expected HTTP status codes
✅ **Validate JSON Structure**: Ensures response has correct fields
✅ **Auto-Save Variables**: Stores tokens and IDs for subsequent requests
✅ **Console Logging**: Displays detailed response information

**View Test Results**:
1. After sending a request, click **Test Results** tab
2. See pass/fail status for each test
3. Check **Console** (bottom left) for detailed logs

---

## Common Testing Scenarios

### Scenario 1: Complete User Journey
1. Register User → Login User
2. Submit Problem → View solution
3. Get User Problems → See history
4. Get Problem By ID → View details
5. Delete Problem → Clean up

### Scenario 2: Testing Error Handling
1. Login with wrong credentials → Expect `401 Unauthorized`
2. Submit without auth token → Expect `401 Unauthorized`
3. Get non-existent problem → Expect `404 Not Found`
4. Upload invalid file type → Expect `400 Bad Request`

### Scenario 3: Testing Pagination
1. Submit 15 problems
2. Get User Problems with `pageSize=10`
3. Verify `hasNextPage: true`
4. Change `page=2` → Get remaining items

### Scenario 4: Testing Filters
1. Submit problems with different categories
2. Use `category=Algebra` filter
3. Submit problems with different statuses
4. Use `status=2` filter (Completed)

---

## Troubleshooting

### Issue: "Could not send request"
**Cause**: Backend not running
**Solution**:
```bash
cd backend/src/Presentation
dotnet run
```
Verify at: http://localhost:8001/swagger

### Issue: "401 Unauthorized"
**Cause**: Missing or expired auth token
**Solution**:
1. Run **Login User** request again
2. Check environment variable `auth_token` is populated
3. Verify Bearer token in Authorization header

### Issue: "ML Service timeout"
**Cause**: ML service not running or slow
**Solution**:
```bash
cd llmOCR
uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --reload
```
Wait 30-60 seconds for models to load

### Issue: "Image upload fails"
**Cause**: Upload directory missing
**Solution**:
```bash
mkdir -p backend/src/Presentation/uploads/images
chmod 777 backend/src/Presentation/uploads/images
```

### Issue: "Database connection failed"
**Cause**: MySQL not running
**Solution**:
```bash
docker ps | grep test-mysql
# If not running, start it:
docker run --name test-mysql \
  -e MYSQL_ROOT_PASSWORD=Mysql@2025 \
  -e MYSQL_DATABASE=MathematicsSolverDb \
  -p 3306:3306 -d mysql:8.0
```

---

## Environment Variables Reference

| Variable | Description | Auto-Populated |
|----------|-------------|----------------|
| `base_url` | API base URL | No (preset to localhost:8001/api) |
| `auth_token` | JWT Bearer token | Yes (after login) |
| `problem_id` | Last created problem ID | Yes (after submit) |
| `user_id` | Current user ID | Yes (after register/login) |

**Manual Override**:
1. Click environment name in top-right
2. Edit variable values
3. Save changes

---

## Advanced Tips

### Tip 1: Test Different Image Types
Try uploading:
- Simple equations: `2x + 5 = 15`
- Complex equations: Quadratic formulas
- Handwritten math problems
- Printed textbook images

### Tip 2: Monitor ML Processing
Watch backend console logs to see:
```
INFO: Processing image from URL: http://localhost:8001/uploads/images/abc123.jpg
INFO: OCR completed with confidence: 0.95
INFO: Solution generated with 3 steps
```

### Tip 3: Use Postman Runner
1. Click **Runner** button (top right)
2. Select **Mathematics Solver API** collection
3. Configure iterations and delays
4. Run automated test suite

### Tip 4: Export Test Results
1. After running requests, click **Console**
2. Click **Download** to save logs
3. Use for bug reports or documentation

---

## Success Criteria Checklist

✅ User can register and login
✅ Backend returns valid JWT token
✅ User can submit problem with image
✅ Image is saved to uploads directory
✅ ML service processes image and returns solution
✅ Solution is saved to database
✅ User can retrieve problem list with pagination
✅ User can view individual problem details
✅ User can delete problems
✅ User can retry failed problems

---

## Next Steps After Manual Testing

Once manual testing is complete:

1. **Frontend Integration**: Test with React Native app
2. **E2E Testing**: Create automated test scripts
3. **Performance Testing**: Load testing with multiple users
4. **Security Testing**: Penetration testing and vulnerability scans
5. **Production Deployment**: Deploy to staging/production environment

---

## Additional Resources

- **API Documentation**: http://localhost:8001/swagger
- **Integration Guide**: `TEST_INTEGRATION.md`
- **Docker Setup**: `docker-compose.yml`
- **Roadmap**: `documents/app_roadmap.md`
