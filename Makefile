.PHONY: help build up down logs test clean sync-dicts

help:
	@echo "168-ФЗ Text Checker - Docker Микросервис"
	@echo ""
	@echo "Доступные команды:"
	@echo "  make build          - Сборка Docker образа"
	@echo "  make up             - Запуск контейнера"
	@echo "  make down           - Остановка контейнера"
	@echo "  make logs           - Просмотр логов"
	@echo "  make test           - Тест API"
	@echo "  make sync           - Синхронизация словарей"
	@echo "  make clean          - Очистка (остановка + удаление образа)"
	@echo "  make shell          - Открыть shell в контейнере"
	@echo ""
	@echo "После запуска: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Сервис запущен: http://localhost:8000"
	@echo "API документация: http://localhost:8000/docs"

down:
	docker-compose down

logs:
	docker-compose logs -f checker

test:
	@echo "Проверка здоровья сервиса..."
	@curl -s http://localhost:8000/api/v1/health | jq . 2>/dev/null || curl -s http://localhost:8000/api/v1/health
	@echo ""
	@echo "Тестовая проверка текста..."
	@curl -s -X POST "http://localhost:8000/api/v1/check" \
		-H "Content-Type: application/json" \
		-d '{"text": "Наш developer провел meeting"}' | jq . 2>/dev/null || echo "Установите jq для красивого вывода"

sync:
	docker-compose exec checker python sync_cli.py --sync all

shell:
	docker-compose exec checker bash

clean: down
	docker-compose rm -f
	docker rmi fz168-checker 2>/dev/null || true
	@echo "Очистка завершена"
