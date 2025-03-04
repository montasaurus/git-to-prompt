import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from git import Repo

from git_to_prompt.log import (
    Commit,
    FileChange,
    get_commits,
    get_repo,
)


@pytest.fixture
def sample_git_commit() -> MagicMock:
    """Create a sample git commit mock object."""
    mock_commit = MagicMock()
    mock_commit.hexsha = "1234567890abcdef1234567890abcdef12345678"
    mock_commit.author.name = "Test Author"
    mock_commit.author.email = "test@example.com"
    mock_commit.authored_datetime = datetime(2023, 1, 1, tzinfo=timezone.utc)
    mock_commit.committer.name = "Test Committer"
    mock_commit.committer.email = "committer@example.com"
    mock_commit.committed_datetime = datetime(2023, 1, 2, tzinfo=timezone.utc)
    mock_commit.message = "Test commit message\n\nMore details about the commit."
    mock_commit.summary = "Test commit message"
    mock_commit.parents = []
    mock_commit.stats.files = {}

    return mock_commit


@pytest.fixture
def sample_file_change() -> FileChange:
    """Create a sample file change object."""
    return FileChange(
        path="test/file.py",
        change_type="M",
        insertions=10,
        deletions=5,
        content="     def test_function():\n     -    return 'old'\n4   +    return 'new'",
        old_path=None,
    )


def test_commit_from_git_commit(sample_git_commit: MagicMock):
    """Test the creation of a Commit object from a GitPython Commit object."""
    # Prepare sample_git_commit for testing with no file changes
    sample_git_commit.diff.return_value = []

    # Create a commit without file changes
    commit = Commit.from_git_commit(sample_git_commit, include_files=False)

    # Verify the commit has the expected values
    assert commit.hexsha == "1234567890abcdef1234567890abcdef12345678"
    assert commit.short_sha == "1234567"
    assert commit.author_name == "Test Author"
    assert commit.author_email == "test@example.com"
    assert commit.authored_datetime == datetime(2023, 1, 1, tzinfo=timezone.utc)
    assert commit.committer_name == "Test Committer"
    assert commit.committer_email == "committer@example.com"
    assert commit.committed_datetime == datetime(2023, 1, 2, tzinfo=timezone.utc)
    assert commit.message == "Test commit message\n\nMore details about the commit."
    assert commit.subject == "Test commit message"
    assert commit.parent_shas == []
    assert commit.file_changes is None


def test_commit_from_git_commit_with_parents(sample_git_commit: MagicMock):
    """Test the creation of a Commit object with parents."""
    # Create mock parent commit
    parent_commit = MagicMock()
    parent_commit.hexsha = "abcdef1234567890abcdef1234567890abcdef12"

    # Add parent to sample commit
    sample_git_commit.parents = [parent_commit]

    # Create a commit
    commit = Commit.from_git_commit(sample_git_commit, include_files=False)

    # Verify parent SHA is correct
    assert commit.parent_shas == ["abcdef1234567890abcdef1234567890abcdef12"]


def test_get_repo(temp_git_repo: Path):
    """Test getting a repository from a path."""
    # Get the repo from the temp directory
    repo = get_repo(temp_git_repo)

    # Verify it's a valid repo
    assert isinstance(repo, Repo)
    assert not repo.bare


def test_get_repo_nested_directory(temp_git_repo: Path):
    """Test getting a repository from a nested directory."""
    # Create a nested directory
    nested_dir = temp_git_repo / "nested" / "dir"
    nested_dir.mkdir(parents=True)

    # Get the repo from the nested directory
    repo = get_repo(nested_dir)

    # Verify it found the repo in a parent directory
    assert isinstance(repo, Repo)
    assert not repo.bare


def test_get_repo_not_found():
    """Test behavior when no git repository is found."""
    with (
        tempfile.TemporaryDirectory() as tmpdir,
        pytest.raises(ValueError, match="No Git repository found"),
    ):
        # Try to get a repo from a directory that's not a git repo
        get_repo(Path(tmpdir))


def test_get_commits(temp_git_repo: Path):
    """Test retrieving commits from a repository."""
    repo = get_repo(temp_git_repo)

    # Get all commits
    commits = list(get_commits(repo, None, include_diffs=False, max_count=None))

    # Should have at least 2 commits (initial + update)
    assert len(commits) >= 2

    # Check the most recent commit (first in the list)
    assert commits[0].subject == "Update test file"

    # Test with max_count
    limited_commits = list(get_commits(repo, None, include_diffs=False, max_count=1))
    assert len(limited_commits) == 1
