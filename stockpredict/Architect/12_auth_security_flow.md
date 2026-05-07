# 12 — Auth & Security Flow

## 12.1 JWT Architecture — Multi-Service Validation

```mermaid
flowchart TD
    subgraph AUTH_SVC["auth-service (JWT ISSUER)"]
        USER_DB[("users table\nhashed_password\nrole")]
        RT_DB[("refresh_tokens table\ntoken | expires_at | is_revoked")]
        JWT_MGR["JWTManager\n(stock-common/auth/jwt.py)"]
        PW_HASH["PasswordManager\nbcrypt hash/verify"]

        LOGIN["POST /auth/login"]
        REFRESH["POST /auth/refresh"]
        REGISTER["POST /auth/register"]
        RESET["POST /auth/reset-password"]
    end

    subgraph SHARED_SECRET["Shared Configuration"]
        SECRET["JWT_SECRET_KEY\n(same env var\nacross ALL services)"]
        ALGO["Algorithm: HS256\nAccess token TTL: 24h\nRefresh token TTL: 30d"]
    end

    subgraph OTHER_SVCS["Other Services (JWT VALIDATORS)"]
        STOCK_V["stock-data-service"]
        PORT_V["portfolio-service"]
        PRED_V["prediction-service"]
        ANAL_V["analysis-service"]
        COMMON_VALIDATOR["stock-common/auth/middleware.py\nAuthMiddleware.verify_token(token)\n→ JWTPayload{sub, role, exp, iat, jti}"]
    end

    subgraph TOKEN_FLOW["Token Flow"]
        ACCESS_T["Access Token\nJWT HS256\nPayload:\n  sub: user_id\n  role: user|admin|premium\n  exp: now+24h\n  iat: now\n  jti: uuid"]
        REFRESH_T["Refresh Token\nOpaque random string\nStored in DB with user_id\nTTL: 30 days"]
    end

    LOGIN --> PW_HASH
    PW_HASH --> USER_DB
    USER_DB --> JWT_MGR
    JWT_MGR --> ACCESS_T
    JWT_MGR --> REFRESH_T
    REFRESH_T --> RT_DB

    REFRESH --> RT_DB
    RT_DB --> JWT_MGR

    SECRET --> JWT_MGR
    SECRET --> COMMON_VALIDATOR
    ALGO --> JWT_MGR
    ALGO --> COMMON_VALIDATOR

    COMMON_VALIDATOR --> STOCK_V & PORT_V & PRED_V & ANAL_V

    style AUTH_SVC fill:#fef9c3,stroke:#ca8a04
    style SHARED_SECRET fill:#fee2e2,stroke:#ef4444
    style OTHER_SVCS fill:#dbeafe,stroke:#3b82f6
```

---

