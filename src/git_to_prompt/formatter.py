import html
from collections.abc import Generator
from typing import TextIO

from .log import Commit, FileChange


def format_commit_as_cxml(
    commit: Commit, index: int, include_diffs: bool = False
) -> str:
    """
    Format a commit as CXML.

    Args:
        commit: The commit to format
        index: The index of the commit in the sequence
        include_diffs: Whether to include diffs

    Returns:
        The commit formatted as CXML
    """
    # Format datetime in ISO 8601 format
    authored_date = commit.authored_datetime.isoformat()
    committed_date = commit.committed_datetime.isoformat()

    # Convert the message to HTML-safe format
    message = html.escape(commit.message)
    subject = html.escape(commit.subject)

    cxml = f'<commit index="{index}">\n'
    cxml += f"<sha>{commit.hexsha}</sha>\n"
    cxml += f"<short_sha>{commit.short_sha}</short_sha>\n"
    cxml += f"<author>{html.escape(commit.author_name or '')} <{commit.author_email}></author>\n"
    cxml += f"<authored_date>{authored_date}</authored_date>\n"
    cxml += f"<committer>{html.escape(commit.committer_name or '')} <{commit.committer_email}></committer>\n"
    cxml += f"<committed_date>{committed_date}</committed_date>\n"
    cxml += f"<subject>{subject}</subject>\n"

    if commit.parent_shas:
        cxml += "<parents>\n"
        for parent in commit.parent_shas:
            cxml += f"<parent>{parent}</parent>\n"
        cxml += "</parents>\n"

    if include_diffs and commit.file_changes:
        cxml += "<patch>\n"
        for file_change in commit.file_changes:
            cxml += format_file_change(file_change)
        cxml += "</patch>\n"

    cxml += "<message>\n"
    cxml += f"{message.strip()}\n"
    cxml += "</message>\n"
    cxml += "</commit>\n"

    return cxml


def format_file_change(file_change: FileChange) -> str:
    """
    Format a file change as CXML.

    Args:
        file_change: The file change to format

    Returns:
        The file change formatted as CXML
    """
    path = html.escape(file_change.path)

    cxml = f'<file path="{path}" change_type="{file_change.change_type}"'

    if file_change.insertions or file_change.deletions:
        cxml += f' insertions="{file_change.insertions}" deletions="{file_change.deletions}"'

    if file_change.old_path:
        cxml += f' old_path="{html.escape(file_change.old_path)}"'

    if file_change.content:
        cxml += ">\n"
        cxml += "<diff>\n"
        # Add the diff content with proper indentation and escaping
        content = html.escape(file_change.content)
        # Split by lines to maintain proper indentation
        for line in content.splitlines():
            cxml += f"{line}\n"
        cxml += "</diff>\n"
        cxml += "</file>\n"
    else:
        cxml += " />\n"

    return cxml


def write_commits_as_cxml(
    commits: Generator[Commit], output: TextIO, include_files: bool = False
) -> None:
    """
    Write commits as CXML to the given output stream.

    Args:
        commits: Generator of commits to format
        output: Output stream to write to
        include_files: Whether to include file changes
    """
    output.write("<commits>\n")

    for i, commit in enumerate(commits, 1):
        output.write(format_commit_as_cxml(commit, i, include_files))

    output.write("</commits>\n")
