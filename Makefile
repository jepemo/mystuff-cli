# Makefile for mystuff-cli development
.PHONY: help install install-dev test test-coverage lint format check fix clean all

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

help: ## Show available commands
	@echo "$(BOLD)MyStuff CLI Development Commands$(RESET)"
	@echo ""
	@echo "$(YELLOW)🔨 Development Workflow:$(RESET)"
	@echo "  make install-dev    - Install development environment"
	@echo "  make sync-deps      - Sync dependencies with UV"
	@echo "  make deps-update    - Update dependencies to latest versions"
	@echo ""
	@echo "$(YELLOW)🧹 Code Quality:$(RESET)"
	@echo "  make format         - Format code with black + isort"
	@echo "  make fix-all        - Auto-fix all possible linting issues"
	@echo "  make fix-imports    - Remove unused imports"
	@echo "  make fix-whitespace - Fix trailing whitespace"
	@echo ""
	@echo "$(YELLOW)✅ Linting & Checks:$(RESET)"
	@echo "  make lint           - Run all linting checks"
	@echo "  make quick-lint     - Run fast flake8 check only"
	@echo "  make check-ci       - Run GitHub Actions equivalent checks"
	@echo "  make check          - Run all quality checks (lint + test)"
	@echo ""
	@echo "$(YELLOW)🧪 Testing:$(RESET)"
	@echo "  make test           - Run all tests"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo "  make test-sync      - Run only sync module tests"
	@echo ""
	@echo "$(YELLOW)🏗️ Build & Deploy:$(RESET)"
	@echo "  make build          - Build the package"
	@echo "  make clean          - Clean build artifacts"
	@echo ""
	@echo "$(YELLOW)📚 Documentation:$(RESET)"
	@echo "  make docs-check     - Check documentation status"
	@echo ""
	@echo "$(YELLOW)🚀 Full Workflow:$(RESET)"
	@echo "  make all            - Run complete development workflow"
	@echo ""
	@echo "$(GREEN)💡 Tip: Use 'make fix-all' before committing to auto-fix most issues!$(RESET)"

install: ## Install the package in development mode
	@echo "$(BLUE)Installing mystuff-cli in development mode...$(RESET)"
	uv pip install -e .

install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(RESET)"
	uv sync --dev

test: ## Run tests
	@echo "$(BLUE)Running tests...$(RESET)"
	uv run pytest tests/ -v

test-coverage: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(RESET)"
	uv run pytest tests/ --cov=mystuff --cov-report=term-missing --cov-report=html

test-sync: ## Run only sync module tests
	@echo "$(BLUE)Running sync tests...$(RESET)"
	uv run pytest tests/test_sync.py -v

lint: ## Run all linting checks (black, flake8, mypy)
	@echo "$(BLUE)Running all linting checks...$(RESET)"
	@$(MAKE) lint-black
	@$(MAKE) lint-flake8
	@$(MAKE) lint-mypy
	@echo "$(GREEN)All linting checks completed!$(RESET)"

lint-black: ## Check code formatting with black
	@echo "$(BLUE)Checking code formatting with black...$(RESET)"
	uv run black --check --diff mystuff/ tests/

lint-flake8: ## Run flake8 linting
	@echo "$(BLUE)Running flake8 linting...$(RESET)"
	uv run flake8 mystuff/ tests/ --max-line-length=88 --extend-ignore=E203,W503

lint-mypy: ## Run mypy type checking
	@echo "$(BLUE)Running mypy type checking...$(RESET)"
	uv run mypy mystuff/ --ignore-missing-imports || true

lint-isort: ## Check import sorting with isort
	@echo "$(BLUE)Checking import sorting with isort...$(RESET)"
	uv run isort --check-only --diff mystuff/ tests/

fix-imports: ## Remove unused imports automatically
	@echo "$(BLUE)Removing unused imports...$(RESET)"
	uv run autoflake --remove-all-unused-imports --recursive --in-place mystuff/ tests/

fix-whitespace: ## Fix trailing whitespace and blank lines
	@echo "$(BLUE)Fixing whitespace issues...$(RESET)"
	@find mystuff/ tests/ -name "*.py" -exec sed -i '' 's/[[:space:]]*$$//' {} \;
	@echo "$(GREEN)Whitespace fixed!$(RESET)"

fix-all: ## Auto-fix all possible linting issues
	@echo "$(BLUE)Auto-fixing all possible issues...$(RESET)"
	@$(MAKE) fix-imports
	@$(MAKE) fix-whitespace
	@$(MAKE) format
	@echo "$(GREEN)All auto-fixes completed!$(RESET)"

