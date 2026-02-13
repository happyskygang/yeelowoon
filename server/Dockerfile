FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY server/requirements.txt /app/server/
COPY pyproject.toml /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/server/requirements.txt

# Copy application code
COPY engine/ /app/engine/
COPY cli/ /app/cli/
COPY server/ /app/server/

# Install package with fallback version (no .git in Docker)
ENV SETUPTOOLS_SCM_PRETEND_VERSION=0.2.0
RUN pip install --no-cache-dir /app

# Set environment variables
ENV PYTHONPATH=/app
ENV HOST=0.0.0.0
ENV PORT=8001
ENV WORK_DIR=/tmp/drum2midi-jobs

# Expose port
EXPOSE 8001

# Run server
CMD ["python", "-m", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8001"]
