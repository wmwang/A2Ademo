from __future__ import annotations

import os
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx


EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".next",
    ".idea",
    ".vscode",
    "coverage",
}

TEXT_SUFFIXES = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".cs",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".swift",
    ".kt",
    ".kts",
    ".scala",
    ".sql",
    ".md",
    ".txt",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".xml",
    ".sh",
    ".env",
}

MANIFEST_NAMES = {
    "README.md",
    "README.rst",
    "README.txt",
    "pyproject.toml",
    "package.json",
    "package-lock.json",
    "requirements.txt",
    "Pipfile",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    ".env.example",
}

CODE_SUFFIXES = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".cs",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".swift",
    ".kt",
    ".kts",
    ".scala",
}


@dataclass(frozen=True)
class FileSnippet:
    path: str
    excerpt: str


@dataclass(frozen=True)
class RepositoryBrief:
    source_type: str
    source_label: str
    summary: str
    top_languages: tuple[str, ...]
    tree_preview: tuple[str, ...]
    snippets: tuple[FileSnippet, ...]
    notes: tuple[str, ...] = ()

    def prompt_text(self) -> str:
        languages = ", ".join(self.top_languages) if self.top_languages else "unknown"
        tree = "\n".join(f"- {item}" for item in self.tree_preview) or "- (no files)"
        snippet_blocks = []
        for snippet in self.snippets:
            snippet_blocks.append(f"## {snippet.path}\n{snippet.excerpt}")
        notes = "\n".join(f"- {item}" for item in self.notes)
        sections = [
            f"Repository source: {self.source_label}",
            f"Repository summary: {self.summary}",
            f"Top languages: {languages}",
            "Repository tree preview:",
            tree,
            "Representative file excerpts:",
            "\n\n".join(snippet_blocks) if snippet_blocks else "No excerpt available.",
        ]
        if notes:
            sections.extend(["Notes:", notes])
        return "\n\n".join(sections)

    def console_summary(self) -> str:
        languages = ", ".join(self.top_languages[:4]) if self.top_languages else "unknown"
        return f"{self.source_label} | {self.summary} | languages: {languages}"


def load_repository_brief(
    target: str,
    *,
    max_files: int = 8,
    max_chars_per_file: int = 1600,
    max_tree_entries: int = 40,
) -> RepositoryBrief:
    if _is_github_url(target):
        return _load_github_repository_brief(
            target,
            max_files=max_files,
            max_chars_per_file=max_chars_per_file,
            max_tree_entries=max_tree_entries,
        )
    return _load_local_repository_brief(
        target,
        max_files=max_files,
        max_chars_per_file=max_chars_per_file,
        max_tree_entries=max_tree_entries,
    )


def _load_local_repository_brief(
    target: str,
    *,
    max_files: int,
    max_chars_per_file: int,
    max_tree_entries: int,
) -> RepositoryBrief:
    root = Path(target).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Path does not exist: {root}")

    if root.is_file():
        files = [root]
        tree_preview = (root.name,)
        source_label = f"local file: {root}"
    else:
        files = list(_iter_local_text_files(root))
        tree_preview = tuple(
            str(path.relative_to(root))
            for path in sorted(files, key=lambda item: str(item.relative_to(root)))[:max_tree_entries]
        )
        source_label = f"local repo: {root}"

    selected = _select_paths(
        files,
        root=root.parent if root.is_file() else root,
        max_files=max_files,
    )
    snippets = tuple(
        FileSnippet(
            path=str(path.relative_to(root.parent if root.is_file() else root)),
            excerpt=_read_text_excerpt(path, max_chars_per_file),
        )
        for path in selected
    )

    languages = _summarize_languages(
        path.relative_to(root.parent if root.is_file() else root).suffix.lower()
        for path in files
    )
    summary = (
        f"{len(files)} text files scanned from {root.name or str(root)}"
        if root.is_dir()
        else f"single file review of {root.name}"
    )
    return RepositoryBrief(
        source_type="local",
        source_label=source_label,
        summary=summary,
        top_languages=languages,
        tree_preview=tree_preview,
        snippets=snippets,
    )


