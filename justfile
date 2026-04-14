# napoln development commands

set dotenv-load := false

# List available commands
default:
    @just --list

# Run all checks (lint, typecheck, test)
check: lint test

# Run the full test suite
test *args:
    uv run pytest {{ args }}

# Run tests with coverage report
coverage:
    uv run pytest --cov=napoln --cov-report=term-missing

# Run only unit tests
unit *args:
    uv run pytest tests/unit/ {{ args }}

# Run only integration tests
integration *args:
    uv run pytest tests/integration/ {{ args }}

# Run only BDD tests
bdd *args:
    uv run pytest tests/steps/ {{ args }}

# Lint and format check
lint:
    uv run ruff check src/ tests/
    uv run ruff format --check src/ tests/

# Auto-fix lint and formatting
fix:
    uv run ruff check --fix src/ tests/
    uv run ruff format src/ tests/

# Install dev dependencies
setup:
    uv sync --extra dev

# Run napoln CLI
run *args:
    uv run napoln {{ args }}

# Run napoln doctor on this machine
doctor:
    uv run napoln doctor

# Build the package
build:
    uv build

# Clean build artifacts and caches
clean:
    rm -rf dist/ build/ .pytest_cache/ .coverage
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
