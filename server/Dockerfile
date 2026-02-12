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
RUN pip install --no-cache-dir -e /app

# Copy application code
COPY engine/ /app/engine/
COPY cli/ /app/cli/
COPY server/ /app/server/

# Set environment variables
ENV PYTHONPATH=/app
ENV HOST=0.0.0.0
ENV PORT=8001
ENV WORK_DIR=/tmp/drum2midi-jobs

# Expose port
EXPOSE 8001

# Run server
CMD ["python", "-m", "server.main"]