## 12.2 Login & Token Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant SPA as React SPA\n(AuthContext)
    participant TK as Traefik
    participant AUTH as auth-service
    participant DB as MySQL

    Note over User, DB: --- Registration ---
    User->>SPA: Fill register form\n{username, email, password}
    SPA->>TK: POST /stock_helper/api/v2/auth/register
    TK->>AUTH: Forward (no auth required)
    AUTH->>AUTH: bcrypt.hash(password, rounds=12)
    AUTH->>DB: INSERT INTO users\n(username, email, hashed_password, role='user')
    DB-->>AUTH: user created
    AUTH-->>SPA: {user_id, username, email}

    Note over User, DB: --- Login ---
    User->>SPA: Submit login form\n{username, password}
    SPA->>TK: POST /stock_helper/api/v2/auth/login
    TK->>AUTH: Forward
    AUTH->>DB: SELECT * FROM users WHERE username=?
    DB-->>AUTH: user record
    AUTH->>AUTH: bcrypt.verify(password, hashed_password)
    AUTH->>AUTH: jwt.encode({sub, role, exp=+24h, jti=uuid})
    AUTH->>AUTH: generate refresh_token = secrets.token_hex(32)
    AUTH->>DB: INSERT INTO refresh_tokens\n(user_id, token, expires_at=+30d)
    AUTH-->>SPA: {access_token, refresh_token, user: {id, username, role}}
    SPA->>SPA: localStorage.setItem('access_token', ...)\nlocalStorage.setItem('refresh_token', ...)
    SPA->>SPA: AuthContext.setUser({id, role})

    Note over User, DB: --- Authenticated API call ---
    User->>SPA: Trigger some action
    SPA->>TK: GET /stock_helper/api/v2/portfolio\nAuthorization: Bearer <access_token>
    TK->>TK: Extract Bearer token
    TK->>TK: jwt.decode(token, JWT_SECRET_KEY)\nVerify signature + expiry
    TK->>AUTH: Forward + X-User-Id header

    Note over User, DB: --- Token Refresh ---
    SPA->>TK: Any request → 401 (token expired)
    TK-->>SPA: 401 Unauthorized
    SPA->>SPA: Detect 401, read refresh_token from localStorage
    SPA->>TK: POST /auth/refresh {refresh_token}
    TK->>AUTH: Forward
    AUTH->>DB: SELECT * FROM refresh_tokens WHERE token=? AND is_revoked=false
    DB-->>AUTH: token record
    AUTH->>AUTH: Check expires_at > now
    AUTH->>AUTH: Issue new access_token
    AUTH-->>SPA: {access_token}
    SPA->>SPA: Update localStorage\nRetry original request

    Note over User, DB: --- Logout ---
    User->>SPA: Click logout
    SPA->>TK: POST /auth/logout {refresh_token}
    TK->>AUTH: Forward
    AUTH->>DB: UPDATE refresh_tokens SET is_revoked=true WHERE token=?
    AUTH-->>SPA: 200 OK
    SPA->>SPA: localStorage.clear()\nAuthContext.setUser(null)\nredirect to /login
```

---

## 12.3 Role-Based Access Control

```mermaid
flowchart TD
    subgraph ROLES["User Roles"]
        R_USER["role: user\n(default)\nBasic access"]
        R_PREMIUM["role: premium\nAI insights\nAdvanced predictions"]
        R_ADMIN["role: admin\nUser management\nSystem monitoring"]
    end

    subgraph PROTECTED["Protected Endpoint Categories"]
        P1["Public (no auth)\nPOST /auth/login\nPOST /auth/register\nGET /health/*"]
        P2["Authenticated (any role)\nGET /stocks/*\nGET /companies/*\nGET /market/*\nGET /analysis/*"]
        P3["Premium + Admin\nGET /ai/insight/*\nGET /ai/market-overview\nPOST /ai/ask\nPOST /predict"]
        P4["Admin only\nUser management\nSystem config\nDELETE operations"]
    end

    subgraph ENFORCEMENT["Enforcement Points"]
        MW["FastAPI Auth Middleware\n(stock-common/auth/middleware.py)\n\nif endpoint requires auth:\n  token = extract_bearer(request)\n  payload = jwt.decode(token)\n  if required_role not in payload.role:\n    raise HTTPException(403)"]
    end

    R_USER --> P2
    R_PREMIUM --> P2 & P3
    R_ADMIN --> P2 & P3 & P4
    P1 -.->|"bypasses"| MW
    P2 & P3 & P4 --> MW
```

---

## 12.4 Security Architecture Overview

```mermaid
mindmap
  root((Security))
    Authentication
      JWT HS256
        Shared secret across services
        24h access token TTL
        30d refresh token
        Token rotation on refresh
      Password Security
        bcrypt hash rounds=12
        No plaintext storage
        Reset via email token
    Transport Security
      HTTPS/TLS
        Traefik TLS termination
        Self-signed cert (dev)
        Cert from CA (prod)
      CORS
        Configurable origins
        Preflight handling
    API Security
      Input Validation
        Pydantic schema validation
        Type checking on all inputs
        SQL injection prevention via SQLAlchemy ORM
      Rate Limiting
        Planned via Traefik middleware
        Per-IP limits
    Secrets Management
      Environment Variables
        JWT_SECRET_KEY
        DB credentials
        API keys (OpenAI, Anthropic)
        Never in code or VCS
      Docker Secrets
        .env files excluded from git
        .env.example as template
    Network Security
      Internal Docker Network
        Services not exposed externally
        Only Traefik port 8004 public
      Database
        MySQL not externally accessible
        Redis not externally accessible
        RabbitMQ management on 15672
```
