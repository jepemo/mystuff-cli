#!/bin/bash

# Test script for mystuff-cli
# This script runs all tests in the proper order

set -e

echo "🧪 Running mystuff-cli tests..."

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run a test and report results
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -e "${YELLOW}Running $test_name...${NC}"
    
    if eval "$test_command"; then
        echo -e "${GREEN}✅ $test_name passed!${NC}"
        return 0
    else
        echo -e "${RED}❌ $test_name failed!${NC}"
        return 1
    fi
}

# Set up test environment
export MYSTUFF_HOME="/tmp/test_mystuff_script"
rm -rf "$MYSTUFF_HOME"

echo "🏗️  Setting up test environment..."
echo "   Test directory: $MYSTUFF_HOME"

# Synchronize the project environment through uv.
echo "📦 Synchronizing development environment..."
uv sync --all-extras

# Run unit tests
echo -e "\n🔧 Running unit tests..."
run_test "Init tests" "uv run python tests/test_init_simple.py"
run_test "Link tests" "uv run python tests/test_link.py"
run_test "Meeting tests" "uv run python tests/test_meeting.py"
run_test "Journal tests" "uv run python tests/test_journal_simple.py"
run_test "Wiki tests" "uv run python tests/test_wiki_simple.py"
run_test "Eval tests" "uv run python tests/test_eval_simple.py"
run_test "Lists tests" "uv run python tests/test_lists_simple.py"
run_test "GitHub stars tests" "uv run python tests/test_github_stars.py"
run_test "Error handling tests" "uv run python tests/test_error_handling.py"
run_test "fzf integration tests" "uv run python tests/test_fzf_integration.py"

# Run integration tests
echo -e "\n🔗 Running integration tests..."
run_test "CLI version" "uv run python -m mystuff.cli --version"
run_test "CLI help" "uv run python -m mystuff.cli --help >/dev/null"
run_test "CLI init" "uv run python -m mystuff.cli init --force"

# Test basic functionality
echo -e "\n⚙️  Testing basic functionality..."
run_test "Add link" "uv run python -m mystuff.cli link add --url 'https://github.com' --title 'GitHub'"
run_test "List links" "uv run python -m mystuff.cli link list"
run_test "Search links" "uv run python -m mystuff.cli link search 'GitHub'"

run_test "Add meeting" "uv run python -m mystuff.cli meeting add --title 'Test Meeting' --date '2023-12-01' --no-edit"
run_test "List meetings" "uv run python -m mystuff.cli meeting list"
run_test "Search meetings" "uv run python -m mystuff.cli meeting search 'Test'"

run_test "Add journal" "uv run python -m mystuff.cli journal add --date '2023-12-01' --body 'Test journal entry' --no-edit"
run_test "List journals" "uv run python -m mystuff.cli journal list --no-interactive"
run_test "Search journals" "uv run python -m mystuff.cli journal search 'Test' --no-interactive"

run_test "Add wiki" "uv run python -m mystuff.cli wiki new 'Test Wiki Note' --tag 'test' --body 'Test wiki content' --no-edit"
run_test "List wikis" "uv run python -m mystuff.cli wiki list --no-interactive"
run_test "Search wikis" "uv run python -m mystuff.cli wiki search 'Test' --no-interactive"

# Check if fzf is available
if command -v fzf &> /dev/null; then
    echo -e "\n🔍 fzf is available - interactive features enabled"
else
    echo -e "\n⚠️  fzf not available - interactive features disabled"
fi

# Clean up
echo -e "\n🧹 Cleaning up test environment..."
rm -rf "$MYSTUFF_HOME"

echo -e "\n${GREEN}🎉 All tests completed successfully!${NC}"
