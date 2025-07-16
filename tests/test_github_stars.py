#!/usr/bin/env python3
"""
Test GitHub stars import functionality
"""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
import urllib.error

# Add the parent directory to the path so we can import mystuff
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from mystuff.commands.link import fetch_github_stars, import_github_stars, load_links, save_links

def test_fetch_github_stars_success():
    """Test successful GitHub stars fetch"""
    mock_response_data = [
        {
            'html_url': 'https://github.com/python/cpython',
            'full_name': 'python/cpython',
            'description': 'The Python programming language',
            'language': 'Python',
            'stargazers_count': 50000
        },
        {
            'html_url': 'https://github.com/microsoft/vscode',
            'full_name': 'microsoft/vscode',
            'description': 'Visual Studio Code',
            'language': 'TypeScript',
            'stargazers_count': 40000
        }
    ]
    
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(mock_response_data).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_response
        
        stars = fetch_github_stars('testuser')
        
        assert len(stars) == 2
        assert stars[0]['url'] == 'https://github.com/python/cpython'
        assert stars[0]['title'] == 'python/cpython'
        assert stars[0]['description'] == 'The Python programming language'
        assert 'testuser' in stars[0]['tags']
        assert 'github' in stars[0]['tags']
        assert stars[0]['language'] == 'Python'
        assert stars[0]['stars'] == 50000

def test_fetch_github_stars_user_not_found():
    """Test GitHub stars fetch with non-existent user"""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url='test', code=404, msg='Not Found', hdrs=None, fp=None
        )
        
        stars = fetch_github_stars('nonexistentuser')
        
        assert stars == []

def test_fetch_github_stars_rate_limit():
    """Test GitHub stars fetch with rate limit exceeded"""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url='test', code=403, msg='Forbidden', hdrs=None, fp=None
        )
        
        stars = fetch_github_stars('testuser')
        
        assert stars == []

def test_import_github_stars_integration():
    """Test complete GitHub stars import process"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up temporary mystuff directory
        mystuff_dir = Path(temp_dir) / '.mystuff'
        mystuff_dir.mkdir()
        
        # Mock environment variable
        with patch.dict(os.environ, {'MYSTUFF_HOME': str(mystuff_dir)}):
            # Create some existing links
            existing_links = [
                {
                    'url': 'https://github.com/python/cpython',
                    'title': 'Python CPython',
                    'description': 'Existing Python repo',
                    'tags': ['python'],
                    'timestamp': '2025-01-01T00:00:00'
                }
            ]
            save_links(existing_links)
            
            # Mock GitHub API response
            mock_response_data = [
                {
                    'html_url': 'https://github.com/python/cpython',  # Already exists
                    'full_name': 'python/cpython',
                    'description': 'The Python programming language',
                    'language': 'Python',
                    'stargazers_count': 50000
                },
                {
                    'html_url': 'https://github.com/microsoft/vscode',  # New
                    'full_name': 'microsoft/vscode',
                    'description': 'Visual Studio Code',
                    'language': 'TypeScript',
                    'stargazers_count': 40000
                }
            ]
            
            with patch('urllib.request.urlopen') as mock_urlopen:
                mock_response = Mock()
                mock_response.read.return_value = json.dumps(mock_response_data).encode()
                mock_response.__enter__ = Mock(return_value=mock_response)
                mock_response.__exit__ = Mock(return_value=None)
                mock_urlopen.return_value = mock_response
                
                # Import stars
                imported_count = import_github_stars('testuser')
                
                # Should import 1 new star (vscode), skip 1 existing (cpython)
                assert imported_count == 1
                
                # Check that links were saved correctly
                all_links = load_links()
                assert len(all_links) == 2
                
                # Find the new vscode link
                vscode_link = next(link for link in all_links if 'vscode' in link['url'])
                assert vscode_link['title'] == 'microsoft/vscode'
                assert vscode_link['description'] == 'Visual Studio Code'
                assert 'testuser' in vscode_link['tags']
                assert 'github' in vscode_link['tags']

def run_tests():
    """Run all tests"""
    test_functions = [
        test_fetch_github_stars_success,
        test_fetch_github_stars_user_not_found,
        test_fetch_github_stars_rate_limit,
        test_import_github_stars_integration,
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
