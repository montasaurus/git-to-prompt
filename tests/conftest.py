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
        repo_path = Path(tmpdir)
        repo = Repo.init(repo_path)

        # Git identity (redundant with config, but keeps commits deterministic if config changes)
        git_env = {
            "GIT_AUTHOR_NAME": "Test User",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test User",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        }

        # Configure git user (for commands that rely on config)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", git_env["GIT_AUTHOR_NAME"])
        config_writer.set_value("user", "email", git_env["GIT_AUTHOR_EMAIL"])
        config_writer.release()

        commit_times = [
            "2024-01-01T12:00:00+00:00",
            "2024-01-01T12:05:00+00:00",
            "2024-01-01T12:10:00+00:00",
        ]

        def commit(paths: str | list[str], message: str, date: str) -> None:
            with repo.git.custom_environment(
                **git_env,
                GIT_AUTHOR_DATE=date,
                GIT_COMMITTER_DATE=date,
            ):
                repo.git.add(paths)
                repo.git.commit("-m", message)

        # Create a test file
        test_file = repo_path / "test.txt"
        test_file.write_text("Initial content")

        commit("test.txt", "Initial commit", commit_times[0])

        # Make a change
        test_file.write_text("Updated content")
        commit("test.txt", "Update test file", commit_times[1])

        second_file = repo_path / "second.txt"
        second_file.write_text("Second file content")
        commit("second.txt", "Add second file", commit_times[2])

        yield repo_path
