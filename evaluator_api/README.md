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
PUBLIC_BASE_URL={http://host.docker.internal:8004/}
EXTERNAL_LOGIN_API_URL={https://eubbc-digital.upb.edu/booking/api/users/token/}
EXTERNAL_AUTH_ME_URL={https://eubbc-digital.upb.edu/booking/api/users/me/}

# RAG BASE URL
RAG_BASE_URL={http://host.docker.internal:8005/api}
RAG_CALLBACK_SECRET={shared_secret_key}

# --- CORS ---
CORS_ALLOW_ALL_ORIGINS={True_or_False}
CORS_ALLOWED_ORIGINS={comma_separated_origins}

# --- EMAIL (production only) ---
EMAIL_HOST_USER={gmail_address}
EMAIL_HOST_PASSWORD={gmail_app_password}
ADMIN_EMAIL={admin_address}
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
| `PUBLIC_BASE_URL` | Public URL of this API (used to build the callback URLs the RAG service calls back to). **Local**: `http://host.docker.internal:8004/`. **Server**: Real domain `https://api.yourdomain.com/`. | `http://host.docker.internal:8004/` |
| `EXTERNAL_LOGIN_API_URL` | **Fixed URL.** Points to the Book4RLab authentication (token) service. | `https://eubbc-digital.upb.edu/booking/api/users/token/` |
| `EXTERNAL_AUTH_ME_URL` | **Fixed URL.** Book4RLab current-user endpoint used to resolve the authenticated user. | `https://eubbc-digital.upb.edu/booking/api/users/me/` |
| `RAG_BASE_URL` | RAG Service URL. **Local**: `http://host.docker.internal:8005/api`. **Server**: `https://eu-begp.upb.edu/qip-rag-api`. | `http://host.docker.internal:8005/api` |
| `RAG_CALLBACK_SECRET` | Shared secret key for RAG, must be the same configured in RAG api. | `shared key...` |
| `CORS_ALLOW_ALL_ORIGINS`| CORS Policy. | `True` or `False` |
| `CORS_ALLOWED_ORIGINS` | Specific allowed origins (used only when `CORS_ALLOW_ALL_ORIGINS` is `False`). | `http://localhost:3000` |
| `EMAIL_HOST_USER` | Gmail SMTP account. **Required in production only** (dev prints email to the console). | `you@gmail.com` |
| `EMAIL_HOST_PASSWORD` | Gmail SMTP app password. **Required in production only**. | `app password` |
| `ADMIN_EMAIL` | Address that receives Django admin error reports. | `admin@yourdomain.com` |


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

The Evaluator API is accessible at your configured `PUBLIC_BASE_URL`.