def _load_github_repository_brief(
    target: str,
    *,
    max_files: int,
    max_chars_per_file: int,
    max_tree_entries: int,
) -> RepositoryBrief:
    repo_target = _parse_github_target(target)
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "a2a-scrum-meeting-demo",
    }
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with httpx.Client(timeout=20.0, headers=headers, follow_redirects=True) as client:
        repo_resp = client.get(f"https://api.github.com/repos/{repo_target.owner}/{repo_target.repo}")
        repo_resp.raise_for_status()
        repo_data = repo_resp.json()

        ref = repo_target.ref or repo_data["default_branch"]
        branch_resp = client.get(
            f"https://api.github.com/repos/{repo_target.owner}/{repo_target.repo}/branches/{ref}"
        )
        branch_resp.raise_for_status()
        branch_data = branch_resp.json()
        tree_sha = branch_data["commit"]["commit"]["tree"]["sha"]

        tree_resp = client.get(
            f"https://api.github.com/repos/{repo_target.owner}/{repo_target.repo}/git/trees/{tree_sha}",
            params={"recursive": 1},
        )
        tree_resp.raise_for_status()
        tree_data = tree_resp.json()

        file_paths = [
            entry["path"]
            for entry in tree_data.get("tree", [])
            if entry.get("type") == "blob" and _github_path_is_allowed(entry["path"], repo_target.subpath)
        ]
        selected_paths = _select_remote_paths(file_paths, max_files=max_files)
        snippets = []
        for path in selected_paths:
            raw_url = (
                f"https://raw.githubusercontent.com/{repo_target.owner}/"
                f"{repo_target.repo}/{ref}/{path}"
            )
            raw_resp = client.get(raw_url)
            raw_resp.raise_for_status()
            text = _truncate_text(raw_resp.text, max_chars_per_file)
            snippets.append(FileSnippet(path=path, excerpt=text))

    languages = _summarize_languages(Path(path).suffix.lower() for path in file_paths)
    tree_preview = tuple(sorted(file_paths)[:max_tree_entries])
    summary = (
        f"GitHub repository {repo_target.owner}/{repo_target.repo} at ref {ref}"
        + (f" under {repo_target.subpath}" if repo_target.subpath else "")
    )
    notes = ("Runtime access to GitHub may hit rate limits without GITHUB_TOKEN.",)
    return RepositoryBrief(
        source_type="github",
        source_label=f"github: {target}",
        summary=summary,
        top_languages=languages,
        tree_preview=tree_preview,
        snippets=tuple(snippets),
        notes=notes,
    )


@dataclass(frozen=True)
class GithubTarget:
    owner: str
    repo: str
    ref: str | None
    subpath: str | None


def _parse_github_target(target: str) -> GithubTarget:
    parsed = urlparse(target)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise ValueError(f"Unsupported GitHub URL: {target}")

    owner = parts[0]
    repo = parts[1].removesuffix(".git")
    ref = None
    subpath = None

    if len(parts) >= 4 and parts[2] in {"tree", "blob"}:
        ref = parts[3]
        if len(parts) > 4:
            subpath = "/".join(parts[4:])

    return GithubTarget(owner=owner, repo=repo, ref=ref, subpath=subpath)


def _iter_local_text_files(root: Path):
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        rel_parts = path.relative_to(root).parts
        if any(part in EXCLUDED_DIRS for part in rel_parts):
            continue
        if not _is_probably_text(path):
            continue
        yield path


def _is_probably_text(path: Path) -> bool:
    if path.name in MANIFEST_NAMES or path.suffix.lower() in TEXT_SUFFIXES:
        return True
    try:
        sample = path.read_bytes()[:512]
    except OSError:
        return False
    return b"\x00" not in sample


def _select_paths(paths: list[Path], *, root: Path, max_files: int) -> list[Path]:
    sorted_paths = sorted(paths, key=lambda path: _path_sort_key(path.relative_to(root)))
    return sorted_paths[:max_files]


def _select_remote_paths(paths: list[str], *, max_files: int) -> list[str]:
    return sorted(paths, key=lambda item: _path_sort_key(Path(item)))[:max_files]


def _path_sort_key(path: Path) -> tuple[int, int, int, str]:
    name = path.name
    suffix = path.suffix.lower()
    priority = 100
    if name in MANIFEST_NAMES:
        priority -= 60
    if suffix in CODE_SUFFIXES:
        priority -= 20
    if "test" in path.parts or name.startswith("test_"):
        priority += 5
    return (priority, len(path.parts), len(name), str(path))


def _read_text_excerpt(path: Path, max_chars: int) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        return f"[Unable to read file: {exc}]"
    return _truncate_text(text, max_chars)


def _truncate_text(text: str, max_chars: int) -> str:
    cleaned = text.strip()
    if len(cleaned) <= max_chars:
        return cleaned
    shortened = cleaned[:max_chars].rstrip()
    return f"{shortened}\n... [truncated]"


def _summarize_languages(suffixes) -> tuple[str, ...]:
    counter = Counter()
    for suffix in suffixes:
        if not suffix:
            counter["(no extension)"] += 1
        else:
            counter[suffix] += 1
    return tuple(f"{suffix} x{count}" for suffix, count in counter.most_common(5))


def _github_path_is_allowed(path: str, subpath: str | None) -> bool:
    path_obj = Path(path)
    if any(part in EXCLUDED_DIRS for part in path_obj.parts):
        return False
    if path_obj.name not in MANIFEST_NAMES and path_obj.suffix.lower() not in TEXT_SUFFIXES:
        return False
    if subpath and not path.startswith(subpath.rstrip("/") + "/") and path != subpath.rstrip("/"):
        return False
    return True


def _is_github_url(target: str) -> bool:
    parsed = urlparse(target)
    return parsed.scheme in {"http", "https"} and parsed.netloc.lower() == "github.com"
