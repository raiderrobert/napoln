# List available recipes
default:
    @just --list

# Run all checks (fmt, lint, type, test)
check:
    uv run ruff format --check src/ tests/
    uv run ruff check src/ tests/
    uv run ty check src/
    uv run pytest

# Run tests
test *args:
    uv run pytest {{ args }}

# Run tests with coverage
coverage:
    uv run pytest --cov=napoln --cov-report=term-missing

# Build the package
build:
    uv build

# Run formatting and lint fixes
fmt:
    uv run ruff format src/ tests/
    uv run ruff check --fix src/ tests/

# Install dev dependencies
setup:
    uv sync --extra dev

# Install napoln locally
install:
    uv tool install --editable .

# Clean build artifacts and caches
clean:
    rm -rf dist/ build/ .pytest_cache/ .coverage
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
