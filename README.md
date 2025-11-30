# Intelligent Content API

FastAPI-based service that authenticates users, stores their content, and augments it with AI-generated summaries and sentiment labels. The stack pairs PostgreSQL for relational data, Redis for caching, and Hugging Face's chat completions for AI enrichment.

## 1. Setup Instructions

### Local Python environment
1. **Prerequisites:** Python 3.9+, running PostgreSQL 18+, and Redis 7+. Create a database (default URL: `postgresql://postgres:mysecretpassword@localhost:5432/postgres`).
2. **Environment variables:** Copy `.env` (or create one) with at least:
   ```env
   SECRET_KEY=change-me
   HUGGINGFACE_API_KEY=hf_xxx
   DATABASE_URL=postgresql://<user>:<pass>@<host>:<port>/<db>
   REDIS_URL=redis://localhost:6379/0
   CACHE_ENABLED=True
   ```
3. **Install deps:**
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. **Run the API:**
   ```bash
   uvicorn app.main:app --reload
   ```
5. **Verify:** Visit `http://localhost:8000/docs` to exercise the endpoints (JWT auth flow + content routes).

### One liner setup using Docker / Docker Compose
1. Ensure Docker Desktop is running.
2. Build and start all services (API, Postgres, Redis):
   ```bash
   docker compose up --build
   ```
3. The API is exposed on `http://localhost:8000`, Postgres on `5432`, Redis on `6379`.
4. Stop everything with `docker compose down` (add `-v` to clear volumes).

## 2. API Documentation
- **Interactive docs:** FastAPI auto-generates Swagger UI at `GET /docs` and ReDoc at `GET /redoc`.
- **Auth Routes:**
  - `POST /signup` → create a user and returns a JWT.
  - `POST /login` → exchange credentials for a JWT.
- **Content Routes** (require `Authorization: Bearer <token>`):
  - `POST /contents` → store raw text, trigger background AI analysis.
  - `GET /contents` → list caller's content (Redis-cached for 5 minutes).
  - `GET /contents/{id}` → fetch a single entry (also cached).
  - `DELETE /contents/{id}` → remove content and invalidate cache. Summaries/sentiment are populated asynchronously.

## 3. Design Decisions
- **Database (single RDBMS choice):** I stayed with one consistent PostgreSQL instance so foreign keys between `users` and `contents` stay enforced at the database layer. Splitting data across heterogeneous stores (e.g., mixing document DBs) would complicate referential integrity and migrations.
- **AI integration:** The API calls Hugging Face's Router (`meta-llama/Meta-Llama-3-8B-Instruct`) asynchronously, wrapping the request in a background task. Responses are forced into a concise JSON schema, then mapped to enums so the DB always receives valid sentiment states. Failures fall back to a neutral placeholder to avoid blocking user flows.
- **Performance/caching:** Redis keeps per-user list/detail responses hot for five minutes. Mutations invalidate both the collection and item keys, ensuring consistency without re-querying Postgres on every GET.

---

## 4. Application Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT (Browser / App)                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FastAPI Application                                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────────────┐  │
│  │  /signup    │    │  /login     │    │  /contents (CRUD)               │  │
│  │  /login     │    │  JWT Token  │    │  - POST: Save + AI background   │  │
│  └─────────────┘    └─────────────┘    │  - GET: Cache check → DB        │  │
│                                         │  - DELETE: Invalidate cache     │  │
│                                         └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
         │                    │                         │
         ▼                    ▼                         ▼
