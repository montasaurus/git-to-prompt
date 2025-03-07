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


def test_get_commits_with_path_filter(temp_git_repo: Path):
    """Test retrieving commits filtered by a specific path."""
    repo = get_repo(temp_git_repo)

    # Create a new file in a different directory
    other_dir = temp_git_repo / "other"
    other_dir.mkdir()
    other_file = other_dir / "other.txt"
    other_file.write_text("Other content")

    # Add and commit the new file
    repo.git.add("other/other.txt")
    repo.git.commit("-m", "Add other file")

    # Get commits filtered by test.txt path
    test_file_commits = list(
        get_commits(repo, None, include_diffs=False, max_count=None, paths="test.txt")
    )

    # Should have only commits that modified test.txt (initial + update)
    assert len(test_file_commits) == 2
    assert all(
        "test file" in commit.subject.lower() or "initial" in commit.subject.lower()
        for commit in test_file_commits
    )

    # Get commits filtered by other.txt path
    other_file_commits = list(
        get_commits(
            repo, None, include_diffs=False, max_count=None, paths="other/other.txt"
        )
    )

    # Should have only the commit that added other.txt
    assert len(other_file_commits) == 1
    assert other_file_commits[0].subject == "Add other file"

    # Test with Path objects (as the CLI now uses)
    path_obj_commits = list(
        get_commits(
            repo,
            None,
            include_diffs=False,
            max_count=None,
            paths=[Path("other/other.txt")],
        )
    )
    assert len(path_obj_commits) == 1
    assert path_obj_commits[0].subject == "Add other file"


def test_get_commits_with_multiple_paths(temp_git_repo: Path):
    """Test retrieving commits filtered by multiple paths."""
    repo = get_repo(temp_git_repo)

    # Create files in different directories
    dir1 = temp_git_repo / "dir1"
    dir1.mkdir()
    file1 = dir1 / "file1.txt"
    file1.write_text("File 1 content")

    dir2 = temp_git_repo / "dir2"
    dir2.mkdir()
    file2 = dir2 / "file2.txt"
    file2.write_text("File 2 content")

    # Add and commit both files together
    repo.git.add(all=True)
    repo.git.commit("-m", "Add multiple files")

    # Update file1.txt
    file1.write_text("Updated File 1 content")
    repo.git.add("dir1/file1.txt")
    repo.git.commit("-m", "Update file1")

    # Update file2.txt
    file2.write_text("Updated File 2 content")
    repo.git.add("dir2/file2.txt")
    repo.git.commit("-m", "Update file2")

    # Get commits filtered by both paths
    multi_path_commits = list(
        get_commits(
            repo,
            None,
            include_diffs=False,
            max_count=None,
            paths=["dir1/file1.txt", "dir2/file2.txt"],
        )
    )

    # Should include commits that modified either file1 or file2
    assert (
        len(multi_path_commits) == 3
    )  # Initial multi-file commit + update file1 + update file2
    assert any(
        "multiple files" in commit.subject.lower() for commit in multi_path_commits
    )
    assert any(
        "update file1" in commit.subject.lower() for commit in multi_path_commits
    )
    assert any(
        "update file2" in commit.subject.lower() for commit in multi_path_commits
    )

    # Get commits for just file1
    file1_commits = list(
        get_commits(
            repo, None, include_diffs=False, max_count=None, paths="dir1/file1.txt"
        )
    )
    assert len(file1_commits) == 2  # Initial multi-file commit + update file1
    assert not any("update file2" in commit.subject.lower() for commit in file1_commits)


