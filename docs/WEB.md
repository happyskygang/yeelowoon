# Web UI Deployment Guide

## Architecture

```
┌─────────────────┐     HTTPS      ┌─────────────────┐
│   GitHub Pages  │ ◄────────────► │   Your Browser  │
│   (Static UI)   │                │                 │
└─────────────────┘                └────────┬────────┘
                                            │
                                            │ HTTP/HTTPS
                                            ▼
                                   ┌─────────────────┐
                                   │   API Server    │
                                   │   (Docker/VM)   │
                                   └─────────────────┘
```

- **Web UI**: Static HTML/CSS/JS hosted on GitHub Pages
- **API Server**: FastAPI running in Docker on your server/NAS

## Local Development (code-server)

### 1. Start API Server

```bash
# Terminal 1: Run API server
make dev-server

# Or manually:
cd server && python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

The server runs on `http://0.0.0.0:8001`.

### 2. Start Web UI

```bash
# Terminal 2: Serve static files
make dev-web

# Or manually:
cd webui/public && python -m http.server 8080 --bind 0.0.0.0
```

The UI is available at `http://0.0.0.0:8080`.

### 3. Configure API URL

Edit `webui/public/config.json`:

```json
{
  "apiBaseUrl": "http://localhost:8001"
}
```

### 4. Port Forwarding

In code-server, forward ports 8001 and 8080 to access from your browser.

## Deploy API Server (Docker)

### Option 1: Docker Compose

```bash
docker-compose up -d
```

### Option 2: Docker Run

```bash
# Build
docker build -t drum2midi-server -f server/Dockerfile .

# Run
docker run -d \
  --name drum2midi-api \
  -p 8001:8001 \
  -e CORS_ORIGINS=https://happyskygang.github.io,http://localhost:8080 \
  -v $(pwd)/jobs:/tmp/drum2midi-jobs \
  drum2midi-server
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8001` | Server port |
| `WORK_DIR` | `/tmp/drum2midi-jobs` | Job storage directory |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Allowed CORS origins (comma-separated) |
| `MAX_FILE_SIZE` | `52428800` | Max upload size in bytes (50MB) |

### Reverse Proxy (HTTPS)

If your GitHub Pages uses HTTPS, the API must also use HTTPS (mixed content blocked).

**nginx example:**

```nginx
server {
    listen 443 ssl;
    server_name api.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # For file uploads
        client_max_body_size 50M;
    }
}
```

## Deploy Web UI (GitHub Pages)

### 1. Enable GitHub Pages

1. Go to repository Settings → Pages
2. Source: "GitHub Actions"
3. The workflow will auto-deploy on push to `main`

### 2. Configure API URL

Before deploying, edit `webui/public/config.json`:

```json
{
  "apiBaseUrl": "https://your-api-server.com"
}
```

Commit and push to trigger deployment.

### 3. Access

After deployment, the UI is available at:

```
https://happyskygang.github.io/yeelowoon/
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/healthz` | Health check |
| `POST` | `/api/jobs` | Create processing job |
| `GET` | `/api/jobs/{id}` | Get job status |
| `GET` | `/api/jobs/{id}/download` | Download result ZIP |

### Create Job

```bash
curl -X POST http://localhost:8001/api/jobs \
  -F "file=@drums.wav" \
  -F "stems=kick,snare,hihat" \
  -F "bpm=auto" \
  -F "sep_backend=bandpass" \
  -F "sep_quality=balanced"
```

### Check Status

```bash
curl http://localhost:8001/api/jobs/{job_id}
```

### Download Result

```bash
curl -O http://localhost:8001/api/jobs/{job_id}/download
```

## Troubleshooting

### CORS Errors

Ensure `CORS_ORIGINS` includes your frontend URL:

```bash
CORS_ORIGINS=http://localhost:8080,https://happyskygang.github.io
```

### Mixed Content Blocked

If using HTTPS for Pages, API must also be HTTPS. Use a reverse proxy with SSL.

### File Upload Fails

- Check file size limit (default 50MB)
- Ensure file is valid WAV format
- Check server logs for errors
