# Heavily inspired by https://github.com/yamadashy/repomix (i.e. Claude reimplemented it in Python)

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import fnmatch
import os
from pathlib import Path
from typing import Any

from git import Repo


class RepomixPython:
    """A Python implementation of Repomix for packing repositories into AI-friendly formats using GitPython."""

    def __init__(self, repo: Repo, ignore_paths: list[str] | None = None):
        """Initialize the Repomix Python implementation.

        Args:
            root_dir: Root directory of the repository to process
            ignore_paths: List of additional paths to ignore (glob patterns)
        """
        self.repo = repo
        self.root_dir = Path(repo.working_dir)
        self.ignore_paths = ignore_paths or []

        # Default ignore patterns (from defaultIgnore.ts)
        self.default_ignore_patterns = [
            ".git/**",
            ".hg/**",
            ".hgignore",
            ".svn/**",
            "**/node_modules/**",
            "**/bower_components/**",
            "**/jspm_packages/**",
            "vendor/**",
            "**/.bundle/**",
            "**/.gradle/**",
            "target/**",
            "logs/**",
            "**/*.log",
            "**/npm-debug.log*",
            "**/yarn-debug.log*",
            "**/yarn-error.log*",
            "pids/**",
            "*.pid",
            "*.seed",
            "*.pid.lock",
            "lib-cov/**",
            "coverage/**",
            ".nyc_output/**",
            ".grunt/**",
            ".lock-wscript",
            "build/Release/**",
            "typings/**",
            "**/.npm/**",
            ".eslintcache",
            ".rollup.cache/**",
            ".webpack.cache/**",
            ".parcel-cache/**",
            ".sass-cache/**",
            "*.cache",
            ".node_repl_history",
            "*.tgz",
            "**/.yarn/**",
            "**/.yarn-integrity",
            ".env",
            ".next/**",
            ".nuxt/**",
            ".vuepress/dist/**",
            ".serverless/**",
            ".fusebox/**",
            ".dynamodb/**",
            "dist/**",
            "**/.DS_Store",
            "**/Thumbs.db",
            ".idea/**",
            ".vscode/**",
            "**/*.swp",
            "**/*.swo",
            "**/*.swn",
            "**/*.bak",
            "build/**",
            "out/**",
            "tmp/**",
            "temp/**",
            "**/repomix-output.*",
            "**/repopack-output.*",
            "**/package-lock.json",
            "**/yarn-error.log",
            "**/yarn.lock",
            "**/pnpm-lock.yaml",
            "**/bun.lockb",
            "**/__pycache__/**",
            "**/*.py[cod]",
            "**/venv/**",
            "**/.venv/**",
            "**/.pytest_cache/**",
            "**/.mypy_cache/**",
            "**/.ipynb_checkpoints/**",
            "**/Pipfile.lock",
            "**/poetry.lock",
            "**/Cargo.lock",
            "**/Cargo.toml.orig",
            "**/target/**",
            "**/*.rs.bk",
            "**/composer.lock",
            "**/Gemfile.lock",
            "**/go.sum",
            "**/mix.lock",
            "**/stack.yaml.lock",
            "**/cabal.project.freeze",
        ]

        # Also use .repomixignore if available
        self.repomixignore_patterns = self._parse_ignore_file(".repomixignore")

    def _parse_ignore_file(self, ignore_file: str) -> list[str]:
        """Parse ignore patterns from a file like .gitignore or .repomixignore.

        Args:
            ignore_file: The name of the ignore file to parse

        Returns:
            List of ignore patterns from the file
        """
        patterns: list[str] = []
        ignore_path = self.root_dir / ignore_file

        if ignore_path.exists():
            with Path.open(ignore_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.append(line)

        return patterns

    def _should_ignore(self, file_path: str) -> bool:
        """Check if a file should be ignored based on ignore patterns.

        Args:
            file_path: Path to the file to check

        Returns:
            True if the file should be ignored, False otherwise
        """
        # Make path relative to root_dir
        rel_path = os.path.relpath(file_path, self.root_dir)

        # First, check default patterns and repomixignore patterns
        all_patterns = (
            self.default_ignore_patterns
            + self.repomixignore_patterns
            + self.ignore_paths
        )

        # Check if the file matches any of these patterns
        for pattern in all_patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                return True

        # Then check if git would ignore this file
        if os.path.exists(file_path) and not os.path.isdir(file_path):
            try:
                # Check if file is ignored by git
                return self.repo.git.check_ignore(rel_path) != ""
            except:
                # If any error occurs during the git check, fall back to default behavior
                pass

        # For directories, we check if they would be ignored by git
        if os.path.isdir(file_path):
            try:
                return self.repo.git.check_ignore(rel_path) != ""
            except:
                # If any error occurs during the git check, fall back to default behavior
                pass

        return False

    def _collect_files(self) -> list[str]:
        """Collect all files in the repository that don't match ignore patterns.

        Returns:
            List of file paths
        """
        all_files: list[str] = []

        for root, dirs, files in os.walk(self.root_dir):
            # Filter out directories that match ignore patterns
            dirs[:] = [
                d for d in dirs if not self._should_ignore(os.path.join(root, d))
            ]

            for file in files:
                file_path = os.path.join(root, file)
                if not self._should_ignore(file_path):
                    all_files.append(file_path)

        return sorted(all_files)

    def _generate_directory_structure(self, file_paths: list[str]) -> str:
        """Generate a directory structure tree from the list of file paths.

        Args:
            file_paths: List of file paths

        Returns:
            Directory structure as a string
        """
        # Make paths relative to root
        rel_paths = [os.path.relpath(path, self.root_dir) for path in file_paths]

        # Create a dictionary to represent the directory structure
        dir_structure: dict[str, Any] = {}

        for path in rel_paths:
            path_parts = path.split(os.sep)
            current = dir_structure

            # Build tree structure
            for part in path_parts:
                if part not in current:
                    current[part] = {}
                current = current[part]

        # Convert the structure to a string
        result: list[str] = []

        def _build_tree(node: dict[str, Any], prefix: str = "") -> None:
            keys = sorted(node.keys())
            for i, key in enumerate(keys):
                is_last_item = i == len(keys) - 1
                result.append(f"{prefix}{'└── ' if is_last_item else '├── '}{key}")

                if node[key]:  # If has children
                    next_prefix = prefix + ("    " if is_last_item else "│   ")
                    _build_tree(node[key], next_prefix)

        _build_tree(dir_structure)
        return "\n".join(result)

    def _is_binary_file(self, file_path: str) -> bool:
        """Check if a file is binary.

        Args:
            file_path: Path to the file

        Returns:
            True if the file is binary, False otherwise
        """
        # Check file extension first (optimistic)
        binary_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".ico",
            ".webp",
            ".mp3",
            ".wav",
            ".ogg",
            ".flac",
            ".mp4",
            ".avi",
            ".mov",
            ".wmv",
            ".zip",
            ".tar",
            ".gz",
            ".bz2",
            ".7z",
            ".rar",
            ".exe",
            ".dll",
            ".so",
            ".dylib",
            ".pyc",
            ".pyd",
            ".pyo",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
        }

        if os.path.splitext(file_path)[1].lower() in binary_extensions:
            return True

        # If not determined by extension, check content
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(1024)
                return b"\0" in chunk  # Simple heuristic for binary files
        except Exception:
            # If we can't read the file, consider it binary to be safe
            return True

    def pack(self) -> str:
        """Pack the repository into a single file and return the result.

        Returns:
            The packed repository as a string
        """
        # Collect files
        file_paths = self._collect_files()

        # Generate directory structure
        dir_structure = self._generate_directory_structure(file_paths)

        # Build the output
        output: list[str] = []

        # Add the header
        output.append(
            "This file is a merged representation of a subset of the codebase, containing files not matching ignore patterns, combined into a single document by Repomix."
        )
        output.append("")

        # Add file summary
        output.append(
            "================================================================"
        )
        output.append("File Summary")
        output.append(
            "================================================================"
        )
        output.append("")
        output.append("Purpose:")
        output.append("--------")
        output.append(
            "This file contains a packed representation of the entire repository's contents."
        )
        output.append(
            "It is designed to be easily consumable by AI systems for analysis, code review,"
        )
        output.append("or other automated processes.")
        output.append("")
        output.append("File Format:")
        output.append("------------")
        output.append("The content is organized as follows:")
        output.append("1. This summary section")
        output.append("2. Repository information")
        output.append("3. Directory structure")
        output.append("4. Multiple file entries, each consisting of:")
        output.append("  a. A separator line (================)")
        output.append("  b. The file path (File: path/to/file)")
        output.append("  c. Another separator line")
        output.append("  d. The full contents of the file")
        output.append("  e. A blank line")
        output.append("")
        output.append("Usage Guidelines:")
        output.append("-----------------")
        output.append(
            "- This file should be treated as read-only. Any changes should be made to the"
        )
        output.append("  original repository files, not this packed version.")
        output.append("- When processing this file, use the file path to distinguish")
        output.append("  between different files in the repository.")
        output.append(
            "- Be aware that this file may contain sensitive information. Handle it with"
        )
        output.append(
            "  the same level of security as you would the original repository."
        )
        output.append("")
        output.append("Notes:")
        output.append("------")
        output.append(
            "- Some files may have been excluded based on .gitignore rules and Repomix's configuration"
        )
        output.append(
            "- Binary files are not included in this packed representation. Please refer to the Repository Structure section for a complete list of file paths, including binary files"
        )
        if self.ignore_paths:
            output.append(
                f"- Files matching these patterns are excluded: {', '.join(self.ignore_paths)}"
            )
        output.append("- Files matching patterns in .gitignore are excluded")
        output.append("- Files matching default ignore patterns are excluded")
        output.append("")
        output.append("Additional Info:")
        output.append("----------------")
        output.append("")

        # Add directory structure
        output.append(
            "================================================================"
        )
        output.append("Directory Structure")
        output.append(
            "================================================================"
        )
        output.append(dir_structure)
        output.append("")

        # Add files
        output.append(
            "================================================================"
        )
        output.append("Files")
        output.append(
            "================================================================"
        )
        output.append("")

        for file_path in file_paths:
            if not self._is_binary_file(file_path):
                rel_path = os.path.relpath(file_path, self.root_dir)

                output.append("================")
                output.append(f"File: {rel_path}")
                output.append("================")

                try:
                    with open(file_path, encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    output.append(content)
                except Exception as e:
                    output.append(f"Error reading file: {e!s}")

                output.append("")

        return "\n".join(output)
