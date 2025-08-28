.PHONY: help up down restart logs clean db-shell redis-shell nats-shell minio-shell install-deps dev build test lint format

# Default target
help: ## Show this help message
	@echo "AI Documentation Gap Finder - Development Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Infrastructure commands
up: ## Start all services (Docker Compose)
	@echo "Starting AI Documentation Gap Finder services..."
	docker-compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 10
	@docker-compose ps

down: ## Stop all services
	@echo "Stopping AI Documentation Gap Finder services..."
	docker-compose down

restart: ## Restart all services
	@echo "Restarting AI Documentation Gap Finder services..."
	docker-compose restart

logs: ## Show logs from all services
	docker-compose logs -f

clean: ## Stop services and remove volumes (WARNING: destroys data)
	@echo "Cleaning up AI Documentation Gap Finder services and data..."
	docker-compose down -v --remove-orphans

# Database access
db-shell: ## Connect to PostgreSQL shell
	docker-compose exec postgres psql -U postgres -d ai_docgap

redis-shell: ## Connect to Redis CLI
	docker-compose exec redis redis-cli

nats-shell: ## Connect to NATS CLI
	docker-compose exec nats nats --server=nats:4222

minio-shell: ## Access MinIO console (opens browser)
	@echo "MinIO Console: http://localhost:9001"
	@echo "Access Key: ai-docgap"
	@echo "Secret Key: ai-docgap-secret"

# Development setup
install-deps: ## Install development dependencies
	@echo "Installing dependencies..."
	# Frontend dependencies (Next.js)
	@if [ -f "package.json" ]; then \
		echo "Installing frontend dependencies..."; \
		npm install; \
	fi
	# Backend dependencies (Python workers)
	@if [ -f "requirements.txt" ]; then \
		echo "Installing Python dependencies..."; \
		pip install -r requirements.txt; \
	fi
	# API dependencies (NestJS)
	@if [ -f "api/package.json" ]; then \
		echo "Installing API dependencies..."; \
		cd api && npm install && cd ..; \
	fi

dev: ## Start development servers (requires services to be running)
	@echo "Starting development servers..."
	@echo "Make sure to run 'make up' first to start the infrastructure"
	# Start Next.js frontend
	@if [ -f "package.json" ]; then \
		echo "Starting Next.js frontend on http://localhost:3000"; \
		npm run dev & \
	fi
	# Start API server
	@if [ -f "api/package.json" ]; then \
		echo "Starting NestJS API on http://localhost:4000"; \
		cd api && npm run start:dev && cd ..; \
	fi

# Build commands
build: ## Build all services
	@echo "Building services..."
	# Build frontend
	@if [ -f "package.json" ]; then \
		echo "Building Next.js frontend..."; \
		npm run build; \
	fi
	# Build API
	@if [ -f "api/package.json" ]; then \
		echo "Building NestJS API..."; \
		cd api && npm run build && cd ..; \
	fi

# Testing and quality
test: ## Run all tests
	@echo "Running tests..."
	# Frontend tests
	@if [ -f "package.json" ]; then \
		npm test; \
	fi
	# API tests
	@if [ -f "api/package.json" ]; then \
		cd api && npm test && cd ..; \
	fi
	# Python tests
	@if [ -f "requirements.txt" ]; then \
		python -m pytest; \
	fi

lint: ## Run linters
	@echo "Running linters..."
	# Frontend linting
	@if [ -f "package.json" ]; then \
		npm run lint; \
	fi
	# API linting
	@if [ -f "api/package.json" ]; then \
		cd api && npm run lint && cd ..; \
	fi
	# Python linting
	@if [ -f "requirements.txt" ]; then \
		python -m flake8 || echo "flake8 not installed"; \
	fi

format: ## Format code
	@echo "Formatting code..."
	# Frontend formatting
	@if [ -f "package.json" ]; then \
		npm run format; \
	fi
	# Python formatting
	@if [ -f "requirements.txt" ]; then \
		python -m black . || echo "black not installed"; \
	fi

# Health checks
health: ## Check health of all services
	@echo "Checking service health..."
	@docker-compose ps
	@echo ""
	@echo "PostgreSQL health:"
	@docker-compose exec -T postgres pg_isready -U postgres || echo "PostgreSQL not ready"
	@echo "Redis health:"
	@docker-compose exec -T redis redis-cli ping || echo "Redis not ready"
	@echo "NATS health:"
	@curl -s http://localhost:8222/ > /dev/null && echo "NATS ready" || echo "NATS not ready"
	@echo "MinIO health:"
	@curl -s http://localhost:9000/minio/health/live > /dev/null && echo "MinIO ready" || echo "MinIO not ready"

# Utility commands
seed: ## Seed database with demo data
	@echo "Seeding database with demo data..."
	@docker-compose exec -T postgres psql -U postgres -d ai_docgap -f /docker-entrypoint-initdb.d/01-init.sql

backup: ## Backup database
	@echo "Backing up database..."
	@docker-compose exec postgres pg_dump -U postgres ai_docgap > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore: ## Restore database from backup (usage: make restore FILE=backup.sql)
	@echo "Restoring database from $(FILE)..."
	@docker-compose exec -T postgres psql -U postgres -d ai_docgap < $(FILE)

# Environment setup
setup: ## Initial project setup
	@echo "Setting up AI Documentation Gap Finder project..."
	@echo "1. Starting infrastructure..."
	make up
	@echo "2. Installing dependencies..."
	make install-deps
	@echo "3. Seeding database..."
	make seed
	@echo ""
	@echo "Setup complete! 🎉"
	@echo "Next steps:"
	@echo "- Run 'make dev' to start development servers"
	@echo "- Visit http://localhost:3000 for the frontend"
	@echo "- Visit http://localhost:4000 for the API"
	@echo "- Visit http://localhost:9001 for MinIO console"
