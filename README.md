# git-to-prompt

A command-line tool for turning Git repository information into context for LLM prompts.

Inspired by [files-to-prompt](https://github.com/simonw/files-to-prompt), this tool focuses on git history instead of files, making it easy to include repository history in your prompts to LLMs like Claude and GPT.

This tool was largely written using Claude 3.7 Sonnet, and is very lightly tested.

## Installation

Install directly from the repository using [uv](https://github.com/astral-sh/uv):

```bash
uv tool install git-to-prompt
```

## Usage

### Basic usage

Get all the commits from the current repository:

```bash
git-to-prompt log
```

Get all the diffs in this branch back off `master`:

```bash
git-to-prompt log master..HEAD --patch
```

This outputs Git commits in a Claude XML format that's well-suited for LLM prompting.

### Options

```
Usage: git-to-prompt log [<options>] [<revision-range>] [[--] <path>...]

  Generate a formatted log of git commits suitable for LLM prompts.

  Outputs in Claude XML format, which is designed to be easily parseable by large
  language models while maintaining the structured nature of git commit data.

Arguments:
  <revision-range>   Revision range (e.g., 'HEAD~5..HEAD')
  <path>...          Paths to filter commits by (only commits affecting these paths will be shown)

Options:
  -n, --max-count INTEGER       Maximum number of commits to show
  -p, -u, --patch / --no-patch  Include commit diffs in the output (default: false)
  -o, --output PATH             Output file (defaults to stdout)
  --repo-path DIRECTORY         Path to the Git repository (defaults to current directory)
  --help                        Show this message and exit.

Examples:
  # Get the last 5 commits with diffs attached
  git-to-prompt log -n 5 --patch

  # Get commits between two revisions
  git-to-prompt log "v1.0..v2.0"

  # Output to a file
  git-to-prompt log -o log.xml

  # Filter commits by path (using -- syntax, just like git)
  git-to-prompt log -- path/to/file.py

  # Filter commits by multiple paths
  git-to-prompt log -- path/to/file.py another/path

  # Combine with revision range and paths
  git-to-prompt log HEAD~10..HEAD path/to/file.py
```

## Output Format

The output is formatted as XML, which works particularly well with Claude's XML parsing capabilities (indents included for readability):

```xml
<commits>
<commit index="1">
  <sha>60122e857891a3dab3a93846c2e6447c2af75adb</sha>
  <short_sha>60122e8</short_sha>
  <author>Bob Bobkins <bob@example.com></author>
  <authored_date>2025-03-04T13:05:29-05:00</authored_date>
  <committer>Bob Bobkins <bob@example.com></committer>
  <committed_date>2025-03-04T13:05:29-05:00</committed_date>
  <subject>more hype</subject>
  <parents>
    <parent>c9560686a132206738cd1ea4952039a05f964b60</parent>
  </parents>
  <patch>
    <file path="README.md" change_type="M" insertions="1" deletions="1">
      <diff>
           1  @@ -1 +1 @@
             -My New Project
           2  +My AWESOME Project
      </diff>
    </file>
  </patch>
  <message>
    more hype
  </message>
</commit>
<commit index="2">
  <sha>c9560686a132206738cd1ea4952039a05f964b60</sha>
  <short_sha>c956068</short_sha>
  <author>Bob Bobkins <bob@example.com></author>
  <authored_date>2025-03-04T13:05:03-05:00</authored_date>
  <committer>Bob Bobkins <bob@example.com></committer>
  <committed_date>2025-03-04T13:05:03-05:00</committed_date>
  <subject>init repo</subject>
  <patch>
    <file path="README.md" change_type="A" insertions="1" deletions="0">
      <diff>
           1  @@ -0,0 +1 @@
           2  +My New Project
      </diff>
    </file>
  </patch>
  <message>
    init repo
  </message>
</commit>
</commits>
```

## Development

### Build

To build the project:

```bash
just build
```