lint-ruff: ## Run ruff linting (fast alternative)
	@echo "$(BLUE)Running ruff linting...$(RESET)"
	uv run ruff check mystuff/ tests/

format: ## Auto-format code with black and isort
	@echo "$(BLUE)Formatting code with black...$(RESET)"
	uv run black mystuff/ tests/
	@echo "$(BLUE)Sorting imports with isort...$(RESET)"
	uv run isort mystuff/ tests/
	@echo "$(GREEN)Code formatting completed!$(RESET)"

fix: ## Auto-fix code issues where possible
	@echo "$(BLUE)Auto-fixing code issues...$(RESET)"
	@$(MAKE) format
	uv run ruff check --fix mystuff/ tests/ || true
	@echo "$(GREEN)Auto-fix completed!$(RESET)"

check: ## Run all checks (format, lint, test) - CI equivalent
	@echo "$(BLUE)Running all quality checks...$(RESET)"
	@$(MAKE) lint
	@$(MAKE) test
	@echo "$(GREEN)All checks passed!$(RESET)"

check-ci: ## Run checks exactly like GitHub Actions
	@echo "$(BLUE)Running GitHub Actions equivalent checks...$(RESET)"
	@echo "$(YELLOW)1. Code formatting (black)...$(RESET)"
	uv run black --check --diff mystuff/ tests/
	@echo "$(YELLOW)2. Linting (flake8)...$(RESET)"
	uv run flake8 mystuff/ tests/ --max-line-length=88 --extend-ignore=E203,W503
	@echo "$(YELLOW)3. Type checking (mypy)...$(RESET)"
	uv run mypy mystuff/ --ignore-missing-imports || true
	@echo "$(YELLOW)4. Running tests...$(RESET)"
	uv run pytest tests/ -v
	@echo "$(GREEN)All CI checks completed!$(RESET)"

build: ## Build the package
	@echo "$(BLUE)Building package...$(RESET)"
	uv build

clean: ## Clean up generated files
	@echo "$(BLUE)Cleaning up...$(RESET)"
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

sync-deps: ## Sync and update dependencies
	@echo "$(BLUE)Syncing dependencies...$(RESET)"
	uv sync --dev

version: ## Show version information
	@echo "$(BLUE)Version Information:$(RESET)"
	@echo "mystuff-cli: $(shell uv run python -c 'import mystuff; print(mystuff.__version__ if hasattr(mystuff, "__version__") else "development")')"
	@echo "Python: $(shell python --version)"
	@echo "uv: $(shell uv --version)"

dev-setup: ## Complete development setup
	@echo "$(BLUE)Setting up development environment...$(RESET)"
	@$(MAKE) install-dev
	@$(MAKE) install
	@echo "$(GREEN)Development environment ready!$(RESET)"
	@echo "$(YELLOW)Next steps:$(RESET)"
	@echo "  - Run 'make test' to run tests"
	@echo "  - Run 'make lint' to check code quality"
	@echo "  - Run 'make check' to run all checks"
	@echo "  - Run 'make help' to see all available commands"

# Quick development commands
quick-test: ## Quick test run (no coverage)
	@uv run pytest tests/ -x --tb=short

quick-lint: ## Quick lint check (only flake8)
	@uv run flake8 mystuff/ tests/ --max-line-length=88 --extend-ignore=E203,W503

# Specific module testing
test-init: ## Test init module
	@uv run pytest tests/test_init*.py -v

test-link: ## Test link module
	@uv run pytest tests/test_link.py -v

test-meeting: ## Test meeting module
	@uv run pytest tests/test_meeting.py -v

test-all-modules: ## Test all individual modules
	@echo "$(BLUE)Testing all modules...$(RESET)"
	@$(MAKE) test-link
	@$(MAKE) test-meeting
	@$(MAKE) test-sync

# Documentation
docs-check: ## Check if documentation is up to date
	@echo "$(BLUE)Checking documentation...$(RESET)"
	@echo "Implementation docs:"
	@ls -la docs/IMPLEMENTATION_*.md
	@echo "$(GREEN)Documentation check completed!$(RESET)"

all: ## Run complete development workflow
	@echo "$(BLUE)Running complete development workflow...$(RESET)"
	@$(MAKE) clean
	@$(MAKE) install-dev
	@$(MAKE) format
	@$(MAKE) lint
	@$(MAKE) test-coverage
	@$(MAKE) build
	@echo "$(GREEN)Complete workflow finished!$(RESET)"