┌─────────────┐      ┌─────────────┐           ┌─────────────────┐
│  PostgreSQL │      │    Redis    │           │  Hugging Face   │
│  (Users +   │      │   (Cache)   │           │  LLM API        │
│   Contents) │      │             │           │  (Async call)   │
└─────────────┘      └─────────────┘           └─────────────────┘
```

### Request Flow for `POST /contents`
```
1. Client ──────► FastAPI (JWT validated)
2. FastAPI ─────► PostgreSQL (save raw content)
3. FastAPI ─────► Background Task started
4. Background ──► Hugging Face API (summarize + sentiment)
5. Background ──► PostgreSQL (update with AI results)
6. Background ──► Redis (invalidate user cache)
7. Client ◄───── 201 Created (immediate response)
```

### Request Flow for `GET /contents`
```
1. Client ──────► FastAPI (JWT validated)
2. FastAPI ─────► Redis (cache lookup)
   ├─ HIT ──────► Return cached response
   └─ MISS ─────► PostgreSQL (query contents)
                  └──► Redis (store in cache, TTL 5 min)
3. Client ◄───── JSON response
```

---

## 5. GCP Architecture (Theoretical)

### Services Used
| Service | Purpose |
|---------|---------|
| **Cloud Run** | Hosts containerized FastAPI app, auto-scales 0→N |
| **Cloud SQL** | Managed PostgreSQL with automated backups |
| **Memorystore** | Managed Redis for caching layer |
| **Secret Manager** | Securely stores API keys and credentials |
| **Artifact Registry** | Stores Docker images built by CI |
| **API Gateway** | Rate limiting, custom domain, JWT validation |
| **Cloud Logging** | Centralized logs and monitoring |

### GCP Deployment Diagram

```
                                    ┌──────────────────┐
                                    │   GitHub Repo    │
                                    │   (Source Code)  │
                                    └────────┬─────────┘
                                             │ push
                                             ▼
                                    ┌──────────────────┐
                                    │  GitHub Actions  │
                                    │  (CI Pipeline)   │
                                    └────────┬─────────┘
                                             │ build & push
                                             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                              Google Cloud Platform                          │
│                                                                              │
│  ┌──────────────────┐                                                       │
│  │ Artifact Registry│◄─── Docker Image                                      │
│  └────────┬─────────┘                                                       │
│           │                                                                  │
│           ▼                                                                  │
│  ┌──────────────────┐         ┌──────────────────┐                          │
│  │   API Gateway    │────────►│    Cloud Run     │                          │
│  │ (Rate Limiting,  │         │  (FastAPI App)   │                          │
│  │  Custom Domain)  │         └────────┬─────────┘                          │
│  └──────────────────┘                  │                                    │
│           ▲                            │ VPC Connector                      │
│           │                            ▼                                    │
│      HTTPS Request         ┌─────────────────────────────────┐              │
│                            │         Private VPC             │              │
│                            │  ┌─────────────┐ ┌───────────┐  │              │
│                            │  │  Cloud SQL  │ │Memorystore│  │              │
│                            │  │ (Postgres)  │ │  (Redis)  │  │              │
│                            │  └─────────────┘ └───────────┘  │              │
│                            └─────────────────────────────────┘              │
│                                                                              │
│  ┌──────────────────┐      ┌──────────────────┐                             │
│  │  Secret Manager  │      │  Cloud Logging   │                             │
│  │ (API Keys, Creds)│      │  & Monitoring    │                             │
│  └──────────────────┘      └──────────────────┘                             │
│                                                                              │
└────────────────────────────────────────────────────────────────────────────┘
                                             │
                                             ▼
                                    ┌──────────────────┐
                                    │  Hugging Face    │
                                    │  API (External)  │
                                    └──────────────────┘
```

### Deployment Steps (Theory)
1. **CI/CD:** GitHub Actions builds Docker image on push → pushes to Artifact Registry
2. **Infrastructure:** Cloud SQL and Memorystore pre-provisioned in a private VPC
3. **Runtime:** Cloud Run pulls latest image, connects via Serverless VPC Connector
4. **Secrets:** Secret Manager injects `SECRET_KEY`, `HUGGINGFACE_API_KEY`, DB credentials
5. **Edge:** API Gateway provides custom domain, rate limiting, and request validation
6. **Observability:** Cloud Trace captures latency; alerts on error spikes or AI timeouts

This architecture is cost-effective (Cloud Run scales to zero), secure (private VPC, managed secrets), and production-ready with minimal operational overhead.
