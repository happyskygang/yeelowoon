.PHONY: dev-server dev-web install test build docker-build docker-run clean

# Development
dev-server:
	cd server && python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload

dev-web:
	cd webui/public && python -m http.server 8080 --bind 0.0.0.0

# Installation
install:
	pip install -e ".[dev]"
	pip install -r server/requirements.txt

# Testing
test:
	pytest tests/ -v

# Docker
docker-build:
	docker build -t drum2midi-server -f server/Dockerfile .

docker-run:
	docker run -p 8001:8001 \
		-e CORS_ORIGINS=http://localhost:8080,https://happyskygang.github.io \
		drum2midi-server

# Clean
clean:
	rm -rf dist/ build/ *.egg-info/
	rm -rf jobs/ out/
	find . -type d -name __pycache__ -exec rm -rf {} +
