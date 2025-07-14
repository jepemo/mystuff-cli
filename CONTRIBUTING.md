# Contributing to mystuff-cli

Thank you for your interest in contributing to mystuff-cli! This document provides guidelines for contributing to the project.

## Development Setup

1. **Fork and clone the repository**:

   ```bash
   git clone https://github.com/your-username/mystuff-cli.git
   cd mystuff-cli
   ```

2. **Set up the development environment**:

   ```bash
   # Install in development mode
   pip install -e ".[dev]"

   # Or using uv
   uv pip install -e ".[dev]"
   ```

3. **Run tests to ensure everything works**:
   ```bash
   ./run_tests.sh
   ```

## Development Workflow

### Making Changes

1. **Create a new branch**:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:

   - Follow the existing code style
   - Add tests for new functionality
   - Update documentation as needed

3. **Run tests and checks**:

   ```bash
   # Run all tests
   ./run_tests.sh

   # Format code
   black mystuff/ tests/

   # Check linting
   flake8 mystuff/ tests/

   # Type checking
   mypy mystuff/
   ```

4. **Commit your changes**:

   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and create a pull request**:
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Messages

We follow conventional commits format:

- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `test:` for test additions/changes
- `refactor:` for code refactoring
- `chore:` for maintenance tasks

## Code Style

- **Python**: Follow PEP 8 standards
- **Line length**: 88 characters (Black default)
- **Imports**: Use absolute imports, sort with isort
- **Type hints**: Use type hints for all functions
- **Docstrings**: Use Google-style docstrings

## Testing

### Test Structure

- `tests/test_init_simple.py`: Tests for init functionality
- `tests/test_link.py`: Tests for link management
- `tests/test_meeting.py`: Tests for meeting notes
- `tests/test_fzf_integration.py`: Tests for fzf integration

### Writing Tests

- Write tests for all new functionality
- Use descriptive test names
- Include edge cases and error conditions
- Mock external dependencies (like fzf)

### Test Environment

Tests use temporary directories and environment variables:

- `MYSTUFF_HOME`: Points to test directory
- Temporary files are cleaned up automatically

## Documentation

- Update `README.md` for user-facing changes
- Update `PLAN.md` for roadmap changes
- Add docstrings to all functions and classes
- Include examples in docstrings

## Pull Request Process

1. **Ensure tests pass**: All tests must pass before merging
2. **Update documentation**: Include relevant documentation updates
3. **Add tests**: New functionality must include tests
4. **Follow code style**: Code must pass linting and formatting checks
5. **Descriptive PR**: Include clear description of changes

### PR Template

```markdown
## Description

Brief description of changes

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing

- [ ] Tests pass locally
- [ ] Added tests for new functionality
- [ ] Updated documentation

## Checklist

- [ ] Code follows project style
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
```

## Release Process

Releases are automated through GitHub Actions:

1. **Version bump**: Update version in `pyproject.toml`
2. **Create tag**: `git tag v0.x.y && git push origin v0.x.y`
3. **Automated release**: GitHub Actions will:
   - Run all tests
   - Create GitHub release
   - Publish to PyPI (if configured)

## Architecture

### Core Components

- **CLI**: `mystuff/cli.py` - Main CLI entry point
- **Commands**: `mystuff/commands/` - Individual command implementations
- **Tests**: `tests/` - Test suite

### Design Principles

- **Simple file formats**: JSONL for links, Markdown+YAML for meetings
- **Environment-aware**: Respects `$MYSTUFF_HOME`, `$EDITOR`
- **Optional dependencies**: Core functionality works without fzf
- **Comprehensive testing**: Unit and integration tests

## Getting Help

- **Issues**: Report bugs or request features via GitHub Issues
- **Discussions**: Use GitHub Discussions for questions
- **Code Review**: Maintainers will review PRs promptly

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Follow the project's technical standards

Thank you for contributing to mystuff-cli! 🎉
