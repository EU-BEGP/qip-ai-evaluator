# RAG API

This is a Django project that provides the RAG (Retrieval-Augmented Generation) API service.
The project is containerized using Docker and is designed to run in both development and production environments. It utilizes Celery with a Redis broker for asynchronous task processing and features dynamic worker scaling based on available API keys.

## Environment Setup

All environment variables are defined in a single `.env` file located in the root directory.

### `.env` File Template

```env
# --- GENERAL ---
ENVIRONMENT={development_or_production}

# --- DOCKER ---
RESTART_POLICY={no_or_always}

# --- DJANGO CORE ---
SECRET_KEY={django_secret_key}
ALLOWED_HOSTS={*}

# --- CALLBACK / SERVICE AUTH ---
QIP_CALLBACK_SECRET={shared_secret_key}
RAG_INBOUND_SECRET={shared_secret_key}
ALLOWED_CALLBACK_HOSTS={localhost,127.0.0.1,host.docker.internal}

# --- API KEYS ---
HF_TOKEN={huggingface_token}
# LLM provider key — must match `wrapper:` in config/config.yaml.
# OpenAI (default):
OPENAI_API_KEY={openai_key}
# Groq alternative (single key, or GROQ_API_KEYS):
# GROQ_API_KEY={groq_key}

# --- CORS ---
CORS_ALLOW_ALL_ORIGINS={True_or_False}
CORS_ALLOWED_ORIGINS={comma_separated_origins}
```

## Environment Variables Reference

| Variable | Description | Example Values |
|----------|-------------|----------------|
| `ENVIRONMENT` | Defines the execution mode. **Development**: Runs `runserver`. **Production**: Runs `gunicorn` and enables auto-static collection. | `development` or `production` |
| `RESTART_POLICY` | Docker container restart behavior. **Local**: `no`. **Server**: `always` (to ensure uptime). | `no` (dev), `always` (prod) |
| `SECRET_KEY` | Django security key. Use a strong, unique key for production servers. | `django-insecure...` (dev), `k^7&...` (prod) |
| `ALLOWED_HOSTS` | Domains/IPs this API serves. **Local**: `*`. **Server**: The real domain/IP. | `*` |
| `QIP_CALLBACK_SECRET` | Shared secret this service attaches to callbacks it sends **to** evaluator_api. Must match `RAG_CALLBACK_SECRET` in the evaluator_api `.env`. | `JQvR4Txh...` |
| `RAG_INBOUND_SECRET` | Shared secret required on every **inbound** request to this service (`X-Internal-Secret` header); unauthenticated requests are rejected. Must match `RAG_INBOUND_SECRET` in the evaluator_api `.env`. | `change-me` |
| `ALLOWED_CALLBACK_HOSTS` | Comma-separated allowlist of hosts the worker may POST callbacks to. Each entry may be a bare host or a full URL (only the host is matched). | `localhost,127.0.0.1,host.docker.internal` |
| `HF_TOKEN` | Hugging Face Token used to download the embedding model. | `hf_...` |
| `OPENAI_API_KEY` | OpenAI API key (default provider). Use `OPENAI_API_KEYS` (comma-separated) to rotate multiple keys. | `sk-...` |
| `GROQ_API_KEY` | Groq API key (used when `wrapper: "groq"`). Use `GROQ_API_KEYS` (comma-separated) for multi-key rotation / worker scaling. | `gsk_...` |
| `CORS_ALLOW_ALL_ORIGINS`| CORS Policy toggle. | `True` or `False` |
| `CORS_ALLOWED_ORIGINS` | Specific allowed origins for browser requests. | `https://eu-begp.upb.edu` |


## Running the Project
The project uses a `start.sh` script to automate the entire deployment process.

```bash
  ./start.sh
```

This script automatically performs the following:
1.  Builds the Docker images.
2.  Pre-builds the vector store (knowledge base) once — skipped if already up to date.
3.  Starts the services (recreates only the containers that changed — no full teardown): the Redis broker, the Django app, and the Celery worker.

> This service has no relational database — it stores no models and runs no migrations.

>**Note:** Ensure the script is executable:
>```bash
>sudo chmod +x start.sh
>```

### Service Authentication
Every inbound request must carry the `X-Internal-Secret` header (`RAG_INBOUND_SECRET`); requests without it are rejected. Outbound callbacks carry `QIP_CALLBACK_SECRET` and may only target hosts listed in `ALLOWED_CALLBACK_HOSTS`. In production, terminate TLS in front of this service (e.g. nginx) so these secrets never travel in plaintext.

### Performance Scaling
To increase the processing speed of the RAG service, add more keys to the provider's rotation variable (`OPENAI_API_KEYS` or `GROQ_API_KEYS`) in your `.env` file. The system will automatically scale the workers.