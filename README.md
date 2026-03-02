# NexusAPI - Kasparro AI Backend

A robust, multi-tenant API built for the Kasparro backend engineering assignment. This service handles secure organization-based authentication, an append-only credit ledger system, synchronous/asynchronous product endpoints, and strict API rate limiting.

## Tech Stack
* **Framework:** FastAPI (Python 3.12)
* **Database:** PostgreSQL (asyncpg)
* **ORM & Migrations:** SQLAlchemy 2.0 & Alembic
* **Background Jobs:** ARQ & Redis (Upstash)
* **Authentication:** Google OAuth2 & JWT
* **Logging:** Structlog (JSON structured logging)

---

## ⚙️ Environment Variables

Create a `.env` file in the root directory. You must configure the following variables for the application to run:

```env
# Project Settings
PROJECT_NAME="NexusAPI"

# Database Connections
DATABASE_URL="postgresql+asyncpg://<user>:<password>@<host>:<port>/<dbname>"
REDIS_URL="rediss://default:<password>@<upstash-host>:<port>"

# Security & Authentication
ALGORITHM="HS256"
JWT_SECRET_KEY="<your-secure-random-string>"
ACCESS_TOKEN_EXPIRES_MINUTES=1440

# Google OAuth
GOOGLE_CLIENT_ID="<your-google-oauth-client-id>"
GOOGLE_CLIENT_SECRET="<your-google-oauth-client-secret>"
```

## 🚀 Local Setup & Execution

**1. Clone the repository and navigate to the directory:**
```bash
git clone <your-repo-url>
cd nexusapi
```

**2. Create a virtual environment and install dependencies:**
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

**3. Run Database Migrations:**
Ensure your PostgreSQL database is running and your DATABASE_URL is set in .env. Then, apply the schema migrations:
```bash
alembic upgrade head
```

**4. Start the Application (Requires Two Terminals):** \

**Terminal 1 (The API Server):**
```bash
uvicorn app.main:app --reload
```
The API will be available at: http://127.0.0.1:8000 \
Interactive Swagger Docs: http://127.0.0.1:8000/docs

**Terminal 2 (The Async Worker):** \
Ensure your virtual environment is activated and start the ARQ background worker:
```bash
arq app.worker.WorkerSettings
```


## 📡 Example API Requests

Here are three core interactions using curl. (Note: Replace <YOUR_JWT_TOKEN> with a valid token obtained via the /api/v1/auth/google endpoint).

**1. Check Credit Balance** \
Retrieves the total balance calculated from the append-only transaction ledger.
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/api/v1/credits/balance' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

**2. Grant Credits (Admin Only, Idempotent)** \
Grants 100 credits to the organization. This endpoint requires the admin role and utilizes an idempotency key to prevent double-funding.
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/v1/credits/grant' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{
  "amount": 100,
  "reason": "Monthly allowance",
  "idempotency_key": "grant-march-001"
}'
```


**3. Queue an Async Summarisation Job** \
Deducts 10 credits and instantly returns a job_id while processing the text in the Redis-backed background worker.
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/summarise' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>' \
  -H 'Idempotency-Key: sum-req-001' \
  -H 'Content-Type: application/json' \
  -d '{
  "text": "Kasparro AI is evaluating this highly robust, async-capable API."
}'
```
