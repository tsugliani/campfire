"""Shared fixtures for Campfire CLI tests."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml


@pytest.fixture()
def tmp_repo(tmp_path: Path) -> Path:
    """Create a minimal Hugo repo structure with hugo.toml and content dir."""
    (tmp_path / "hugo.toml").write_text("[params]\ntitle = 'Campfire'\n")
    content = tmp_path / "content"
    content.mkdir()
    static = tmp_path / "static" / "screenshots"
    static.mkdir(parents=True)
    return tmp_path


@pytest.fixture()
def sample_link_md(tmp_repo: Path) -> Path:
    """Create a sample link markdown file inside a week directory."""
    week_dir = tmp_repo / "content" / "2026" / "w12"
    week_dir.mkdir(parents=True)

    # Week _index.md
    index = week_dir / "_index.md"
    fm = {"title": "Week 12", "date": "2026-03-16", "year": 2026, "week": 12}
    yaml_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    index.write_text(f"---\n{yaml_str}---\n")

    # A link file
    link = week_dir / "example-post.md"
    fm = {
        "title": "Example Post",
        "url_link": "https://example.com/post",
        "tags": ["python", "testing"],
        "description": "An example post for testing.",
        "date": "2026-03-18",
        "year": 2026,
        "week": 12,
        "comments": [],
    }
    yaml_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    link.write_text(f"---\n{yaml_str}---\n")
    return link


@pytest.fixture()
def second_link_md(tmp_repo: Path) -> Path:
    """Create a second link in week 12 with different tags."""
    week_dir = tmp_repo / "content" / "2026" / "w12"
    week_dir.mkdir(parents=True, exist_ok=True)

    link = week_dir / "another-article.md"
    fm = {
        "title": "Another Article",
        "url_link": "https://example.com/another",
        "tags": ["kubernetes", "devops"],
        "description": "Another article.",
        "date": "2026-03-19",
        "year": 2026,
        "week": 12,
        "comments": [],
    }
    yaml_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    link.write_text(f"---\n{yaml_str}---\n")
    return link


SAMPLE_HTML = textwrap.dedent("""\
    <html>
    <head>
        <title>Test Page Title</title>
        <meta property="og:title" content="OG Title Here" />
        <meta property="og:description" content="OG description text." />
        <meta property="og:image" content="https://example.com/image.png" />
        <meta name="description" content="Meta description." />
        <meta name="keywords" content="python, testing, automation" />
    </head>
    <body><h1>Hello World</h1><p>Some paragraph text.</p></body>
    </html>
""")
