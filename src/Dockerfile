# 1. Use the official Python 3.11 base image
FROM python:3.11

# 2. Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV HF_HOME=/app/cache/huggingface

# 3. Install minimal system dependencies
RUN apt-get update \
 && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

# 4. Set the main working directory
WORKDIR /app

# 5. Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy local 'app' to container '/app'
COPY ./app /app/

COPY ./scripts /scripts
RUN sed -i 's/\r$//' /scripts/entrypoint.sh && \
    chmod +x /scripts/entrypoint.sh

# 7. Create directories
RUN mkdir -p /app/static
RUN mkdir -p /app/db 
RUN mkdir -p /app/cache/huggingface

# 8. Create non-root user
RUN addgroup --system django_user
RUN adduser --system --ingroup django_user --no-create-home django_user
RUN chown -R django_user:django_user /app

# 9. Switch user
USER django_user

# 10. Expose port
EXPOSE 8000

# 11. Start via Script
CMD ["/scripts/entrypoint.sh"]
