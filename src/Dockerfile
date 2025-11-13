# 1. Use a stable, slim Python base image
FROM python:3.11-slim

# 2. Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Install system dependencies
RUN apt-get update \
  && apt-get -y install libpq-dev gcc \
  && rm -rf /var/lib/apt/lists/*

# 4. Set the working directory
WORKDIR /app

# 5. Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy ALL project code (src/ -> /app/)
COPY . /app/

# 7. Create group and user
RUN addgroup --system django_user
RUN adduser --system --ingroup django_user --no-create-home django_user

# 8. Set permissions for persistent volumes and code
# Create directories for volumes first
RUN mkdir -p /app/app/db
RUN mkdir -p /app/static
# Set ownership
RUN chown -R django_user:django_user /app

# 9. Switch to the non-root user
USER django_user

# 10. Expose the port
EXPOSE 8000

# 11. Start Gunicorn (pointing to the 'app' project's wsgi file)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app.wsgi:application"]