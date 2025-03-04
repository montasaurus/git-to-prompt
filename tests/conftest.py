import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from git import Repo


@pytest.fixture
def temp_git_repo() -> Generator[Path]:
    """Create a temporary git repository for testing.

    This fixture creates a new Git repository with two commits:
    1. Initial commit with "test.txt" file
    2. Update to "test.txt" file

    Returns:
        Path to the temporary repository
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a git repo
        repo_path = Path(tmpdir)
        repo = Repo.init(repo_path)

        # Configure git user
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test User")
        config_writer.set_value("user", "email", "test@example.com")
        config_writer.release()

        # Create a test file
        test_file = repo_path / "test.txt"
        test_file.write_text("Initial content")

        # Add and commit the file
        repo.git.add("test.txt")
        repo.git.commit("-m", "Initial commit")

        # Make a change
        test_file.write_text("Updated content")
        repo.git.add("test.txt")
        repo.git.commit("-m", "Update test file")

        yield repo_path
