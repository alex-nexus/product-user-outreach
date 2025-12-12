.PHONY: help install migrate dev runserver shell test clean

# Default Python interpreter
PYTHON := python3
PIP := pip3

# Django settings
DJANGO_SETTINGS_MODULE := outreach.settings

# Help target
help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make migrate    - Run database migrations"
	@echo "  make dev        - Run development server"
	@echo "  make shell      - Open Django shell"
	@echo "  make test       - Run tests"
	@echo "  make clean      - Clean Python cache files"

# Install dependencies
install:
	@echo "Installing dependencies..."
	$(PIP) install -r requirements.txt
	@echo "✓ Dependencies installed"

# Run database migrations
migrate:
	@echo "Running migrations..."
	$(PYTHON) manage.py migrate
	@echo "✓ Migrations completed"

# Run development server
dev:
	@echo "Starting development server..."
	$(PYTHON) manage.py runserver

# Open Django shell
shell:
	$(PYTHON) manage.py shell

# Run tests
test:
	$(PYTHON) manage.py test

# Clean Python cache files
clean:
	@echo "Cleaning Python cache files..."
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "✓ Clean completed"

# Setup: install and migrate
setup: install migrate
	@echo "✓ Setup completed"

