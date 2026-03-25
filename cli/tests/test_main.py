"""Comprehensive tests for campfire_cli.main."""

from __future__ import annotations

import datetime
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import httpx
import pytest
import yaml
from typer.testing import CliRunner

from campfire_cli import main
from tests.conftest import SAMPLE_HTML

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chdir(tmp_path: Path, monkeypatch):
    """Set cwd to tmp_path so find_repo_root picks it up."""
    main._reset_repo_root_cache()
    monkeypatch.chdir(tmp_path)


# ---------------------------------------------------------------------------
# 1. find_repo_root
# ---------------------------------------------------------------------------

class TestFindRepoRoot:
    def test_finds_hugo_toml_in_cwd(self, tmp_repo, monkeypatch):
        _chdir(tmp_repo, monkeypatch)
        assert main.find_repo_root() == tmp_repo

    def test_finds_hugo_toml_in_parent(self, tmp_repo, monkeypatch):
        child = tmp_repo / "cli"
        child.mkdir()
        _chdir(child, monkeypatch)
        assert main.find_repo_root() == tmp_repo

    def test_raises_when_missing(self, tmp_path, monkeypatch):
        _chdir(tmp_path, monkeypatch)
        with pytest.raises(Exception):
            main.find_repo_root()


# ---------------------------------------------------------------------------
# 2. current_iso_week
# ---------------------------------------------------------------------------

class TestCurrentIsoWeek:
    def test_returns_tuple(self):
        year, week = main.current_iso_week()
        assert isinstance(year, int)
        assert isinstance(week, int)
        assert 1 <= week <= 53

    @patch("campfire_cli.main.datetime")
    def test_specific_date(self, mock_dt):
        mock_dt.date.today.return_value = datetime.date(2026, 3, 19)
        year, week = main.current_iso_week()
        assert year == 2026
        assert week == 12


# ---------------------------------------------------------------------------
# 3. slugify
# ---------------------------------------------------------------------------

class TestSlugify:
    def test_basic(self):
        assert main.slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert main.slugify("What's new in C++?") == "whats-new-in-c"

    def test_multiple_spaces_and_underscores(self):
        assert main.slugify("foo   bar__baz") == "foo-bar-baz"

    def test_leading_trailing(self):
        assert main.slugify("  --hello--  ") == "hello"

    def test_max_length(self):
        result = main.slugify("a" * 100, max_len=10)
        assert len(result) == 10

    def test_unicode(self):
        result = main.slugify("cafe resume")
        assert result == "cafe-resume"

    def test_empty_string(self):
        assert main.slugify("") == "untitled"


# ---------------------------------------------------------------------------
# 4. find_duplicate_url
# ---------------------------------------------------------------------------

class TestFindDuplicateUrl:
    def test_finds_duplicate(self, tmp_repo, sample_link_md, monkeypatch):
        _chdir(tmp_repo, monkeypatch)
        result = main.find_duplicate_url("https://example.com/post")
        assert result == sample_link_md

    def test_no_duplicate(self, tmp_repo, sample_link_md, monkeypatch):
        _chdir(tmp_repo, monkeypatch)
        assert main.find_duplicate_url("https://other.com") is None

    def test_empty_content_dir(self, tmp_repo, monkeypatch):
        _chdir(tmp_repo, monkeypatch)
        assert main.find_duplicate_url("https://example.com") is None


# ---------------------------------------------------------------------------
# 5. parse_front_matter / write_front_matter round-trip
# ---------------------------------------------------------------------------

class TestFrontMatter:
    def test_round_trip(self, tmp_path):
        p = tmp_path / "test.md"
        fm = {"title": "Test", "tags": ["a", "b"], "count": 42}
        body = "\nSome body content.\n"
        main.write_front_matter(p, fm, body)
        parsed_fm, parsed_body = main.parse_front_matter(p)
        assert parsed_fm["title"] == "Test"
        assert parsed_fm["tags"] == ["a", "b"]
        assert parsed_fm["count"] == 42
        assert "Some body content." in parsed_body

    def test_no_front_matter(self, tmp_path):
        p = tmp_path / "plain.md"
        p.write_text("Just plain text.")
        fm, body = main.parse_front_matter(p)
        assert fm == {}
        assert "Just plain text." in body

    def test_empty_front_matter(self, tmp_path):
        p = tmp_path / "empty.md"
        p.write_text("---\n---\nBody here.\n")
        fm, body = main.parse_front_matter(p)
        assert fm == {}
        assert "Body here." in body


