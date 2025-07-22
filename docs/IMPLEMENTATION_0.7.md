# Implementation 0.7 – Sync

## Overview

The **Sync** module provides a flexible system for executing custom command sequences defined in configuration. This module enables users to automate data synchronization, backup workflows, and any personalized maintenance tasks through configurable shell commands. The sync module allows users to:

- Define custom command sequences in `config.yaml`
- Execute all commands with a single command
- Preview commands before execution (dry-run mode)
- Control execution flow with error handling options
- Monitor progress with verbose output
- Maintain consistent execution context

## Features Implemented

### Core Commands

- `mystuff sync run` - Execute all sync commands defined in config.yaml
- `mystuff sync list-commands` - List all configured sync commands

### Command Flags

- `--dry-run` / `-n` - Show commands that would be executed without running them
- `--verbose` / `-v` - Show detailed output during execution
- `--continue-on-error` / `-c` - Continue executing remaining commands even if one fails

### Key Features

- **Configuration-driven**: Commands defined in `config.yaml` under `sync.commands`
- **Shell integration**: Supports any shell command or script
- **Error handling**: Configurable behavior on command failures
- **Progress tracking**: Visual feedback with progress indicators
- **Directory context**: All commands execute within the mystuff directory
- **Safety features**: Dry-run mode for command preview
- **Flexible execution**: Support for complex multi-step workflows

## Configuration

### YAML Structure

The sync module reads commands from the `sync.commands` section in `config.yaml`:

```yaml
# config.yaml
sync:
  commands:
    - echo 'Starting synchronization...'
    - git add . && git commit -m "Auto-sync $(date)"
    - rsync -av data/ backup/
    - echo 'Sync completed!'
```

### Configuration Examples

#### Basic Git Sync

```yaml
sync:
  commands:
    - git add .
    - git commit -m "Auto-sync $(date)"
    - git push origin main
```

#### Cloud Backup

```yaml
sync:
  commands:
    - echo 'Syncing to cloud storage...'
    - rclone sync ~/.mystuff/ remote:mystuff/
    - echo 'Cloud sync completed!'
```

#### Database Backup

```yaml
sync:
  commands:
    - echo 'Creating database backup...'
    - pg_dump mydb > backup/mydb_$(date +%Y%m%d).sql
    - gzip backup/mydb_$(date +%Y%m%d).sql
    - echo 'Database backup completed!'
```

#### Complex Multi-Step Workflow

```yaml
sync:
  commands:
    - echo 'Starting comprehensive sync...'
    - git status
    - git add . && git commit -m "Auto-sync $(date)" || echo 'Nothing to commit'
    - git push origin main || echo 'Push failed, continuing...'
    - rsync -av --delete ~/.mystuff/ /backup/mystuff/
    - find /backup/mystuff/ -name "*.old" -delete
    - echo 'Sync completed at $(date)'
```

## Implementation Details

### File Structure

```
mystuff/commands/sync.py      # Main sync command implementation
tests/test_sync.py           # Comprehensive test suite
```

### Core Functions

#### `get_mystuff_dir() -> Optional[Path]`

- Searches for mystuff directory by looking for `config.yaml`
- Traverses up directory tree from current working directory
- Returns `None` if no mystuff directory found

#### `load_sync_config(mystuff_dir: Path) -> Dict[str, Any]`

- Loads and validates sync configuration from `config.yaml`
- Handles YAML parsing errors gracefully
- Validates presence of `sync` section
- Returns sync configuration dictionary

#### `execute_sync_commands(commands, mystuff_dir, **kwargs) -> bool`

- Executes list of shell commands sequentially
- Supports dry-run, verbose, and continue-on-error modes
- Provides progress feedback and error reporting
- Returns success status boolean

### Command Execution

Commands are executed using `subprocess.run()` with the following characteristics:

- **Working Directory**: Commands execute in the mystuff directory
- **Shell Integration**: Full shell command support including pipes, variables, etc.
- **Output Handling**: Captured output in non-verbose mode, streamed in verbose mode
- **Error Reporting**: Detailed error messages with exit codes
- **Progress Indicators**: Visual feedback during execution

### Error Handling

The sync module provides robust error handling:

- **Configuration Errors**: Missing files, invalid YAML, missing sync section
- **Command Execution Errors**: Failed commands with detailed error reporting
- **Graceful Degradation**: Option to continue execution despite failures
- **User Guidance**: Clear error messages with actionable suggestions

## Usage Examples

### Basic Usage

