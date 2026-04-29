# 1. Use a stable, slim Python base image
FROM python:3.11-slim

# 2. Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Install system dependencies for PostgreSQL
RUN apt-get update \
  && apt-get -y install libpq-dev gcc postgresql-client \
  && rm -rf /var/lib/apt/lists/*

# 4. Set the working directory
WORKDIR /app

# 5. Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip \
  && pip install --no-cache-dir -r requirements.txt

# 6. Copy your project code into the container
COPY . /app/

# Setup Entrypoint script
COPY ./scripts /scripts
RUN sed -i 's/\r$//' /scripts/entrypoint.sh && \
    chmod +x /scripts/entrypoint.sh

# 7. Create runtime directories
RUN mkdir -p /app/logs

# 8. Expose the port
EXPOSE 8000

# 8. Start using the entrypoint script
CMD ["/scripts/entrypoint.sh"]