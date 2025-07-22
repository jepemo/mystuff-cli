# Python Package Management with uv

Use uv exclusively for Python package management in this project.

## Package Management Commands

- All Python dependencies **must be installed, synchronized, and locked** using uv
- Never use pip, pip-tools, poetry, or conda directly for dependency management

Use these commands:

- Install dependencies: `uv add <package>`
- Remove dependencies: `uv remove <package>`
- Sync dependencies: `uv sync`

## Running Python Code

- Run a Python script with `uv run <script-name>.py`
- Run Python tools like Pytest with `uv run pytest` or `uv run ruff`
- Launch a Python repl with `uv run python`

## Managing Scripts with PEP 723 Inline Metadata

- Run a Python script with inline metadata (dependencies defined at the top of the file) with: `uv run script.py`
- You can add or remove dependencies manually from the `dependencies =` section at the top of the script, or
- Or using uv CLI:
  - `uv add package-name --script script.py`
  - `uv remove package-name --script script.py`

## Testing Requirements

- **Always verify tests** after making any changes to the codebase
- Run the complete test suite with: `./run_tests.sh`
- Run individual unit tests with: `uv run pytest tests/`
- Ensure all tests pass before considering a feature complete

## Code Quality and Linting

- **After running tests**, always execute code quality checks and auto-fixes:
  ```bash
  make fix-all && make check-ci
  ```
- This command will:
  1. `make fix-all`: Automatically fix imports, whitespace, and formatting issues
  2. `make check-ci`: Run the same checks as GitHub Actions to verify code quality
- **If errors are found**, fix them before proceeding:
  - Most errors will be auto-fixed by `make fix-all`
  - Remaining errors (if any) should be fixed manually
  - Re-run `make check-ci` to verify all issues are resolved
- **This ensures** your code will pass CI/CD checks before committing

## Testing with Custom Directory

- **Use the `-d` parameter** when testing to avoid overwriting the default mystuff directory
- The default directory (`~/.mystuff`) may be in active use
- Examples:

  ```bash
  # Test with custom directory
  export MYSTUFF_HOME="/tmp/mystuff-test"
  mystuff init
  mystuff link add --url "https://example.com" --title "Test Link"

  # Or use a temporary directory for each test session
  MYSTUFF_HOME="/tmp/mystuff-$(date +%s)" mystuff init
  ```

- Always clean up test directories after testing:
  ```bash
  rm -rf /tmp/mystuff-test
  ```
