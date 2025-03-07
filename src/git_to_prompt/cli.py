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
            allow_leading_hyphen=True,
        ),
    ] = None,
    paths: Annotated[
        list[Path],
        Parameter(help="Paths to filter commits by", allow_leading_hyphen=True),
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
        # GitPython path handling works like git - paths should be relative to the repository root
        # When we're in a subdirectory, we need to convert relative paths to be relative to repo root
        repo_root = Path(repo.working_dir)
        current_dir = Path.cwd()

        # If we're in a subfolder of the repo, adjust the paths accordingly
        path_strs = []
        if paths:
            for p in paths:
                if p.name == "--":
                    continue
                path_obj = Path(p)
                # If it's already an absolute path within the repo, use it as is but make relative to repo root
                if path_obj.is_absolute() and repo_root in path_obj.parents:
                    path_strs.append(str(path_obj.relative_to(repo_root)))
                # For relative paths, we need to adjust based on our current location
                else:
                    # Determine if we're in a subfolder of the repo
                    if current_dir != repo_root and current_dir.is_relative_to(
                        repo_root
                    ):
                        # If we're in a subfolder and path is relative, we need to make it relative to the repo root
                        # First calculate the path relative to current dir (which may be a subfolder)
                        # Then calculate the current dir relative to repo root
                        # Finally combine them to get the proper path relative to repo root
                        subfolder_path = current_dir.relative_to(repo_root)
                        full_path = subfolder_path / path_obj
                        path_strs.append(str(full_path))
                    else:
                        # We're at repo root or outside the repo, use the path as is
                        path_strs.append(str(path_obj))

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
