import itertools
from collections.abc import Generator, Sequence
from datetime import datetime
from os import PathLike
from pathlib import Path

from attrs import frozen
from git import Commit as GitCommit
from git import Repo
from git.diff import Diff


@frozen
class FileChange:
    """Represents a change to a file in a commit."""

    path: str
    change_type: str  # A=Added, M=Modified, D=Deleted, R=Renamed
    insertions: int = 0
    deletions: int = 0
    content: str | None = None
    old_path: str | None = None  # Only populated for renames


@frozen
class Commit:
    """Represents a git commit with all relevant information."""

    hexsha: str
    short_sha: str
    author_name: str | None
    author_email: str | None
    authored_datetime: datetime
    committer_name: str | None
    committer_email: str | None
    committed_datetime: datetime
    message: str
    subject: str
    parent_shas: list[str]
    file_changes: list[FileChange] | None

    @classmethod
    def from_git_commit(
        cls, git_commit: GitCommit, include_files: bool = False
    ) -> "Commit":
        """Create a Commit object from a GitPython Commit object."""
        if include_files:
            if git_commit.parents:
                parent = git_commit.parents[0]
                diffs = parent.diff(git_commit, create_patch=True)
            else:
                # For the first commit
                diffs = git_commit.diff(GitCommit.NULL_TREE, create_patch=True)

            file_changes = _process_diffs(diffs, git_commit)
        else:
            file_changes = None

        commit = cls(
            hexsha=git_commit.hexsha,
            short_sha=git_commit.hexsha[:7],
            author_name=git_commit.author.name,
            author_email=git_commit.author.email,
            authored_datetime=git_commit.authored_datetime,
            committer_name=git_commit.committer.name,
            committer_email=git_commit.committer.email,
            committed_datetime=git_commit.committed_datetime,
            message=git_commit.message
            if isinstance(git_commit.message, str)
            else git_commit.message.decode(),
            subject=git_commit.summary
            if isinstance(git_commit.summary, str)
            else git_commit.summary.decode(),
            parent_shas=[p.hexsha for p in git_commit.parents],
            file_changes=file_changes,
        )

        return commit


def _process_diffs(diffs: list[Diff], commit: GitCommit) -> list[FileChange]:
    """Process diffs to extract file changes."""
    file_changes: list[FileChange] = []

    for diff in diffs:
        change_type = _get_change_type(diff)

        # Handle file paths correctly
        path = diff.b_path or diff.a_path
        assert path
        old_path = None

        if change_type == "R":  # Renamed
            old_path = diff.a_path

        # Get stats for the file
        insertions = 0
        deletions = 0

        if path and commit.stats.files.get(path):
            stats = commit.stats.files[path]
            insertions = stats.get("insertions", 0)
            deletions = stats.get("deletions", 0)

        # Get and format the diff content
        content = None

        if diff.diff and isinstance(diff.diff, bytes):
            diff_text = diff.diff.decode("utf-8", errors="replace")
            # Split into lines and add line numbers
            lines = diff_text.splitlines()
            # Create line-numbered output similar to files-to-prompt
            numbered_lines: list[str] = []
            line_num = 1
            for line in lines:
                if line.startswith("+"):
                    prefix = f"{line_num:4}  "
                    line_num += 1
                elif line.startswith("-"):
                    prefix = "     "  # No line number for deleted lines
                else:
                    prefix = f"{line_num:4}  "
                    line_num += 1
                numbered_lines.append(f"{prefix}{line}")
            content = "\n".join(numbered_lines)

        file_change = FileChange(
            path=path,
            change_type=change_type,
            insertions=insertions,
            deletions=deletions,
            content=content,
            old_path=old_path,
        )

        file_changes.append(file_change)

    return file_changes


def _get_change_type(diff: Diff) -> str:
    """Convert the GitPython change type to a simpler representation."""
    if diff.new_file:
        return "A"  # Added
    elif diff.deleted_file:
        return "D"  # Deleted
    elif diff.renamed:
        return "R"  # Renamed
    else:
        return "M"  # Modified


def get_commits(
    repo: Repo,
    revision_range: str | None,
    include_diffs: bool,
    max_count: int | None,
    paths: str | PathLike[str] | Sequence[str | PathLike[str]] | None = None,
) -> Generator[Commit]:
    """
    Get commits from the repository for the given revision range.

    Args:
        repo: The Git repository
        revision_range: Git revision range (e.g., "HEAD~5..HEAD")
        include_diffs: Whether to include diffs in the commit information
        max_count: Maximum number of commits to return
        paths: Path or list of paths to filter commits by (only commits affecting these paths will be shown)

    Yields:
        Commit objects for each commit in the range
    """
    # If paths is None, use empty string which means no path filtering
    path_arg = paths if paths is not None else ""
    commits = repo.iter_commits(rev=revision_range, paths=path_arg)

    for git_commit in itertools.islice(commits, max_count):
        yield Commit.from_git_commit(git_commit, include_diffs)


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