```bash
# Execute all sync commands
mystuff sync run

# Preview commands without executing
mystuff sync run --dry-run

# Execute with detailed output
mystuff sync run --verbose

# Continue on errors
mystuff sync run --continue-on-error

# List configured commands
mystuff sync list-commands
```

### Advanced Usage

```bash
# Combine flags for detailed dry run
mystuff sync run --dry-run --verbose

# Execute with error tolerance and detailed output
mystuff sync run --continue-on-error --verbose
```

### Configuration Setup

```bash
# Create sync configuration
cat > ~/.mystuff/config.yaml << EOF
sync:
  commands:
    - echo 'Starting sync...'
    - git add . && git commit -m "Auto-sync"
    - rsync -av data/ backup/
    - echo 'Sync completed!'
EOF

# Execute the sync
mystuff sync run
```

## Testing

### Test Coverage

The sync module includes comprehensive testing with 17 test cases covering:

- **Configuration Loading**: Valid/invalid YAML, missing files, missing sections
- **Command Execution**: Success/failure scenarios, dry-run mode, verbose output
- **Error Handling**: Continue-on-error behavior, invalid configurations
- **CLI Integration**: Full command-line interface testing
- **Edge Cases**: Empty command lists, non-list configurations

### Test Files

- `tests/test_sync.py` - Complete test suite with 17 test cases
- All tests pass with 100% success rate
- Tests use temporary directories and mock configurations
- Integration tests verify CLI behavior

### Running Tests

```bash
# Run sync-specific tests
python -m pytest tests/test_sync.py -v

# Run all tests including sync
python -m pytest tests/ -v
```

## Integration

### CLI Integration

The sync module is fully integrated into the main CLI:

- Added to `mystuff/cli.py` as `sync_app`
- Available as `mystuff sync` command group
- Follows consistent CLI patterns with other modules
- Version updated to 0.7.0

### Module Structure

```python
# mystuff/commands/sync.py
sync_app = typer.Typer(help="Execute custom sync commands from configuration")

@sync_app.command()
def run(...):
    """Execute all sync commands defined in config.yaml."""

@sync_app.command()
def list_commands():
    """List all sync commands defined in config.yaml."""
```

## Benefits and Use Cases

### Primary Benefits

- **Automation**: Streamline repetitive synchronization tasks
- **Consistency**: Ensure same commands run every time
- **Flexibility**: Support any shell command or script
- **Safety**: Dry-run mode prevents accidental execution
- **Reliability**: Robust error handling and progress tracking

### Common Use Cases

1. **Data Backup**: Automated backup to local or cloud storage
2. **Version Control**: Automated git commits and pushes
3. **File Synchronization**: Sync between multiple locations
4. **Database Maintenance**: Regular database backups and cleanup
5. **System Maintenance**: Cleanup tasks and health checks
6. **Deployment**: Automated deployment workflows
7. **Content Management**: Sync content between environments

### Workflow Integration

The sync module integrates seamlessly with existing mystuff workflows:

- Complements existing data management modules
- Provides centralized automation for all mystuff operations
- Enables complex workflows spanning multiple data types
- Supports integration with external tools and services

## Future Enhancements

### Potential Improvements

1. **Parallel Execution**: Support for concurrent command execution
2. **Conditional Logic**: Support for conditional command execution
3. **Template Variables**: Dynamic variable substitution in commands
4. **Scheduling**: Integration with cron or system schedulers
5. **Rollback Support**: Ability to undo sync operations
6. **Command Groups**: Organize commands into logical groups
7. **Remote Execution**: Support for remote command execution

### Extensibility

The sync module is designed for easy extension:

- Clear separation of concerns in function structure
- Configurable behavior through flags and configuration
- Plugin-ready architecture for custom command processors
- Integration points for external tools and services

## Summary

The 0.7 Sync module successfully provides a powerful and flexible system for automating custom command sequences within the mystuff ecosystem. It maintains the project's principles of simplicity, reliability, and user-friendliness while adding significant automation capabilities.

Key achievements:

- ✅ Complete implementation with all specified features
- ✅ Comprehensive testing with 17 test cases
- ✅ Full CLI integration following project patterns
- ✅ Robust error handling and user guidance
- ✅ Extensive documentation with practical examples
- ✅ Safe execution with dry-run capabilities
- ✅ Flexible configuration supporting any shell command

The sync module enhances mystuff-cli's value proposition by enabling users to automate their entire knowledge management workflow through simple, configurable command sequences.
