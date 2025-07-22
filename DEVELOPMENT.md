# Development Guide - MyStuff CLI

## 🚀 Initial Setup

```bash
# 1. Install development environment
make install-dev

# 2. Verify everything works
make help
```

## 🛠️ Daily Workflow

### Before making commits

```bash
# Auto-fix common errors
make fix-all

# Verify everything is good (like in GitHub Actions)
make check-ci
```

### Most useful commands

```bash
# Formatting and automatic fixes
make format         # Format code with black + isort
make fix-all        # Fix imports, whitespace, and formatting
make fix-imports    # Only remove unused imports
make fix-whitespace # Only fix whitespace

# Quick checks
make quick-lint     # Quick check with flake8
make lint          # All linting checks
make check-ci      # Simulate GitHub Actions exactly

# Testing
make test          # Run all tests
make test-coverage # Tests with coverage report
make test-sync     # Only sync module tests

# Dependency management
make sync-deps     # Sync dependencies with UV
make deps-update   # Update all dependencies
```

## 📋 Current Linting Status

After setting up this environment, we have significantly reduced linting errors:

### ✅ Automatically Fixed Errors

- **Unused imports**: Removed with `autoflake`
- **Formatting**: Fixed with `black` and `isort`
- **Trailing whitespace**: Removed with `sed`
- **Line spacing**: Fixed with `black`

### ⚠️ Remaining Errors (Require Manual Correction)

- **Lines too long** (E501): ~15 cases
- **Unnecessary f-strings** (F541): ~12 cases
- **Bare except** (E722): 2 cases
- **Comparisons with True/False** (E712): ~6 cases
- **Unused variables** (F841): 1 case
- **Imports in wrong place** (E402): ~4 cases
- **Undefined variables** (F821): 3 cases in tests

## 🎯 Commands by Situation

### 💻 Day-to-day development

```bash
make format && make test-sync  # Format and test changes
```

### 🔍 Before committing

```bash
make fix-all && make check-ci  # Auto-fix and verify everything
```

### 🚀 Before pushing

```bash
make all  # Complete flow: clean + install + format + lint + test
```

### 🐛 When something fails in CI

```bash
make check-ci  # Replicate exactly what GitHub Actions does
```

## 📦 Installed Tools

- **black**: Code formatting
- **isort**: Import sorting
- **flake8**: Basic linting
- **mypy**: Type checking
- **ruff**: Advanced linting
- **autoflake**: Unused import removal
- **pytest**: Testing framework
- **pytest-cov**: Coverage reporting

## 🎨 Custom Configuration

All tools are configured in `pyproject.toml`:

- **black**: 88 characters per line
- **isort**: Compatible with black
- **flake8**: Ignores E203,W503 (conflicts with black)
- **mypy**: Ignores missing imports
- **pytest**: Auto-discovery of tests

## 💡 Tips

1. **Use `make help`** to see all available commands
2. **`make fix-all`** solves most problems automatically
3. **`make check-ci`** tells you exactly what will fail in GitHub Actions
4. **Remaining errors** are mainly cosmetic and can be fixed gradually
5. **UV handles everything**: No need to install dependencies manually

## 🔄 GitHub Actions Equivalence

| Local Command   | GitHub Actions   |
| --------------- | ---------------- |
| `make check-ci` | Complete checks  |
| `make format`   | Auto-formatting  |
| `make lint`     | Complete linting |
| `make test`     | Testing          |

Now you have complete parity between your local environment and CI/CD! 🎉