def test_get_commits_with_revision_range_and_path(temp_git_repo: Path):
    """Test retrieving commits with both revision range and path filters."""
    repo = get_repo(temp_git_repo)

    # Create a series of commits with different files
    # First commit is already there from the fixture with test.txt

    # Add file1.txt
    file1 = temp_git_repo / "file1.txt"
    file1.write_text("File 1 content")
    repo.git.add("file1.txt")
    file1_commit = repo.git.commit("-m", "Add file1")

    # Add file2.txt
    file2 = temp_git_repo / "file2.txt"
    file2.write_text("File 2 content")
    repo.git.add("file2.txt")
    file2_commit = repo.git.commit("-m", "Add file2")

    # Update file1.txt
    file1.write_text("Updated File 1 content")
    repo.git.add("file1.txt")
    update_file1_commit = repo.git.commit("-m", "Update file1")

    # Update file2.txt
    file2.write_text("Updated File 2 content")
    repo.git.add("file2.txt")
    update_file2_commit = repo.git.commit("-m", "Update file2")

    # Get HEAD~3..HEAD commits (last 3 commits) for file1.txt
    # This should include "Add file1" and "Update file1" but not "Add file2" or "Update file2"
    revision_path_commits = list(
        get_commits(
            repo, "HEAD~4..HEAD", include_diffs=False, max_count=None, paths="file1.txt"
        )
    )

    # Should have only commits related to file1.txt in the revision range
    assert len(revision_path_commits) == 2
    commit_subjects = [commit.subject for commit in revision_path_commits]
    assert "Add file1" in commit_subjects
    assert "Update file1" in commit_subjects
    assert "Add file2" not in commit_subjects
    assert "Update file2" not in commit_subjects

    # Test with Path objects and multiple paths
    path_obj_commits = list(
        get_commits(
            repo,
            "HEAD~4..HEAD",
            include_diffs=False,
            max_count=None,
            paths=[Path("file1.txt"), Path("file2.txt")],
        )
    )

    # Should have all commits related to either file in the revision range
    assert len(path_obj_commits) == 4
    path_obj_subjects = [commit.subject for commit in path_obj_commits]
    assert "Add file1" in path_obj_subjects
    assert "Update file1" in path_obj_subjects
    assert "Add file2" in path_obj_subjects
    assert "Update file2" in path_obj_subjects


def test_get_commits_with_none_paths(temp_git_repo: Path):
    """Test that passing None for paths doesn't filter anything (backward compatibility)."""
    repo = get_repo(temp_git_repo)

    # Create two new files
    file1 = temp_git_repo / "file1.txt"
    file1.write_text("File 1 content")

    file2 = temp_git_repo / "file2.txt"
    file2.write_text("File 2 content")

    # Add and commit both files
    repo.git.add(all=True)
    repo.git.commit("-m", "Add new files")

    # Get commits with paths=None
    all_commits = list(
        get_commits(repo, None, include_diffs=False, max_count=None, paths=None)
    )

    # Get commits with no paths parameter
    default_commits = list(get_commits(repo, None, include_diffs=False, max_count=None))

    # Both should return the same number of commits (all commits)
    assert len(all_commits) == len(default_commits)

    # The commit for the new files should be included
    assert any("Add new files" in commit.subject for commit in all_commits)

    # Compare with filtered commits to verify difference
    file1_commits = list(
        get_commits(repo, None, include_diffs=False, max_count=None, paths="file1.txt")
    )
    assert len(file1_commits) < len(
        all_commits
    )  # Should have fewer commits when filtered


def test_get_commits_with_empty_paths_list(temp_git_repo: Path):
    """Test that passing an empty list for paths doesn't filter anything."""
    repo = get_repo(temp_git_repo)

    # Create two new files and commit them
    file1 = temp_git_repo / "file1.txt"
    file1.write_text("File 1 content")
    file2 = temp_git_repo / "file2.txt"
    file2.write_text("File 2 content")
    repo.git.add(all=True)
    repo.git.commit("-m", "Add new files")

    # Get commits with empty paths list
    empty_list_commits = list(
        get_commits(repo, None, include_diffs=False, max_count=None, paths=[])
    )

    # Get commits with no paths parameter
    default_commits = list(get_commits(repo, None, include_diffs=False, max_count=None))

    # Both should return the same number of commits (all commits)
    assert len(empty_list_commits) == len(default_commits)

    # The commit for the new files should be included
    assert any("Add new files" in commit.subject for commit in empty_list_commits)


# The -- delimiter is handled at the CLI level, not directly in get_commits
# so we're removing this test as it doesn't make sense at this level
