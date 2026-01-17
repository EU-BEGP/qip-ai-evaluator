# Evaluator API

This is a Django project that provides the Evaluator API.
The project is containerized using Docker and is designed to run in both development and production environments.

## Environment Setup

All environment variables are defined in a single `.env` file located in the root directory.

### `.env` File Template

```env
# --- GENERAL ---
ENVIRONMENT={development_or_production}
STATIC_VOLUME_PATH={./local_static_files}

# --- DOCKER ---
RESTART_POLICY={no_or_always}

# --- DJANGO CORE ---
SECRET_KEY={django_secret_key}
ALLOWED_HOSTS={*}
STATIC_URL={/evaluator/api/static/}

# --- DATABASE ---
POSTGRES_DB={db_name}
POSTGRES_USER={db_user}
POSTGRES_PASSWORD={db_password}
DB_HOST={db_host}
DB_PORT={db_port}

# --- URLs ---
SERVER_PUBLIC_URL={http://host.docker.internal:8004/}
EXTERNAL_LOGIN_API_URL={https://eubbc-digital.upb.edu/booking/api/users/token}

# RAG BASE URL
RAG_BASE_URL={http://host.docker.internal:8005/api}
RAG_CALLBACK_SECRET={shared_secret_key}

# --- CORS ---
CORS_ALLOW_ALL_ORIGINS={True_or_False}
CORS_ALLOWED_ORIGINS={comma_separated_origins}
```

## Environment Variables Reference

| Variable | Description | Example Values |
|----------|-------------|----------------|
| `ENVIRONMENT` | Defines the execution mode. **Development**: Runs `runserver`. **Production**: Runs `gunicorn` and enables auto-static collection in `start.sh`. | `development` or `production` |
| `STATIC_VOLUME_PATH` | Host path for static files. **Local**: Use relative path (`./local...`). **Server**: Use absolute path (`/var/www...`). | `./local_static_files` |
| `RESTART_POLICY` | Docker container restart behavior. **Local**: `no`. **Server**: `always` (to ensure uptime). | `no` (dev), `always` (prod) |
| `SECRET_KEY` | Django security key. Use a strong, unique key for production servers. | `insecure...` (dev), `x%2...` (prod) |
| `ALLOWED_HOSTS` | Domains/IPs this API serves. **Local**: `*`. **Server**: The real domain/IP. | `*` |
| `STATIC_URL` | URL prefix for static files. | `/evaluator/api/static/` |
| `POSTGRES_DB` | Database name. | `eval_api_db` |
| `POSTGRES_USER` | Database username. | `postgres` |
| `POSTGRES_PASSWORD` | Database password. | `password123` |
| `DB_HOST` | Database service hostname (internal Docker network). | `db` |
| `DB_PORT` | Database port. | `5432` |
| `SERVER_PUBLIC_URL` | Public URL of this API. **Local**: `http://host.docker.internal:8004/`. **Server**: Real domain `https://api.yourdomain.com/`. | `http://host.docker.internal:8004/` |
| `EXTERNAL_LOGIN_API_URL` | **Fixed URL.** Points to the Book4RLab authentication service. | `https://eubbc-digital.upb.edu/booking/api/users/token/` |
| `RAG_BASE_URL` | RAG Service URL. **Local**: `http://host.docker.internal:8005/api`. **Server**: `https://eu-begp.upb.edu/qip-rag-api`. | `http://host.docker.internal:8005/api` |
| `RAG_CALLBACK_SECRET` | Shared secret key for RAG, must be the same configured in RAG api. | `shared key...` |
| `CORS_ALLOW_ALL_ORIGINS`| CORS Policy. | `True` or `False` |
| `CORS_ALLOWED_ORIGINS` | Specific allowed origins. | `http://localhost:3000` |


## Running the Project
The project uses a `start.sh` script to automate the entire deployment process for both environments.

```bash
  ./start.sh
```

This script automatically performs the following:
1.  Stops and cleans old containers.
2.  Builds the Docker images.
3.  Starts the Database and runs migrations.
4.  **Static Files Handling**: The script detects the `ENVIRONMENT` variable. If set to `production`, it automatically runs `collectstatic`.
5.  Starts the application (`runserver` for Dev, `gunicorn` for Prod).

>**Note:** Ensure the script is executable:
>```bash
>sudo chmod +x start.sh
>```

## Recommendations

### Create Superuser
To access the Django Admin Panel, you must create a superuser inside the running container:

```bash
docker-compose run --rm app sh -c "python manage.py createsuperuser"
```

### Static Files
No manual action is required. The `start.sh` script automatically collects static files into the `STATIC_VOLUME_PATH` when deploying in production.

The Evaluator API is accessible at your configured `SERVER_PUBLIC_URL`.