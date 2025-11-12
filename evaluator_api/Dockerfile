# 1. Use a stable, slim Python base image
FROM python:3.11-slim

# 2. Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Install system dependencies for PostgreSQL
RUN apt-get update \
  && apt-get -y install libpq-dev gcc \
  && rm -rf /var/lib/apt/lists/*

# 4. Set the working directory
WORKDIR /app

# 5. Install Python dependencies from your locked file
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy your project code into the container
COPY . /app/

# 7. Create a non-root user for security
RUN adduser --system --no-create-home django_user
USER django_user

# 8. Expose the port Gunicorn will run on
EXPOSE 8000

# 9. Start Gunicorn (project name from manage.py)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "evaluator_api.wsgi:application"]