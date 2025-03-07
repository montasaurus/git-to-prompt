import sys
from pathlib import Path
from typing import Annotated

from cyclopts import App, Parameter, validators
from git import GitCommandError

from git_to_prompt.formatter import write_commits_as_cxml
from git_to_prompt.log import get_commits, get_repo

app = App(
    name="git-to-prompt",
    end_of_options_delimiter="",  # Allow -- delimiter syntax
)


def revision_range_validator(type_, value: str):
    """Validate revision range, allowing bare -- for path-only usage"""
    if value == "--":
        return
    # Add more validation if needed
    return


@app.command
def log(
    revision_range: Annotated[
        str | None, 
        Parameter(
            help="Revision range (e.g., 'HEAD~5..HEAD')",
            validator=revision_range_validator, 
            allow_leading_hyphen=True
        )
    ] = None,
    paths: Annotated[
        list[Path], 
        Parameter(
            help="Paths to filter commits by",
            allow_leading_hyphen=True
        )
    ] = [],
    /,
    include_patch: Annotated[
        bool,
        Parameter(
            help="Include commit diffs in the output",
            name=["--patch", "-p", "-u"],
            negative=["--no-patch"],
        ),
    ] = False,
    max_count: Annotated[
        int | None,
        Parameter(help="Maximum number of commits to show", name=["--max-count", "-n"]),
    ] = None,
    output: Annotated[
        Path | None,
        Parameter(
            help="Output file (defaults to stdout)",
            validator=validators.Path(file_okay=True, dir_okay=False),
            name=["--output", "-o"],
        ),
    ] = None,
    repo_path: Annotated[
        Path,
        Parameter(
            help="Path to the Git repository (defaults to current directory)",
            validator=validators.Path(exists=True, file_okay=False),
        ),
    ] = Path.cwd(),
) -> None:
    """
    Generate a formatted log of git commits suitable for LLM prompts.

    Usage: git-to-prompt log [<options>] [<revision-range>] [[--] <path>...]

    Outputs in Claude XML format, which is designed to be
    easily parseable by large language models while maintaining the
    structured nature of git commit data.

    Examples:
        # Get the last 5 commits with diffs attached
        git-to-prompt log -n 5 --patch

        # Get commits between two revisions
        git-to-prompt log "v1.0..v2.0"

        # Output to a file
        git-to-prompt log -o log.xml

        # Filter commits by path (using -- syntax)
        git-to-prompt log -- path/to/file.py

        # Filter commits by multiple paths (using -- syntax)
        git-to-prompt log -- path/to/file.py another/path

        # Combine with revision range and paths
        git-to-prompt log HEAD~10..HEAD path/to/file.py

        # Explicitly use -- to separate paths
        git-to-prompt log -- path/to/file.py
    """
    try:
        # Find the Git repository
        repo = get_repo(repo_path)

        # If revision_range is the bare "--", set it to None
        if revision_range == "--":
            revision_range = None

        # Convert path objects to strings for GitPython
        path_strs = [str(p) for p in paths] if paths else []

        # Get the commits
        commits = get_commits(repo, revision_range, include_patch, max_count, path_strs)

        # Write the commits to the output
        if output:
            with Path.open(output, "w", encoding="utf-8") as f:
                write_commits_as_cxml(commits, f, include_patch)
        else:
            write_commits_as_cxml(commits, sys.stdout, include_patch)
    except GitCommandError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
