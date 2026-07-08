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

For cloud deployment, set the public frontend address in `deploy/.env` before starting:

```text
PETMALL_PUBLIC_H5_URL=http://your-server-ip:8080
PETMALL_CORS_ORIGINS=http://your-server-ip:8080
PETMALL_ALIPAY_NOTIFY_URL=http://your-server-ip:8000/payments/alipay/notify
PETMALL_ALIPAY_RETURN_URL=http://your-server-ip:8080/#/pages/payment/result
```

If you access the site through a custom hosts entry such as `http://ubuntu:8080`, include that origin too:

```text
PETMALL_CORS_ORIGINS=http://your-server-ip:8080,http://ubuntu:8080
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

## SMS

Real SMS sending requires a Spug Push SMS template id. In `deploy/.env`, set:

```text
PETMALL_SPUG_SMS_TEMPLATE_ID=A27L-your-template-id
PETMALL_SPUG_SMS_TEMPLATE_NAME=PetMall
PETMALL_SPUG_SMS_CODE_PARAM_NAME=code
```

After changing `deploy/.env`, recreate the backend containers:

```powershell
docker compose up -d --force-recreate api worker
```

Verify the value inside the running API container:

```powershell
docker compose exec api printenv PETMALL_SPUG_SMS_TEMPLATE_ID
```

For development/demo only, you can bypass real SMS by setting:

```text
PETMALL_SMS_DEBUG_CODE_ENABLED=true
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

## Optional AI Assistant LangGraph Memory

Start PostgreSQL for AI assistant LangGraph checkpoint memory:

```powershell
cd deploy
docker compose --profile memory up --build
```

Then set `PETMALL_AGENT_MEMORY_POSTGRES_DSN` in `deploy/.env`, for example:

```text
PETMALL_AGENT_MEMORY_POSTGRES_DSN=postgresql://petmall:change_me@postgres:5432/petmall_agent
PETMALL_AGENT_MEMORY_SETUP_ON_START=true
```

This checkpoint memory is currently used by the AI pet care QA assistant. MySQL still stores user-visible chat sessions and messages.

## Notes

- `deploy/.env` is local-only and must not contain committed production secrets.
- `PETMALL_PAYMENT_MODE=mock` is only for local development, demo, and automated tests.
- `frontend` and `api` are exposed publicly by default. MySQL, Redis, RabbitMQ, Ollama, and PostgreSQL bind to `127.0.0.1` by default; change the `*_BIND_HOST` variables only when you intentionally need remote access.
- `api` and `worker` intentionally share the same image so router, service, model, and migration code stay in sync.
- Compose creates a project bridge network by default. Services can reach each other by service name, for example frontend Nginx proxies to `http://api:8000/`.