# ---------------------------------------------------------------------------
# 6. ensure_week_dir
# ---------------------------------------------------------------------------

class TestEnsureWeekDir:
    def test_creates_dirs_and_indexes(self, tmp_repo, monkeypatch):
        _chdir(tmp_repo, monkeypatch)
        week_dir = main.ensure_week_dir(2026, 5)

        assert week_dir.exists()
        assert (week_dir.parent / "_index.md").exists()
        assert (week_dir / "_index.md").exists()

        # Verify year _index.md content
        fm, _ = main.parse_front_matter(week_dir.parent / "_index.md")
        assert fm["title"] == "2026"
        assert fm["year"] == 2026

        # Verify week _index.md content
        fm, _ = main.parse_front_matter(week_dir / "_index.md")
        assert fm["title"] == "Week 5"
        assert fm["week"] == 5

    def test_idempotent(self, tmp_repo, monkeypatch):
        _chdir(tmp_repo, monkeypatch)
        d1 = main.ensure_week_dir(2026, 5)
        d2 = main.ensure_week_dir(2026, 5)
        assert d1 == d2


# ---------------------------------------------------------------------------
# 7. get_existing_tags
# ---------------------------------------------------------------------------

class TestGetExistingTags:
    def test_collects_tags(self, tmp_repo, sample_link_md, second_link_md, monkeypatch):
        _chdir(tmp_repo, monkeypatch)
        tags = main.get_existing_tags()
        assert "python" in tags
        assert "testing" in tags
        assert "kubernetes" in tags
        assert "devops" in tags

    def test_empty_content(self, tmp_repo, monkeypatch):
        _chdir(tmp_repo, monkeypatch)
        assert main.get_existing_tags() == []


# ---------------------------------------------------------------------------
# 8. _llm_config
# ---------------------------------------------------------------------------

class TestLlmConfig:
    @pytest.fixture(autouse=True)
    def reset_cache(self):
        main._reset_caches()
        yield
        main._reset_caches()

    def test_explicit_env_vars(self, monkeypatch):
        monkeypatch.setenv("LLM_BASE_URL", "http://myserver:8080/v1/")
        monkeypatch.setenv("LLM_API_KEY", "sk-test")
        monkeypatch.setenv("LLM_MODEL", "gpt-4")
        result = main._llm_config()
        assert result == ("http://myserver:8080/v1", "sk-test", "gpt-4")

    def test_base_url_defaults_key_and_model(self, monkeypatch):
        monkeypatch.setenv("LLM_BASE_URL", "http://local:9999")
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        monkeypatch.delenv("LLM_MODEL", raising=False)
        result = main._llm_config()
        assert result == ("http://local:9999", "no-key", "default")

    @patch("campfire_cli.main.httpx.get")
    def test_auto_detect_ollama(self, mock_get, monkeypatch):
        monkeypatch.delenv("LLM_BASE_URL", raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        monkeypatch.delenv("LLM_MODEL", raising=False)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"id": "llama3.1"}]}
        mock_get.return_value = mock_resp
        result = main._llm_config()
        assert result == ("http://localhost:11434/v1", "no-key", "llama3.1")

    @patch("campfire_cli.main.httpx.get", side_effect=Exception("connection refused"))
    def test_nothing_available(self, mock_get, monkeypatch):
        monkeypatch.delenv("LLM_BASE_URL", raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        monkeypatch.delenv("LLM_MODEL", raising=False)
        assert main._llm_config() is None


# ---------------------------------------------------------------------------
# 9. _llm_chat
# ---------------------------------------------------------------------------

class TestLlmChat:
    @patch("campfire_cli.main._llm_config", return_value=("http://localhost:11434/v1", "no-key", "llama3"))
    @patch("campfire_cli.main.httpx.post")
    def test_successful_call(self, mock_post, mock_config):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "  hello world  "}}]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp
        result = main._llm_chat("test prompt")
        assert result == "hello world"

    @patch("campfire_cli.main._llm_config", return_value=None)
    def test_no_config(self, mock_config):
        assert main._llm_chat("test") is None

    @patch("campfire_cli.main._llm_config", return_value=("http://localhost:11434/v1", "no-key", "llama3"))
    @patch("campfire_cli.main.httpx.post", side_effect=httpx.ConnectError("refused"))
    def test_request_failure(self, mock_post, mock_config):
        result = main._llm_chat("test")
        assert result is None


