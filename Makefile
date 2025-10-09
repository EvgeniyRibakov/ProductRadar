.PHONY: install test lint format clean run help

help:
	@echo "Доступные команды:"
	@echo "  make install    - Установить зависимости"
	@echo "  make test       - Запустить тесты"
	@echo "  make lint       - Проверить код линтерами"
	@echo "  make format     - Отформатировать код"
	@echo "  make clean      - Очистить временные файлы"
	@echo "  make run        - Запустить агента"

install:
	poetry install --with dev

test:
	poetry run pytest tests/ -v --cov=src --cov-report=html --cov-report=term

lint:
	poetry run flake8 src/ tests/
	poetry run mypy src/

format:
	poetry run black src/ tests/
	poetry run isort src/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov
	rm -rf dist
	rm -rf build

run:
	poetry run python scripts/run_agent.py

