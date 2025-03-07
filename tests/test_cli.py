import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from git_to_prompt.cli import log
from git_to_prompt.log import get_commits


@pytest.fixture
def mock_repo():
    """Mock repo for testing."""
    return MagicMock()


@pytest.fixture
def mock_get_repo():
    """Mock get_repo function for testing."""
    with patch("git_to_prompt.cli.get_repo") as mock:
        yield mock


@pytest.fixture
def mock_get_commits():
    """Mock get_commits function for testing."""
    with patch("git_to_prompt.cli.get_commits") as mock:
        # Create a generator that yields nothing
        mock.return_value = (x for x in [])
        yield mock


@pytest.fixture
def mock_write_commits():
    """Mock write_commits_as_cxml function for testing."""
    with patch("git_to_prompt.cli.write_commits_as_cxml") as mock:
        yield mock


def test_log_with_paths(mock_get_repo, mock_get_commits, mock_write_commits):
    """Test log function with paths parameter."""
    # Setup
    repo_mock = MagicMock()
    mock_get_repo.return_value = repo_mock
    
    # Call the function - simulate passing paths positionally
    log(None, [Path("test/file.py"), Path("another/file.py")], include_patch=False)
    
    # Check if get_commits was called with the correct path parameters
    mock_get_commits.assert_called_once()
    args, _ = mock_get_commits.call_args
    assert args[0] == repo_mock  # repo
    assert args[1] is None  # revision_range
    assert args[4] == ["test/file.py", "another/file.py"]  # paths


def test_log_with_dash_dash_revision_range(mock_get_repo, mock_get_commits, mock_write_commits):
    """Test log function with -- as revision range."""
    # Setup
    repo_mock = MagicMock()
    mock_get_repo.return_value = repo_mock
    
    # Call the function - simulate passing -- and paths
    log("--", [Path("test/file.py")], include_patch=False)
    
    # Check if get_commits was called with revision_range=None (-- is converted to None)
    mock_get_commits.assert_called_once()
    args, _ = mock_get_commits.call_args
    assert args[0] == repo_mock  # repo
    assert args[1] is None  # revision_range
    assert args[4] == ["test/file.py"]  # paths


def test_log_with_regular_revision_range_and_paths(mock_get_repo, mock_get_commits, mock_write_commits):
    """Test log function with regular revision range and paths."""
    # Setup
    repo_mock = MagicMock()
    mock_get_repo.return_value = repo_mock
    
    # Call the function
    log("HEAD~5..HEAD", [Path("test/file.py")], include_patch=False)
    
    # Check if get_commits was called with the correct arguments
    mock_get_commits.assert_called_once()
    args, _ = mock_get_commits.call_args
    assert args[0] == repo_mock  # repo
    assert args[1] == "HEAD~5..HEAD"  # revision_range
    assert args[4] == ["test/file.py"]  # paths