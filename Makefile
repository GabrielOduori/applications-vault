.PHONY: dev dev-backend dev-frontend test install install-frontend build build-extension

install:
	cd backend && pip install -e ".[dev]"

install-frontend:
	cd frontend && npm install

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

dev-frontend:
	cd frontend && npm run dev

dev:
	@echo "Run in two terminals:"
	@echo "  make dev-backend"
	@echo "  make dev-frontend"

test:
	cd backend && python -m pytest tests/ -v

test-quick:
	cd backend && python -m pytest tests/ -x -q

build:
	cd frontend && npm run build

build-extension:
	cd extension && ./build.sh
