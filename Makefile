.PHONY: help install dev run docker-up docker-down db-init db-migrate seed test lint clean fernet-key worker beat celery flower

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- Desarrollo local ---

install: ## Instala dependencias
	pip install -r requirements.txt

dev: ## Inicia servidor de desarrollo
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

run: ## Inicia servidor de producción
	uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4

# --- Docker ---

docker-up: ## Levanta todos los servicios con Docker
	docker compose up -d

docker-down: ## Detiene todos los servicios
	docker compose down

docker-logs: ## Ve los logs de todos los servicios
	docker compose logs -f

docker-build: ## Reconstruye las imágenes
	docker compose build

# --- Base de datos ---

db-init: ## Inicializa la base de datos (crea tablas)
	python -c "import asyncio; from models.base import init_db; asyncio.run(init_db())"

seed: ## Carga datos de prueba (cliente Raiz Rentable + money pages)
	python -m scripts.seed_test_data

db-migrate: ## Crea una nueva migración con Alembic
	alembic revision --autogenerate -m "$(msg)"

db-upgrade: ## Aplica migraciones pendientes
	alembic upgrade head

# --- Utilidades ---

fernet-key: ## Genera una nueva FERNET_KEY
	python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

setup-env: ## Copia .env.example a .env
	cp .env.example .env
	@echo "✅ Archivo .env creado. Edita las variables antes de iniciar."

# --- Testing ---

test: ## Ejecuta tests
	pytest tests/ -v

lint: ## Verifica estilo de código
	ruff check .

# --- Worker ---

worker: ## Inicia worker de Celery
	celery -A core.celery_app worker --loglevel=info --concurrency=2

beat: ## Inicia Celery Beat (tareas programadas)
	celery -A core.celery_app beat --loglevel=info

celery: ## Inicia worker y beat juntos (desarrollo)
	celery -A core.celery_app worker --loglevel=info --concurrency=2 & celery -A core.celery_app beat --loglevel=info

flower: ## Monitoreo de tareas Celery (puerto 5555)
	celery -A core.celery_app flower --port=5555

# --- Limpieza ---

clean: ## Limpia archivos temporales
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .ruff_cache