# ---------------------------------------------------------------------------
# 10. suggest_tags_with_llm
# ---------------------------------------------------------------------------

class TestSuggestTagsWithLlm:
    @patch("campfire_cli.main._llm_chat", return_value="cloud, infrastructure, devops")
    def test_parses_comma_response(self, mock_chat):
        tags = main.suggest_tags_with_llm("Title", "Desc", "text", [])
        assert tags == ["cloud", "infrastructure", "devops"]

    @patch("campfire_cli.main._llm_chat", return_value=None)
    def test_llm_unavailable(self, mock_chat):
        assert main.suggest_tags_with_llm("T", "D", "t", []) == []

    @patch("campfire_cli.main._llm_chat", return_value="  security  ")
    def test_single_tag(self, mock_chat):
        assert main.suggest_tags_with_llm("T", "D", "t", []) == ["security"]


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# 12. fetch_metadata
# ---------------------------------------------------------------------------

class TestFetchMetadata:
    @patch("campfire_cli.main.suggest_tags_with_llm", return_value=["python", "testing"])
    @patch("campfire_cli.main.get_existing_tags", return_value=["python"])
    @patch("campfire_cli.main.httpx.get")
    def test_extracts_og_tags(self, mock_get, mock_existing, mock_suggest):
        mock_resp = MagicMock()
        mock_resp.text = SAMPLE_HTML
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        meta = main.fetch_metadata("https://example.com/page")
        assert meta["title"] == "OG Title Here"
        assert meta["description"] == "OG description text."
        assert "python" in meta["tags"]

    @patch("campfire_cli.main.suggest_tags_with_llm", return_value=[])
    @patch("campfire_cli.main.get_existing_tags", return_value=[])
    @patch("campfire_cli.main.httpx.get")
    def test_falls_back_to_title_tag(self, mock_get, mock_existing, mock_suggest):
        html = "<html><head><title>Fallback Title</title></head><body><p>Body</p></body></html>"
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        meta = main.fetch_metadata("https://example.com")
        assert meta["title"] == "Fallback Title"

    @patch("campfire_cli.main.httpx.get", side_effect=httpx.HTTPStatusError("404", request=MagicMock(), response=MagicMock()))
    def test_http_error_returns_empty(self, mock_get):
        meta = main.fetch_metadata("https://example.com/404")
        assert meta["title"] == ""
        assert meta["description"] == ""


# ---------------------------------------------------------------------------
# 13. detect_author
# ---------------------------------------------------------------------------

