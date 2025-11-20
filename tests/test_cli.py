from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from git_to_prompt.cli import app


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
    """Test log command with paths parameter."""
    # Setup
    repo_mock = MagicMock()
    mock_get_repo.return_value = repo_mock

    # Call the app with a command string
    app("log -- test/file.py another/file.py")

    # Check if get_commits was called with the correct path parameters
    mock_get_commits.assert_called_once()
    args, _ = mock_get_commits.call_args
    assert args[0] == repo_mock  # repo
    assert args[1] is None  # revision_range
    assert args[4] == ["test/file.py", "another/file.py"]  # paths


def test_log_with_dash_dash_revision_range(
    mock_get_repo, mock_get_commits, mock_write_commits
):
    """Test log command with -- as revision range."""
    # Setup
    repo_mock = MagicMock()
    mock_get_repo.return_value = repo_mock

    # Call the app with a command string
    app("log -- test/file.py")

    # Check if get_commits was called with revision_range=None (-- is converted to None)
    mock_get_commits.assert_called_once()
    args, _ = mock_get_commits.call_args
    assert args[0] == repo_mock  # repo
    assert args[1] is None  # revision_range
    assert args[4] == ["test/file.py"]  # paths


def test_log_with_regular_revision_range_and_paths(
    mock_get_repo, mock_get_commits, mock_write_commits
):
    """Test log command with regular revision range and paths."""
    # Setup
    repo_mock = MagicMock()
    mock_get_repo.return_value = repo_mock

    # Call the app with a command string
    app("log HEAD~5..HEAD -- test/file.py")

    # Check if get_commits was called with the correct arguments
    mock_get_commits.assert_called_once()
    args, _ = mock_get_commits.call_args
    assert args[0] == repo_mock  # repo
    assert args[1] == "HEAD~5..HEAD"  # revision_range
    assert args[4] == ["test/file.py"]  # paths


def test_log_with_relative_paths_from_subfolder(
    mock_get_repo, mock_get_commits, mock_write_commits
):
    """Test log command with relative paths when executed from a subfolder."""
    # Setup
    repo_mock = MagicMock()
    repo_mock.working_dir = "/repo/root"
    mock_get_repo.return_value = repo_mock

    # Mock current working directory to be a subfolder of the repo
    with patch("pathlib.Path.cwd") as mock_cwd:
        mock_cwd.return_value = Path("/repo/root/some/subfolder")

        # Call the app with a command string using relative paths
        app("log -- ../another/file.py ./current/file.py")

    # Check if get_commits was called with paths properly adjusted to be relative to repo root
    mock_get_commits.assert_called_once()
    args, _ = mock_get_commits.call_args
    assert args[0] == repo_mock  # repo
    assert args[1] is None  # revision_range
    assert (
        "some/subfolder/current/file.py" in args[4]
    )  # Relative path from current folder
    assert (
        "some/subfolder/../another/file.py" in args[4]
    )  # The path is added but .. is not resolved


def test_show_defaults_to_patch(mock_get_repo, mock_get_commits, mock_write_commits):
    """Show should default to including patches and limit to a single commit."""

    repo_mock = MagicMock()
    mock_get_repo.return_value = repo_mock

    app("show abc123")

    mock_get_commits.assert_called_once()
    args, _ = mock_get_commits.call_args
    assert args[0] == repo_mock
    assert args[1] == "abc123"
    assert args[2] is True  # include_patch defaults to True
    assert args[3] == 1  # max_count fixed to 1


def test_show_with_paths_from_subfolder(
    mock_get_repo, mock_get_commits, mock_write_commits
):
    """Paths should be normalized relative to repo root for show."""

    repo_mock = MagicMock()
    repo_mock.working_dir = "/repo/root"
    mock_get_repo.return_value = repo_mock

    with patch("pathlib.Path.cwd") as mock_cwd:
        mock_cwd.return_value = Path("/repo/root/sub")

        app("show HEAD -- file.py")

    mock_get_commits.assert_called_once()
    args, _ = mock_get_commits.call_args
    assert args[4] == ["sub/file.py"]
