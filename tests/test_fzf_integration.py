"""
Tests for fzf integration functionality
"""
import subprocess
from unittest.mock import patch, MagicMock
from pathlib import Path

from mystuff.commands.link import is_fzf_available, select_link_with_fzf
from mystuff.commands.meeting import select_meeting_with_fzf


def test_is_fzf_available_when_installed():
    """Test fzf availability detection when fzf is installed"""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        
        assert is_fzf_available() is True
        mock_run.assert_called_once_with(
            ["fzf", "--version"], 
            capture_output=True, 
            check=True
        )


def test_is_fzf_available_when_not_installed():
    """Test fzf availability detection when fzf is not installed"""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = FileNotFoundError()
        
        assert is_fzf_available() is False


def test_is_fzf_available_when_fails():
    """Test fzf availability detection when fzf command fails"""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, ["fzf"])
        
        assert is_fzf_available() is False


def test_select_link_with_fzf_success():
    """Test successful link selection with fzf"""
    links = [
        {
            "title": "Example Link",
            "url": "https://example.com",
            "description": "Test description",
            "tags": ["test", "example"],
            "date": "2023-12-01"
        },
        {
            "title": "Another Link",
            "url": "https://another.com", 
            "description": "Another description",
            "tags": ["other"],
            "date": "2023-12-02"
        }
    ]
    
    expected_options = [
        "Example Link | https://example.com | 2023-12-01 [test, example]",
        "Another Link | https://another.com | 2023-12-02 [other]"
    ]
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=expected_options[0] + "\n"
        )
        
        selected = select_link_with_fzf(links)
        
        assert selected == links[0]
        mock_run.assert_called_once_with(
            ["fzf", "--prompt=Select link: ", "--preview-window=down:3:wrap", "--delimiter=|", "--with-nth=1,2"],
            input="\n".join(expected_options),
            text=True,
            capture_output=True,
            check=True
        )


def test_select_link_with_fzf_cancelled():
    """Test link selection cancelled by user"""
    links = [
        {
            "title": "Example Link",
            "url": "https://example.com",
            "description": "Test description",
            "tags": ["test"],
            "date": "2023-12-01"
        }
    ]
    
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, ["fzf"])
        
        selected = select_link_with_fzf(links)
        
        assert selected is None


def test_select_link_with_fzf_keyboard_interrupt():
    """Test link selection interrupted by keyboard"""
    links = [
        {
            "title": "Example Link",
            "url": "https://example.com",
            "description": "Test description",
            "tags": ["test"],
            "date": "2023-12-01"
        }
    ]
    
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = KeyboardInterrupt()
        
        selected = select_link_with_fzf(links)
        
        assert selected is None


def test_select_link_with_fzf_empty_list():
    """Test link selection with empty list"""
    links = []
    
    selected = select_link_with_fzf(links)
    
    assert selected is None


def test_select_meeting_with_fzf_success():
    """Test successful meeting selection with fzf"""
    meetings = [
        {
            "title": "Team Meeting",
            "date": "2023-12-01",
            "participants": ["Alice", "Bob"],
            "tags": ["weekly", "team"],
            "file_path": Path("/tmp/team-meeting.md")
        },
        {
            "title": "Project Review",
            "date": "2023-12-02", 
            "participants": ["Charlie"],
            "tags": ["project"],
            "file_path": Path("/tmp/project-review.md")
        }
    ]
    
    expected_options = [
        "2023-12-01 | Team Meeting | Alice, Bob | [weekly, team]",
        "2023-12-02 | Project Review | Charlie | [project]"
    ]
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=expected_options[0] + "\n"
        )
        
        selected = select_meeting_with_fzf(meetings)
        
        assert selected == meetings[0]
        mock_run.assert_called_once_with(
            ['fzf', '--prompt=Select meeting: ', '--height=40%', '--reverse'],
            input="\n".join(expected_options),
            text=True,
            capture_output=True,
            check=True
        )


def test_select_meeting_with_fzf_no_participants():
    """Test meeting selection with no participants"""
    meetings = [
        {
            "title": "Solo Meeting",
            "date": "2023-12-01",
            "participants": [],
            "tags": ["solo"],
            "file_path": Path("/tmp/solo-meeting.md")
        }
    ]
    
    expected_options = [
        "2023-12-01 | Solo Meeting | [solo]"
    ]
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=expected_options[0] + "\n"
        )
        
        selected = select_meeting_with_fzf(meetings)
        
        assert selected == meetings[0]


def test_select_meeting_with_fzf_no_tags():
    """Test meeting selection with no tags"""
    meetings = [
        {
            "title": "Simple Meeting",
            "date": "2023-12-01",
            "participants": ["Alice"],
            "tags": [],
            "file_path": Path("/tmp/simple-meeting.md")
        }
    ]
    
    expected_options = [
        "2023-12-01 | Simple Meeting | Alice"
    ]
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=expected_options[0] + "\n"
        )
        
        selected = select_meeting_with_fzf(meetings)
        
        assert selected == meetings[0]


if __name__ == "__main__":
    print("Running test_is_fzf_available_when_installed...")
    test_is_fzf_available_when_installed()
    print("✅ test_is_fzf_available_when_installed passed!")
    
    print("Running test_is_fzf_available_when_not_installed...")
    test_is_fzf_available_when_not_installed()
    print("✅ test_is_fzf_available_when_not_installed passed!")
    
    print("Running test_is_fzf_available_when_fails...")
    test_is_fzf_available_when_fails()
    print("✅ test_is_fzf_available_when_fails passed!")
    
    print("Running test_select_link_with_fzf_success...")
    test_select_link_with_fzf_success()
    print("✅ test_select_link_with_fzf_success passed!")
    
    print("Running test_select_link_with_fzf_cancelled...")
    test_select_link_with_fzf_cancelled()
    print("✅ test_select_link_with_fzf_cancelled passed!")
    
    print("Running test_select_link_with_fzf_keyboard_interrupt...")
    test_select_link_with_fzf_keyboard_interrupt()
    print("✅ test_select_link_with_fzf_keyboard_interrupt passed!")
    
    print("Running test_select_link_with_fzf_empty_list...")
    test_select_link_with_fzf_empty_list()
    print("✅ test_select_link_with_fzf_empty_list passed!")
    
    print("Running test_select_meeting_with_fzf_success...")
    test_select_meeting_with_fzf_success()
    print("✅ test_select_meeting_with_fzf_success passed!")
    
    print("Running test_select_meeting_with_fzf_no_participants...")
    test_select_meeting_with_fzf_no_participants()
    print("✅ test_select_meeting_with_fzf_no_participants passed!")
    
    print("Running test_select_meeting_with_fzf_no_tags...")
    test_select_meeting_with_fzf_no_tags()
    print("✅ test_select_meeting_with_fzf_no_tags passed!")
    
    print("\n🎉 All fzf integration tests passed!")
