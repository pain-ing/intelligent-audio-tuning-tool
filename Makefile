.PHONY: help build up down logs shell-api shell-worker migrate test

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build all Docker images
	cd deploy && docker-compose build

up: ## Start all services
	cd deploy && docker-compose up -d

down: ## Stop all services
	cd deploy && docker-compose down

logs: ## Show logs for all services
	cd deploy && docker-compose logs -f

logs-api: ## Show API logs
	cd deploy && docker-compose logs -f api

logs-worker: ## Show worker logs
	cd deploy && docker-compose logs -f worker

shell-api: ## Open shell in API container
	cd deploy && docker-compose exec api bash

shell-worker: ## Open shell in worker container
	cd deploy && docker-compose exec worker bash

migrate: ## Run database migrations
	cd deploy && docker-compose exec api alembic upgrade head

migrate-create: ## Create new migration
	cd deploy && docker-compose exec api alembic revision --autogenerate -m "$(MSG)"

test-api: ## Test API endpoints
	curl -f http://localhost:8080/health
	@echo "\nAPI health check passed!"

setup: ## Initial setup - copy env file and start services
	cp .env.example .env
	make build
	make up
	sleep 10
	make migrate
	make test-api

clean: ## Clean up containers and volumes
	cd deploy && docker-compose down -v
	docker system prune -f
