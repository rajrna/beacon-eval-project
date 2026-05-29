# Beacon

**Student Agent Evaluation & Observability Platform**

Beacon is purpose-built for evaluating student-facing AI agents in higher education. It adds a university-domain layer on top of Langfuse: institution and program hierarchy, FERPA-aware trace handling, mental-health safety routing, SME annotation workflows, and judge rubrics tuned for student conversations.

---

## Quick start (local)

**Prerequisites:** Docker, Docker Compose, Python 3.12, Node 20

```bash
# 1. Clone and enter the repo
git clone https://github.com/your-org/beacon.git && cd beacon

# 2. Set up local environment
cp infra/env.example infra/env.local
# Edit infra/env.local — add your ANTHROPIC_API_KEY and LANGFUSE keys

# 3. Start the full stack
make dev

# 4. Run migrations (first time only)
make migrate

# 5. Seed dev data (optional)
make seed
```

API: http://localhost:8000/docs  
Dashboard: http://localhost:5173

---

## Structure

```
beacon/
├── backend/          # Python FastAPI + SQLAlchemy + RQ workers
├── frontend/         # React 19 + Vite + TypeScript + Tailwind
├── datasets/         # Golden JSONL datasets (versioned in git)
├── infra/            # Azure Bicep + env templates
├── docs/             # Internal MkDocs site
└── .github/          # CI/CD workflows
```

## Commands

| Command | What it does |
|---|---|
| `make dev` | Full local stack |
| `make migrate` | Run Alembic migrations |
| `make test` | Backend tests + coverage |
| `make test-safety` | Safety-critical tests |
| `make lint` / `make fmt` | Ruff lint / format |
| `make typecheck` | mypy |
