# PetMall Docker Deploy

This directory provides a development/test Docker template for the current backend services.

## Services

- `frontend`: uni-app H5 build served by Nginx, exposed on `PETMALL_FRONTEND_PUBLISHED_PORT`.
- `api`: FastAPI backend, exposed on `PETMALL_API_PUBLISHED_PORT` and proxied by frontend Nginx under `/api/`.
- `worker`: knowledge/RAG task worker, consuming RabbitMQ queue `petmall.knowledge`.
- `migrate`: one-shot Alembic migration job, required before `api` and `worker` start.
- `mysql`: MySQL 8.4 for application data.
- `redis`: Redis for cache, SMS code state, and lightweight runtime state.
- `rabbitmq`: RabbitMQ with management UI.
- `ollama`: optional RAG embedding runtime, enabled with profile `rag`.
- `postgres`: optional LangGraph memory database, enabled with profile `memory`.

## Start

```powershell
cd deploy
Copy-Item .env.example .env
docker compose up --build
```

API direct access:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/docs
```

Frontend access:

```text
http://127.0.0.1:8080/
http://127.0.0.1:8080/api/
http://127.0.0.1:8080/generated/
```

RabbitMQ management:

```text
http://127.0.0.1:15672/
```

Default RabbitMQ account is `guest` / `guest`.

## Optional RAG Runtime

The backend stores Chroma vector data under `backend/generated/private/vector_store`; no separate Chroma server is required.

Start Ollama together with the backend:

```powershell
cd deploy
docker compose --profile rag up --build
```

Pull the embedding model inside the Ollama container before processing knowledge tasks:

```powershell
docker compose exec ollama ollama pull nomic-embed-text
```

## Optional LangGraph Memory

Start PostgreSQL for LangGraph checkpoint memory:

```powershell
cd deploy
docker compose --profile memory up --build
```

Then set `PETMALL_AGENT_MEMORY_POSTGRES_DSN` in `deploy/.env`, for example:

```text
PETMALL_AGENT_MEMORY_POSTGRES_DSN=postgresql://petmall:change_me@postgres:5432/petmall_agent
PETMALL_AGENT_MEMORY_SETUP_ON_START=true
```

## Notes

- `deploy/.env` is local-only and must not contain committed production secrets.
- `PETMALL_PAYMENT_MODE=mock` is only for local development, demo, and automated tests.
- `api` and `worker` intentionally share the same image so router, service, model, and migration code stay in sync.
- Compose creates a project bridge network by default. Services can reach each other by service name, for example frontend Nginx proxies to `http://api:8000/`.
