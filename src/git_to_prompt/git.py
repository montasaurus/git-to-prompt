from pathlib import Path

from git import Repo


def get_repo(path: Path) -> Repo:
    """
    Get a Git repository at the given path.
    If the path is not a Git repository, this function will walk up the directory
    tree until it finds a Git repository or raises an exception.

    Args:
        path: The path to start searching from

    Returns:
        The Git repository

    Raises:
        ValueError: If no Git repository is found
    """
    current_path = path.absolute()

    while current_path != current_path.parent:
        try:
            return Repo(current_path)
        except Exception:  # noqa: PERF203
            current_path = current_path.parent

    raise ValueError(f"No Git repository found at or above {path}")
