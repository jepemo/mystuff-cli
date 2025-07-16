#!/usr/bin/env python3
"""
Test error handling for missing mystuff directory
"""
import os
import tempfile
from pathlib import Path
import subprocess
import sys

# Add the parent directory to the path so we can import mystuff
sys.path.insert(0, str(Path(__file__).parent.parent))

from mystuff.commands.link import check_mystuff_directory_exists, handle_mystuff_directory_error

def test_check_mystuff_directory_exists():
    """Test check_mystuff_directory_exists function"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test with existing directory
        with tempfile.TemporaryDirectory() as existing_dir:
            # Store original environment
            original_env = os.environ.get('MYSTUFF_HOME')
            try:
                os.environ['MYSTUFF_HOME'] = existing_dir
                # This should return True
                assert check_mystuff_directory_exists() == True
            finally:
                # Restore original environment
                if original_env is not None:
                    os.environ['MYSTUFF_HOME'] = original_env
                elif 'MYSTUFF_HOME' in os.environ:
                    del os.environ['MYSTUFF_HOME']
        
        # Test with non-existing directory
        nonexistent_dir = Path(temp_dir) / "nonexistent"
        original_env = os.environ.get('MYSTUFF_HOME')
        try:
            os.environ['MYSTUFF_HOME'] = str(nonexistent_dir)
            # This should return False
            assert check_mystuff_directory_exists() == False
        finally:
            # Restore original environment
            if original_env is not None:
                os.environ['MYSTUFF_HOME'] = original_env
            elif 'MYSTUFF_HOME' in os.environ:
                del os.environ['MYSTUFF_HOME']

def test_handle_mystuff_directory_error():
    """Test handle_mystuff_directory_error function"""
    import typer
    
    try:
        handle_mystuff_directory_error()
        # Should not reach here
        assert False, "Expected typer.Exit to be raised"
    except typer.Exit as e:
        # Should exit with code 1
        assert e.exit_code == 1

def test_cli_error_handling():
    """Test CLI error handling with subprocess"""
    import tempfile
    
    with tempfile.TemporaryDirectory() as temp_dir:
        nonexistent_dir = Path(temp_dir) / "nonexistent"
        
        # Set environment variable for the subprocess
        env = os.environ.copy()
        env['MYSTUFF_HOME'] = str(nonexistent_dir)
        
        # Test mystuff link list
        result = subprocess.run(
            [sys.executable, '-m', 'mystuff.cli', 'link', 'list'],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 1
        assert "MyStuff directory not found" in result.stderr
        assert "mystuff init" in result.stderr
        
        # Test mystuff link add
        result = subprocess.run(
            [sys.executable, '-m', 'mystuff.cli', 'link', 'add', '--url', 'https://example.com'],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 1
        assert "MyStuff directory not found" in result.stderr
        assert "mystuff init" in result.stderr

def run_tests():
    """Run all tests"""
    test_functions = [
        test_check_mystuff_directory_exists,
        test_handle_mystuff_directory_error,
        test_cli_error_handling,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            print(f"Running {test_func.__name__}...")
            test_func()
            print(f"✅ {test_func.__name__} passed")
            passed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} failed: {e}")
            failed += 1
    
    print(f"\nTest Results: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