class TestDetectAuthor:
    @patch("campfire_cli.main.subprocess.run")
    def test_gh_cli_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="octocat\n")
        assert main.detect_author() == "@octocat"

    @patch("campfire_cli.main.subprocess.run")
    def test_git_config_fallback(self, mock_run):
        def side_effect(cmd, **kwargs):
            if "gh" in cmd:
                return MagicMock(returncode=1, stdout="")
            return MagicMock(returncode=0, stdout="gituser\n")
        mock_run.side_effect = side_effect
        assert main.detect_author() == "@gituser"

    @patch("campfire_cli.main.subprocess.run")
    def test_nothing_found(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert main.detect_author() is None


# ---------------------------------------------------------------------------
# 14. require_author
# ---------------------------------------------------------------------------

class TestRequireAuthor:
    def test_flag_override_with_at(self):
        assert main.require_author("@myuser") == "@myuser"

    def test_flag_override_without_at(self):
        assert main.require_author("myuser") == "@myuser"

    @patch("campfire_cli.main.detect_author", return_value="@detected")
    def test_detected_author(self, mock_detect):
        assert main.require_author(None) == "@detected"

    @patch("campfire_cli.main.Confirm.ask", return_value=False)
    @patch("campfire_cli.main.Prompt.ask", return_value="prompted")
    @patch("campfire_cli.main.detect_author", return_value=None)
    def test_prompt_fallback(self, mock_detect, mock_prompt, mock_confirm):
        assert main.require_author(None) == "@prompted"


# ---------------------------------------------------------------------------
# 15. capture_screenshot
# ---------------------------------------------------------------------------

class TestCaptureScreenshot:
    @patch("campfire_cli.main.find_repo_root")
    @patch("campfire_cli.main._fetch_og_image", return_value=b"\x89PNG fake image data")
    def test_og_image_success(self, mock_fetch_og, mock_root, tmp_repo):
        mock_root.return_value = tmp_repo
        result = main.capture_screenshot("https://example.com", "test-slug")
        assert result is True
        assert (tmp_repo / "static" / "screenshots" / "test-slug.png").exists()

    @patch("campfire_cli.main.find_repo_root")
    @patch("campfire_cli.main._fetch_og_image", return_value=None)
    def test_playwright_fallback_to_pillow(self, mock_fetch_og, mock_root, tmp_repo):
        mock_root.return_value = tmp_repo
        # Mock playwright import to simulate failure, so it falls through to Pillow
        mock_playwright = MagicMock()
        mock_playwright.__enter__ = MagicMock(side_effect=Exception("no browsers"))
        mock_sync = MagicMock(return_value=mock_playwright)
        with patch("campfire_cli.main._generate_card_image", return_value=b"\x89PNG card") as mock_card, \
             patch("playwright.sync_api.sync_playwright", mock_sync):
            # Force playwright to fail by patching the import inside capture_screenshot
            with patch.dict("sys.modules", {"playwright": MagicMock(), "playwright.sync_api": MagicMock(sync_playwright=mock_sync)}):
                # Actually we need to make the sync_playwright context manager raise
                import campfire_cli.main as m
                original = m.capture_screenshot

                # Simpler approach: just patch at the right level
                def _fake_sync_playwright():
                    raise Exception("no browsers installed")

                with patch("playwright.sync_api.sync_playwright", side_effect=_fake_sync_playwright):
                    result = main.capture_screenshot(
                        "https://example.com", "test-slug",
                        title="Test", description="Desc", tags=["a"]
                    )
                    assert result is True
                    mock_card.assert_called_once()

    @patch("campfire_cli.main.find_repo_root")
    @patch("campfire_cli.main._fetch_og_image", return_value=None)
    @patch("campfire_cli.main._generate_card_image", side_effect=Exception("pillow broken"))
    def test_all_strategies_fail(self, mock_card, mock_fetch_og, mock_root, tmp_repo):
        mock_root.return_value = tmp_repo

        def _fake_sync_playwright():
            raise Exception("no browsers installed")

        with patch("playwright.sync_api.sync_playwright", side_effect=_fake_sync_playwright):
            result = main.capture_screenshot("https://example.com", "fail-slug")
            assert result is False


# ---------------------------------------------------------------------------
# 16. add command (integration test)
# ---------------------------------------------------------------------------

class TestAddCommand:
    @patch("campfire_cli.main.run_hugo", return_value=True)
    @patch("campfire_cli.main.capture_screenshot", return_value=True)
    @patch("campfire_cli.main.Prompt.ask", side_effect=["My Title", "A description", "python, testing"])
    @patch("campfire_cli.main.fetch_metadata", return_value={
        "title": "My Title",
        "description": "A description",
        "tags": ["python", "testing"],
    })
    @patch("campfire_cli.main.find_duplicate_url", return_value=None)
    @patch("campfire_cli.main.current_iso_week", return_value=(2026, 12))
    @patch("campfire_cli.main.find_repo_root")
    @patch("campfire_cli.main._load_dotenv")
    def test_add_basic(self, mock_dotenv, mock_root, mock_week, mock_dup, mock_fetch,
                       mock_prompt, mock_screenshot, mock_hugo, tmp_repo):
        mock_root.return_value = tmp_repo

        result = runner.invoke(main.app, ["link", "add", "https://example.com/new", "--force"])
        assert result.exit_code == 0, result.output

        # Check that a file was created
        week_dir = tmp_repo / "content" / "2026" / "w12"
        md_files = list(week_dir.glob("*.md"))
        link_files = [f for f in md_files if f.name != "_index.md"]
        assert len(link_files) >= 1


# ---------------------------------------------------------------------------
# 17. comment command
# ---------------------------------------------------------------------------

class TestCommentCommand:
    @patch("campfire_cli.main.run_hugo", return_value=True)
    @patch("campfire_cli.main.require_author", return_value="@tester")
    @patch("campfire_cli.main.find_repo_root")
    @patch("campfire_cli.main._load_dotenv")
    def test_adds_comment(self, mock_dotenv, mock_root, mock_author, mock_hugo,
                          tmp_repo, sample_link_md):
        mock_root.return_value = tmp_repo

        result = runner.invoke(main.app, [
            "link", "comment", "2026/w12/example-post", "Great article!",
        ])
        assert result.exit_code == 0, result.output

        fm, _ = main.parse_front_matter(sample_link_md)
        assert len(fm["comments"]) == 1
        assert fm["comments"][0]["text"] == "Great article!"
        assert fm["comments"][0]["author"] == "@tester"

    @patch("campfire_cli.main.find_repo_root")
    @patch("campfire_cli.main._load_dotenv")
    def test_nonexistent_permalink(self, mock_dotenv, mock_root, tmp_repo):
        mock_root.return_value = tmp_repo

        result = runner.invoke(main.app, [
            "link", "comment", "2026/w99/nope", "text", "--author", "bob",
        ])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# 18. list command
# ---------------------------------------------------------------------------

class TestListCommand:
    @patch("campfire_cli.main.find_repo_root")
    @patch("campfire_cli.main._load_dotenv")
    def test_displays_table(self, mock_dotenv, mock_root, tmp_repo, sample_link_md):
        mock_root.return_value = tmp_repo

        result = runner.invoke(main.app, ["list", "--year", "2026", "--week", "12"])
        assert result.exit_code == 0
        assert "Example Post" in result.output

    @patch("campfire_cli.main.find_repo_root")
    @patch("campfire_cli.main._load_dotenv")
    def test_no_content(self, mock_dotenv, mock_root, tmp_repo):
        mock_root.return_value = tmp_repo

        result = runner.invoke(main.app, ["list", "--year", "2099", "--week", "1"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# 19. _load_dotenv
# ---------------------------------------------------------------------------

class TestLoadDotenv:
    def test_loads_env_file(self, tmp_repo, monkeypatch):
        _chdir(tmp_repo, monkeypatch)
        env_file = tmp_repo / ".env"
        env_file.write_text("MY_TEST_VAR=hello\nANOTHER_VAR='quoted'\n")
        # Make sure vars are not set
        monkeypatch.delenv("MY_TEST_VAR", raising=False)
        monkeypatch.delenv("ANOTHER_VAR", raising=False)

        main._load_dotenv()
        assert os.environ["MY_TEST_VAR"] == "hello"
        assert os.environ["ANOTHER_VAR"] == "quoted"

    def test_skips_comments_and_blanks(self, tmp_repo, monkeypatch):
        _chdir(tmp_repo, monkeypatch)
        env_file = tmp_repo / ".env"
        env_file.write_text("# This is a comment\n\nVALID_KEY=value\n")
        monkeypatch.delenv("VALID_KEY", raising=False)

        main._load_dotenv()
        assert os.environ["VALID_KEY"] == "value"

    def test_does_not_override_existing(self, tmp_repo, monkeypatch):
        _chdir(tmp_repo, monkeypatch)
        monkeypatch.setenv("EXISTING_VAR", "original")
        env_file = tmp_repo / ".env"
        env_file.write_text("EXISTING_VAR=overridden\n")

        main._load_dotenv()
        assert os.environ["EXISTING_VAR"] == "original"

    def test_no_env_file(self, tmp_repo, monkeypatch):
        _chdir(tmp_repo, monkeypatch)
        # Should not raise
        main._load_dotenv()
