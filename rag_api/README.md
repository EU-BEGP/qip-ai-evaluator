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

# --- CALLBACK ---
QIP_CALLBACK_SECRET={shared_secret_key}

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
| `QIP_CALLBACK_SECRET` | Shared secret key for authenticating requests between APIs, must be the same configured in evaluator api. | `JQvR4Txh...` |
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
1.  Stops and cleans old containers.
2.  Builds the Docker images.
3.  Runs database migrations.
4.  Starts the Database, Redis, Celery Workers, and the Django App.

>**Note:** Ensure the script is executable:
>```bash
>sudo chmod +x start.sh
>```

### Performance Scaling
To increase the processing speed of the RAG service, add more keys to the provider's rotation variable (`OPENAI_API_KEYS` or `GROQ_API_KEYS`) in your `.env` file. The system will automatically scale the workers.