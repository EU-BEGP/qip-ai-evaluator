# 1. Use slim base image (saves ~850 MB vs python:3.11 full)
FROM python:3.11-slim

# 2. Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/cache/huggingface

# 3. System dependencies (OpenCV requires libgl1 + libglib2.0-0)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

# 4. Working directory
WORKDIR /app

# 5. Install CPU-only PyTorch, then remaining dependencies
COPY requirements.txt /app/
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        pip install --no-cache-dir "torch==2.9.0" \
            --index-url https://download.pytorch.org/whl/cpu; \
    else \
        pip install --no-cache-dir "torch==2.9.0"; \
    fi \
 && pip install --no-cache-dir -r requirements.txt

# 6. Copy application code
COPY ./app /app/
COPY ./scripts /scripts
RUN sed -i 's/\r$//' /scripts/entrypoint.sh \
 && chmod +x /scripts/entrypoint.sh

# 7. Create runtime directories
RUN mkdir -p /app/static \
             /app/data/vector_store \
             /app/cache/huggingface \
             /app/logs

# 8. Expose API port
EXPOSE 8000

# 9. Start via entrypoint
CMD ["/scripts/entrypoint.sh"]
