"""Campfire CLI — curate weekly link collections."""

from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import shutil
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import httpx
import typer
import yaml
from bs4 import BeautifulSoup
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

app = typer.Typer(help="Campfire — weekly link curation CLI", no_args_is_help=True)
link_app = typer.Typer(help="Single-link operations: add, delete, comment", no_args_is_help=True)
site_app = typer.Typer(help="Site management: backup, restore, retag, redate, rebuild, wipe", no_args_is_help=True)
app.add_typer(link_app, name="link")
app.add_typer(site_app, name="site")

ALLOWED_TAGS = {
    "cloud", "infrastructure", "networking", "storage", "devops", "monitoring",
    "security", "automation", "containers", "homelab", "development", "api",
    "web", "cli", "terminal", "ai", "git", "linux", "windows", "macos",
    "desktop", "ux", "troubleshooting", "virtualization", "database",
    "opensource", "performance", "testing", "hardware", "career",
    "vmware", "python", "kubernetes", "rust", "golang", "docker", "ssh",
}

_repo_root_cache: Path | None = None
_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
           "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


@app.callback()
def _app_callback() -> None:
    """Campfire — weekly link curation CLI."""
    _load_dotenv()
console = Console()


def _load_dotenv() -> None:
    """Load .env file from repo root if it exists."""
    try:
        root = find_repo_root()
    except Exception:
        root = Path.cwd()
    env_file = root / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = value


def find_repo_root() -> Path:
    """Walk up from cwd looking for hugo.toml. Cached after first call."""
    global _repo_root_cache
    if _repo_root_cache is not None:
        return _repo_root_cache
    path = Path.cwd()
    for parent in [path, *path.parents]:
        if (parent / "hugo.toml").exists():
            _repo_root_cache = parent
            return parent
    if (path.parent / "hugo.toml").exists():
        _repo_root_cache = path.parent
        return path.parent
    raise typer.BadParameter("Cannot find repo root (no hugo.toml found in parent directories)")


def _reset_caches() -> None:
    """Reset all caches (for testing)."""
    global _repo_root_cache, _existing_tags_cache, _llm_config_cache
    _repo_root_cache = None
    _existing_tags_cache = None
    _llm_config_cache = False


# Keep backward compat for tests
_reset_repo_root_cache = _reset_caches


def content_dir() -> Path:
    return find_repo_root() / "content"


def _iter_link_files(year: int | None = None, week: int | None = None):
    """Iterate all link markdown files, yielding (path, frontmatter) tuples."""
    cdir = content_dir()
    for md_file in sorted(cdir.rglob("*.md")):
        if md_file.name == "_index.md":
            continue
        fm, body = parse_front_matter(md_file)
        if not fm.get("url_link"):
            continue
        if year and fm.get("year") != year:
            continue
        if week and fm.get("week") != week:
            continue
        yield md_file, fm, body


def _find_link_by_permalink(permalink: str):
    """Find a link file by its permalink. Returns (path, fm, slug) or None."""
    permalink = permalink.strip("/")
    for md_file, fm, _ in _iter_link_files():
        slug = md_file.stem
        link_permalink = f"{fm.get('year')}/w{fm.get('week', 0):02d}/{slug}"
        if link_permalink == permalink:
            return md_file, fm, slug
    return None


def current_iso_week() -> tuple[int, int]:
    today = datetime.date.today()
    year, week, _ = today.isocalendar()
    return year, week


def slugify(text: str, max_len: int = 60) -> str:
    import unicodedata
    # Transliterate accented chars to ASCII (é→e, ü→u, etc.)
    slug = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = slug.lower().strip()
    slug = re.sub(r"[^a-z0-9\s_-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:max_len] if slug else "untitled"


def find_duplicate_url(url: str) -> Path | None:
    """Scan all link files for a matching url_link."""
    cdir = content_dir()
    for md_file in cdir.rglob("*.md"):
        if md_file.name == "_index.md":
            continue
        try:
            fm, _ = parse_front_matter(md_file)
            if fm and fm.get("url_link") == url:
                return md_file
        except Exception:
            continue
    return None


def parse_front_matter(path: Path) -> tuple[dict, str]:
    """Parse a markdown file into (front_matter_dict, body)."""
    text = path.read_text()
    if not text.startswith("---"):
        return {}, text
    # Find the closing --- on its own line (not inside content like URLs with ---)
    match = re.search(r"\n---\s*\n", text[3:])
    if not match:
        return {}, text
    end = match.start() + 3  # offset from skipping opening ---
    fm_str = text[4:end]  # between opening --- and closing ---
    body = text[end + match.end() - match.start():]
    fm = yaml.safe_load(fm_str) or {}
    return fm, body


def write_front_matter(path: Path, fm: dict, body: str = "") -> None:
    """Write a markdown file with YAML front matter."""
    yaml_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    # Validate the YAML roundtrips cleanly
    try:
        yaml.safe_load(yaml_str)
    except yaml.YAMLError:
        # Sanitize problematic string fields
        for key in ("description", "title"):
            if key in fm and isinstance(fm[key], str):
                fm[key] = fm[key].replace("\x00", "").strip()
        yaml_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    path.write_text(f"---\n{yaml_str}---\n{body}")


def ensure_week_dir(year: int, week: int) -> Path:
    """Create year and week directories + _index.md files if needed."""
    cdir = content_dir()
    year_dir = cdir / str(year)
    week_dir = year_dir / f"w{week:02d}"

    # Year _index.md
    year_dir.mkdir(parents=True, exist_ok=True)
    year_index = year_dir / "_index.md"
    if not year_index.exists():
        write_front_matter(year_index, {"title": str(year), "year": year})

    # Week _index.md
    week_dir.mkdir(parents=True, exist_ok=True)
    week_index = week_dir / "_index.md"
    if not week_index.exists():
        # Calculate the Monday of this ISO week
        monday = datetime.date.fromisocalendar(year, week, 1)
        write_front_matter(week_index, {
            "title": f"Week {week}",
            "date": monday.isoformat(),
            "year": year,
            "week": week,
        })

    return week_dir


HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


_YOUTUBE_HOSTS = {"www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"}
_TWITTER_HOSTS = {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}


def _is_twitter_url(url: str) -> bool:
    """Check if a URL is a Twitter/X link."""
    return urlparse(url).hostname in _TWITTER_HOSTS


def _fetch_twitter_metadata(url: str) -> dict | None:
    """Fetch tweet/profile metadata from X using fxtwitter API."""
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    if not parts:
        return None

    username = parts[0]
    is_tweet = len(parts) >= 3 and parts[1] == "status"

    if is_tweet:
        tweet_id = parts[2]
        try:
            r = httpx.get(f"https://api.fxtwitter.com/{username}/status/{tweet_id}", timeout=10.0, headers=HTTP_HEADERS)
            r.raise_for_status()
            data = r.json().get("tweet", {})
            author = data.get("author", {})
            name = author.get("name", username)
            screen_name = author.get("screen_name", username)
            text = data.get("text", "").strip()

            # Check for article (X long-form posts)
            article = data.get("article") or {}
            if article.get("title"):
                title = article["title"]
                description = article.get("preview_text", "").strip() or text or f"Article by @{screen_name}"
            else:
                title = f"@{screen_name}: {text[:80]}{'...' if len(text) > 80 else ''}" if text else f"@{screen_name} on X"
                description = text or f"Post by {name}"

            # Extract image URL: article cover > tweet photos > tweet video thumbnails
            image_url = None
            cover_media = article.get("cover_media") or {}
            media_info = cover_media.get("media_info") or {}
            if media_info.get("original_img_url"):
                image_url = media_info["original_img_url"]

            if not image_url:
                media = data.get("media") or {}
                photos = media.get("photos", [])
                image_url = photos[0].get("url") if photos else None
                if not image_url:
                    videos = media.get("videos", [])
                    image_url = videos[0].get("thumbnail_url") if videos else None

            # Extract date
            created = data.get("created_at", "")
            tweet_date = None
            if created:
                try:
                    from email.utils import parsedate_to_datetime
                    tweet_date = parsedate_to_datetime(created).date()
                except Exception:
                    pass

            return {"title": title, "description": description, "image_url": image_url, "date": tweet_date}
        except Exception:
            pass

    return {"title": f"@{username} on X",
            "description": f"Post by @{username}" if is_tweet else f"@{username}'s profile on X",
            "image_url": None, "date": None}


def _fetch_twitter_image(url: str) -> bytes | None:
    """Fetch the image from a tweet if available."""
    meta = _fetch_twitter_metadata(url)
    if not meta or not meta.get("image_url"):
        return None
    try:
        resp = httpx.get(meta["image_url"], follow_redirects=True, timeout=10.0)
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
            return resp.content
    except Exception:
        pass
    return None


def _is_youtube_url(url: str) -> bool:
    """Check if a URL is a YouTube video link."""
    return urlparse(url).hostname in _YOUTUBE_HOSTS


def _fetch_youtube_metadata(url: str) -> dict | None:
    """Fetch video-specific metadata from YouTube using oEmbed + page scrape."""
    # Get title and author via oEmbed (no API key needed)
    oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
    title = ""
    try:
        r = httpx.get(oembed_url, timeout=10.0)
        r.raise_for_status()
        data = r.json()
        title = data.get("title", "")
    except Exception:
        pass

    # Scrape the page for the video description (embedded in page JS, not meta tags)
    description = ""
    soup = None
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=10.0, headers={
            **HTTP_HEADERS,
            "Accept-Language": "en-US,en;q=0.9",
        })
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # YouTube embeds the real video description in JS data as attributedDescription
        match = re.search(r'"attributedDescription":\{"content":"(.*?)(?<!\\)"\,', resp.text)
        if match:
            raw_desc = json.loads('"' + match.group(1) + '"')
            # Filter out sponsor lines
            lines = [l for l in raw_desc.split("\n") if not re.search(r"sponsor", l, re.IGNORECASE)]
            # Convert timestamps (e.g. "01:46 - Topic") to clickable YouTube links
            video_id = _extract_youtube_video_id(url)
            if video_id:
                converted = []
                for line in lines:
                    ts_match = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?\s*[-–—]?\s*(.+)$", line)
                    if ts_match:
                        parts = ts_match.groups()
                        if parts[2] is not None:  # HH:MM:SS
                            seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                        else:  # MM:SS
                            seconds = int(parts[0]) * 60 + int(parts[1])
                        label = parts[3].strip()
                        ts_label = ts_match.group(0).split(" ")[0]  # original timestamp text
                        yt_link = f"https://www.youtube.com/watch?v={video_id}&t={seconds}s"
                        line = f'<a href="{yt_link}" target="_blank" rel="noopener">{ts_label}</a> - {label}'
                    converted.append(line)
                lines = converted
            description = "\n".join(lines).strip()

        # Use og:title as fallback if oEmbed failed
        if not title:
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = og_title["content"]
    except Exception:
        pass

    if not title:
        return None

    return {"title": title, "description": description, "_soup": soup}


def _extract_youtube_video_id(url: str) -> str | None:
    """Extract the video ID from a YouTube URL."""
    parsed = urlparse(url)
    if parsed.hostname == "youtu.be" or parsed.hostname == "www.youtu.be":
        return parsed.path.lstrip("/").split("/")[0] or None
    if parsed.hostname in _YOUTUBE_HOSTS:
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [None])[0]
        # /embed/ID, /v/ID, /shorts/ID
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] in ("embed", "v", "shorts"):
            return parts[1]
    return None


def _fetch_youtube_thumbnail(url: str) -> bytes | None:
    """Fetch the highest-resolution YouTube thumbnail available."""
    video_id = _extract_youtube_video_id(url)
    if not video_id:
        return None
    # Try resolutions from highest to lowest
    for quality in ("maxresdefault", "sddefault", "hqdefault", "mqdefault"):
        thumb_url = f"https://i.ytimg.com/vi/{video_id}/{quality}.jpg"
        try:
            resp = httpx.get(thumb_url, follow_redirects=True, timeout=10.0)
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
                return resp.content
        except Exception:
            continue
    return None


def screenshots_dir() -> Path:
    return find_repo_root() / "static" / "screenshots"


def _fetch_og_image(url: str, soup: BeautifulSoup | None = None) -> bytes | None:
    """Try to fetch the og:image from a URL."""
    if soup is None:
        try:
            resp = httpx.get(url, follow_redirects=True, timeout=10.0, headers=HTTP_HEADERS)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception:
            return None

    og_img = soup.find("meta", property="og:image")
    if not og_img or not og_img.get("content"):
        # Also try twitter:image
        og_img = soup.find("meta", attrs={"name": "twitter:image"})
    if not og_img or not og_img.get("content"):
        return None

    img_url = og_img["content"]
    # Handle relative URLs
    if img_url.startswith("/"):

        parsed = urlparse(url)
        img_url = f"{parsed.scheme}://{parsed.netloc}{img_url}"

    img_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }
    backoffs = [3, 5, 8]
    for attempt in range(len(backoffs) + 1):
        try:
            resp = httpx.get(img_url, follow_redirects=True, timeout=15.0, headers=img_headers)
        except Exception:
            return None
        if resp.status_code == 429 and attempt < len(backoffs):
            wait = backoffs[attempt]
            console.print(f"[yellow]og:image rate-limited (429), retrying in {wait}s...[/yellow]")
            time.sleep(wait)
            continue
        if resp.status_code != 200:
            return None
        ct = resp.headers.get("content-type", "")
        if ct.startswith("image") and "svg" not in ct:
            return resp.content
        return None
    return None


def _generate_card_image(title: str, domain: str, description: str, tags: list[str]) -> bytes:
    """Generate a styled card image using Pillow."""
    from PIL import Image, ImageDraw, ImageFont
    from io import BytesIO

    W, H = 1280, 720
    # Catppuccin Mocha colors
    bg = (30, 30, 46)
    surface = (49, 50, 68)
    text_color = (205, 214, 244)
    subtext = (166, 173, 200)
    accent = (180, 190, 254)  # lavender
    mauve = (203, 166, 247)

    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    # Try to use a nice font, fall back to default
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)
        font_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        font_tag = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    except OSError:
        font_title = ImageFont.load_default(38)
        font_body = ImageFont.load_default(22)
        font_small = ImageFont.load_default(18)
        font_tag = ImageFont.load_default(18)

    pad = 60
    y = pad

    # Domain
    draw.text((pad, y), domain, fill=accent, font=font_small)
    y += 36

    # Word-wrap helper
    def _wrap(text, font, max_width):
        words = text.split()
        lines, line = [], ""
        for w in words:
            test = f"{line} {w}".strip()
            if draw.textbbox((0, 0), test, font=font)[2] > max_width and line:
                lines.append(line)
                line = w
            else:
                line = test
        if line:
            lines.append(line)
        return lines

    # Title
    max_w = W - 2 * pad
    for ln in _wrap(title, font_title, max_w)[:3]:
        draw.text((pad, y), ln, fill=text_color, font=font_title)
        y += 50
    y += 20

    # Description
    if description:
        for ln in _wrap(description, font_body, max_w)[:4]:
            draw.text((pad, y), ln, fill=subtext, font=font_body)
            y += 32
    y += 30

    # Tags
    tag_x = pad
    tag_colors = [
        (180, 190, 254), (203, 166, 247), (148, 226, 213), (250, 179, 135),
        (166, 227, 161), (245, 194, 231), (249, 226, 175), (137, 220, 235),
    ]
    for i, tag in enumerate(tags[:8]):
        color = tag_colors[i % len(tag_colors)]
        bbox = draw.textbbox((0, 0), tag, font=font_tag)
        tw = bbox[2] - bbox[0] + 24
        th = bbox[3] - bbox[1] + 14
        if tag_x + tw > W - pad:
            tag_x = pad
            y += th + 10
        # Pill background
        draw.rounded_rectangle(
            [tag_x, y, tag_x + tw, y + th],
            radius=th // 2,
            fill=(color[0] // 5, color[1] // 5, color[2] // 5),
            outline=(*color, 80),
        )
        draw.text((tag_x + 12, y + 5), tag, fill=color, font=font_tag)
        tag_x += tw + 10

    # Bottom accent line
    draw.rectangle([0, H - 4, W, H], fill=mauve)

    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _dismiss_cookie_banner(page) -> None:
    """Try to dismiss cookie consent banners using multiple strategies."""
    # Strategy 1: Known banner button selectors (most reliable)
    known_buttons = [
        "#onetrust-accept-btn-handler",
        "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
        "#CybotCookiebotDialogBodyButtonAccept",
        ".cc-accept", ".cc-allow", ".cc-dismiss",
        "#gdpr-cookie-accept", ".gdpr-accept",
        '[data-testid="cookie-accept"]',
        "#cookie-accept", "#accept-cookies",
        ".cookie-accept", ".accept-cookies",
        "#truste-consent-button",
        ".js-cookie-consent-agree",
        "#cookieChoiceDismiss",
        ".blogspot-cookie-consent-dismiss",
        ".fc-cta-consent",
    ]
    for sel in known_buttons:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                page.wait_for_timeout(500)
                return
        except Exception:
            continue

    # Strategy 2: Find buttons by text content
    accept_texts = [
        "Accept", "Accept All", "Allow All", "Agree", "Allow",
        "I Agree", "Got It", "OK", "Accept Cookies", "Allow Cookies",
        "Accepter", "Tout accepter", "J'accepte", "Autoriser",
    ]
    for text in accept_texts:
        try:
            btn = page.get_by_role("button", name=text, exact=False)
            if btn.count() > 0 and btn.first.is_visible():
                btn.first.click()
                page.wait_for_timeout(500)
                return
        except Exception:
            continue


def capture_screenshot(url: str, slug: str, soup: BeautifulSoup | None = None,
                       title: str = "", description: str = "", tags: list[str] | None = None) -> bool:
    """Capture a preview image for a link.

    Strategy:
    1. Fetch og:image from the page (fast, lightweight)
    2. Playwright browser screenshot (full render)
    3. Fall back to generating a styled card image with Pillow
    """
    out_dir = screenshots_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}.png"

    # Check if site is accessible (skip to card on 403/Cloudflare/X)
    site_blocked = False
    if _is_twitter_url(url):
        # Try to get tweet image first
        with console.status(f"Fetching X post image for [cyan]{url}[/cyan]..."):
            img_data = _fetch_twitter_image(url)
        if img_data:
            out_path.write_bytes(img_data)
            console.print(f"[green]Tweet image saved:[/green] {out_path.relative_to(find_repo_root())}")
            return True
        console.print(f"[dim]X/Twitter — no image, generating card...[/dim]")
        site_blocked = True
    else:
        try:
            resp = httpx.head(url, follow_redirects=True, timeout=5.0, headers=HTTP_HEADERS)
            if resp.status_code == 403:
                console.print(f"[dim]Site returned 403, generating card...[/dim]")
                site_blocked = True
        except Exception:
            pass

    if not site_blocked:
        # Strategy 0 (YouTube): fetch high-res thumbnail directly
        if _is_youtube_url(url):
            with console.status(f"Fetching YouTube thumbnail for [cyan]{url}[/cyan]..."):
                img_data = _fetch_youtube_thumbnail(url)
            if img_data:
                out_path.write_bytes(img_data)
                console.print(f"[green]Thumbnail saved (YouTube):[/green] {out_path.relative_to(find_repo_root())}")
                return True

        # Strategy 1: og:image
        with console.status(f"Fetching og:image for [cyan]{url}[/cyan]..."):
            img_data = _fetch_og_image(url, soup)

        if img_data:
            out_path.write_bytes(img_data)
            console.print(f"[green]Preview image saved (og:image):[/green] {out_path.relative_to(find_repo_root())}")
            return True

        # Strategy 2: Playwright
        try:
            from playwright.sync_api import sync_playwright
            with console.status(f"Capturing screenshot of [cyan]{url}[/cyan]..."):
                with sync_playwright() as p:
                    browser = p.chromium.launch(args=["--no-sandbox", "--disable-setuid-sandbox"])
                    page = browser.new_page(viewport={"width": 1280, "height": 800})
                    page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(2000)
                    # Detect Cloudflare challenge page
                    page_title = page.title().lower()
                    if "just a moment" in page_title or "attention required" in page_title or "cloudflare" in page_title:
                        browser.close()
                        console.print(f"[dim]Cloudflare challenge detected, generating card...[/dim]")
                        raise Exception("Cloudflare challenge")
                    # Try to dismiss cookie banners using Playwright selectors
                    _dismiss_cookie_banner(page)
                    page.screenshot(path=str(out_path), type="png")
                    browser.close()
            console.print(f"[green]Screenshot saved:[/green] {out_path.relative_to(find_repo_root())}")
            return True
        except Exception as e:
            console.print(f"[dim]Playwright failed ({e}), trying fallback...[/dim]")

    # Strategy 3: generate card image
    try:

        domain = urlparse(url).netloc
        with console.status("Generating preview card..."):
            img_data = _generate_card_image(title or slug, domain, description or "", tags or [])
        out_path.write_bytes(img_data)
        # Mark as generated so the template can skip it
        (out_dir / f"{slug}.generated").touch()
        console.print(f"[green]Preview card generated:[/green] {out_path.relative_to(find_repo_root())}")
        return True
    except Exception as e:
        console.print(f"[yellow]Preview generation failed:[/yellow] {e}")
        return False


def run_hugo() -> bool:
    """Run hugo to rebuild the site. Retries once on failure."""
    import time
    root = find_repo_root()
    hugo_bin = shutil.which("hugo")
    if not hugo_bin:
        console.print("[yellow]Warning: hugo not found in PATH, skipping site rebuild[/yellow]")
        return False
    for attempt in range(2):
        result = subprocess.run([hugo_bin, "--cleanDestinationDir"], cwd=root, capture_output=True, text=True)
        if result.returncode == 0:
            console.print("[green]Site rebuilt successfully.[/green]")
            return True
        if attempt == 0:
            time.sleep(1)
    console.print(f"[red]Hugo build failed:[/red]\n{result.stderr}")
    return False


_existing_tags_cache: list[str] | None = None


def get_existing_tags() -> list[str]:
    """Collect all tags already used across the site. Cached per session."""
    global _existing_tags_cache
    if _existing_tags_cache is not None:
        return _existing_tags_cache
    cdir = content_dir()
    tags: set[str] = set()
    for md_file in cdir.rglob("*.md"):
        if md_file.name == "_index.md":
            continue
        try:
            fm, _ = parse_front_matter(md_file)
            for t in fm.get("tags") or []:
                tags.add(t.lower())
        except Exception:
            continue
    _existing_tags_cache = sorted(tags)
    return _existing_tags_cache


_llm_config_cache: tuple[str, str, str] | None | bool = False  # False = not checked yet


def _llm_config() -> tuple[str, str, str] | None:
    """Return (base_url, api_key, model) from env vars, or None if not configured.

    Supports any OpenAI-compatible API (Ollama, LM Studio, OpenAI, vLLM, etc.)

    Env vars:
        LLM_BASE_URL  — API base URL
        LLM_API_KEY   — API key (default: "no-key" for local servers)
        LLM_MODEL     — Model name
    """
    global _llm_config_cache
    if _llm_config_cache is not False:
        return _llm_config_cache
    base_url = os.environ.get("LLM_BASE_URL", "").strip()
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    model = os.environ.get("LLM_MODEL", "").strip()

    if base_url:
        api_key = api_key or "no-key"
        model = model or "default"
        _llm_config_cache = (base_url.rstrip("/"), api_key, model)
        return _llm_config_cache

    # Auto-detect local Ollama
    try:
        r = httpx.get("http://localhost:11434/v1/models", timeout=2.0)
        if r.status_code == 200:
            models = r.json().get("data", [])
            default_model = models[0]["id"] if models else "llama3"
            _llm_config_cache = ("http://localhost:11434/v1", "no-key", model or default_model)
            return _llm_config_cache
    except Exception:
        pass

    # Auto-detect local LM Studio
    try:
        r = httpx.get("http://localhost:1234/v1/models", timeout=2.0)
        if r.status_code == 200:
            models = r.json().get("data", [])
            default_model = models[0]["id"] if models else "default"
            _llm_config_cache = ("http://localhost:1234/v1", "no-key", model or default_model)
            return _llm_config_cache
    except Exception:
        pass

    _llm_config_cache = None
    return None


def _fetch_page_text(url: str) -> str:
    """Fetch a URL and return its text content, or empty string on failure."""
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=10.0, headers=HTTP_HEADERS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        return soup.get_text(separator=" ", strip=True)
    except Exception:
        return ""


def _format_elapsed(elapsed: float) -> str:
    """Format elapsed seconds as human-readable string."""
    mins, secs = divmod(int(elapsed), 60)
    return f"{mins}m {secs:02d}s" if mins else f"{elapsed:.1f}s"


def _llm_chat(prompt: str, status_msg: str = "Thinking...") -> str | None:
    """Send a chat completion request to an OpenAI-compatible endpoint."""
    config = _llm_config()
    if not config:
        console.print("[yellow]No LLM configured — skipping (set LLM_BASE_URL or run Ollama/LM Studio)[/yellow]")
        return None

    base_url, api_key, model = config

    import time
    import threading

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            t0 = time.monotonic()
            stop_timer = threading.Event()
            result_holder: list = []
            error_holder: list = []

            payload = {
                "model": model,
                "temperature": 0.1,
                "messages": [{"role": "user", "content": prompt}],
            }

            def _request():
                try:
                    resp = httpx.post(
                        f"{base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                        timeout=120.0,
                    )
                    resp.raise_for_status()
                    result_holder.append(resp.json())
                except Exception as e:
                    error_holder.append(e)
                finally:
                    stop_timer.set()

            thread = threading.Thread(target=_request, daemon=True)
            thread.start()

            retry_label = f" (attempt {attempt}/{max_retries})" if attempt > 1 else ""
            with console.status("") as status:
                while not stop_timer.is_set():
                    timer_str = _format_elapsed(time.monotonic() - t0)
                    status.update(f"[cyan]{status_msg}{retry_label}[/cyan] [dim]({timer_str})[/dim]")
                    stop_timer.wait(0.5)

            timer_str = _format_elapsed(time.monotonic() - t0)

            if error_holder:
                raise error_holder[0]

            data = result_holder[0]
            result = data["choices"][0]["message"]["content"].strip()
            console.print(f"[dim]LLM responded in {timer_str}[/dim]")
            return result
        except Exception as e:
            elapsed = time.monotonic() - t0
            mins, secs = divmod(int(elapsed), 60)
            timer_str = f"{mins}m {secs:02d}s" if mins else f"{elapsed:.1f}s"
            timer_str = _format_elapsed(time.monotonic() - t0)
            prompt_preview = prompt[:500].replace('\n', ' ') + ('...' if len(prompt) > 500 else '')
            if attempt < max_retries:
                console.print(f"[yellow]LLM request failed after {timer_str} (attempt {attempt}/{max_retries}):[/yellow] {e}")
                console.print(f"[dim]Retrying...[/dim]")
            else:
                console.print(f"[yellow]LLM request failed after {timer_str} (attempt {attempt}/{max_retries}):[/yellow] {e}")
                console.print(f"[dim]URL: {base_url}/chat/completions[/dim]")
                console.print(f"[dim]Model: {model} | Temperature: {payload['temperature']} | Prompt length: {len(prompt)} chars[/dim]")
                console.print(f"[dim]Prompt: {prompt_preview}[/dim]")
                return None


def _clean_llm_tag_response(raw: str) -> list[str]:
    """Parse LLM tag response, stripping common prefixes and formatting."""
    # Remove markdown backticks
    raw = raw.strip().strip("`")
    # Remove common prefixes the LLM might add
    raw = re.sub(r"^(?:Final\s*List|Tags|Suggested\s*Tags|Result|Here\s*are.*?tags)\s*:\s*", "", raw, flags=re.IGNORECASE)
    # Remove surrounding brackets/quotes
    raw = raw.strip("[]\"'")
    # Split and clean
    return [t.strip().strip("\"'").lower() for t in raw.split(",") if t.strip().strip("\"'")]


def _llm_max_chars() -> int:
    """Max chars for LLM prompt content. Configurable via LLM_MAX_CHARS env var."""
    return int(os.environ.get("LLM_MAX_CHARS", "12000"))


def suggest_tags_with_llm(title: str, description: str, text_snippet: str, existing_tags: list[str]) -> list[str]:
    """Use an LLM to suggest tags based on page content."""
    tags_list = ", ".join(sorted(ALLOWED_TAGS))
    max_chars = _llm_max_chars()
    prompt = f"""Pick 1-4 single-word lowercase tags that DIRECTLY describe this page's topics.

Prefer these well-known tags when they fit (but you may use others if needed):
{tags_list}

STRICT RULES:
- ONLY pick tags the page is SPECIFICALLY about — not loosely related
- If unsure about a tag, DO NOT include it
- 1-2 tags is perfectly fine — do NOT pad with extra tags
- Tags must be single lowercase words, no hyphens
- A browser page gets "web", NOT "containers" or "golang"
- A VMware page gets "vmware", NOT "kubernetes" or "docker"

Title: {title}
Description: {description}

Page content:
{text_snippet[:max_chars]}

Return ONLY a comma-separated list. Nothing else."""

    raw = _llm_chat(prompt, "Suggesting tags...")
    if not raw:
        return []
    tags = _clean_llm_tag_response(raw)[:6]
    console.print(f"[green]LLM suggested tags:[/green] {', '.join(tags)}")
    return tags



def fetch_metadata(url: str) -> dict:
    """Fetch URL and extract title, description, tags."""
    # Twitter/X-specific: use oEmbed API (site blocks scrapers)
    if _is_twitter_url(url):
        with console.status(f"Fetching X post [cyan]{url}[/cyan]..."):
            tw = _fetch_twitter_metadata(url)
        if tw:
            existing_tags = get_existing_tags()
            tags = suggest_tags_with_llm(tw["title"], tw["description"], tw["description"], existing_tags)
            return {"title": tw["title"], "description": tw["description"], "tags": tags, "_soup": None}
        console.print("[yellow]Could not fetch X metadata, falling back to generic fetch.[/yellow]")

    # YouTube-specific: use oEmbed + scrape for accurate video metadata
    if _is_youtube_url(url):
        with console.status(f"Fetching YouTube video [cyan]{url}[/cyan]..."):
            yt = _fetch_youtube_metadata(url)
        if yt:
            soup = yt.get("_soup")
            page_text = soup.get_text(separator=" ", strip=True) if soup else ""
            existing_tags = get_existing_tags()
            tags = suggest_tags_with_llm(yt["title"], yt["description"], page_text, existing_tags)
            return {"title": yt["title"], "description": yt["description"], "tags": tags, "_soup": soup}
        console.print("[yellow]Could not fetch YouTube metadata, falling back to generic fetch.[/yellow]")

    with console.status(f"Fetching [cyan]{url}[/cyan]..."):
        try:
            resp = httpx.get(url, follow_redirects=True, timeout=10.0, headers=HTTP_HEADERS)
            resp.raise_for_status()
        except httpx.TimeoutException:
            console.print(f"[yellow]Timed out fetching {url}[/yellow]")
            console.print("The site took too long to respond. You can enter metadata manually.\n")
            return {"title": "", "description": "", "tags": [], "_soup": None}
        except httpx.HTTPStatusError as e:
            code = e.response.status_code
            reasons = {
                403: "The site is blocking automated requests (common with Cloudflare-protected sites like Medium).",
                404: "The page was not found — check if the URL is correct.",
                429: "Too many requests — the site is rate-limiting. Try again later.",
                451: "The content is unavailable for legal reasons.",
                500: "The site is experiencing a server error.",
                502: "Bad gateway — the site's server is unreachable.",
                503: "The site is temporarily unavailable.",
            }
            reason = reasons.get(code, f"The server returned an error.")
            console.print(f"[yellow]HTTP {code} fetching {url}[/yellow]")
            console.print(f"{reason} You can enter metadata manually.\n")
            return {"title": "", "description": "", "tags": [], "_soup": None}
        except httpx.HTTPError as e:
            console.print(f"[yellow]Failed to fetch {url}:[/yellow] {e}")
            console.print("You can enter metadata manually.\n")
            return {"title": "", "description": "", "tags": [], "_soup": None}

    soup = BeautifulSoup(resp.text, "html.parser")

    # Detect Cloudflare challenge pages
    title_tag = soup.find("title")
    if title_tag and title_tag.string and "just a moment" in title_tag.string.lower():
        console.print(f"[yellow]Cloudflare challenge detected for {url}[/yellow]")
        console.print("The site is blocking automated access. You can enter metadata manually.\n")
        return {"title": "", "description": "", "tags": [], "_soup": None}

    # Title
    title = ""
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"]
    elif soup.title and soup.title.string:
        title = soup.title.string.strip()
    elif soup.h1:
        title = soup.h1.get_text(strip=True)

    # Description
    description = ""
    og_desc = soup.find("meta", property="og:description")
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if og_desc and og_desc.get("content"):
        description = og_desc["content"]
    elif meta_desc and meta_desc.get("content"):
        description = meta_desc["content"]
    else:
        first_p = soup.find("p")
        if first_p:
            description = first_p.get_text(strip=True)[:200]

    # Extract page text for analysis (capped — LLM prompt only uses 8000 chars)
    page_text = soup.get_text(separator=" ", strip=True)
    # Gather existing tags for consistency
    existing_tags = get_existing_tags()

    # Tags: always use LLM for consistent tagging
    tags = suggest_tags_with_llm(title, description, page_text, existing_tags)

    return {"title": title, "description": description, "tags": tags, "_soup": soup}


def _detect_email() -> str | None:
    """Try to detect git email."""
    try:
        result = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def detect_author() -> str | None:
    """Try to detect GitHub username."""
    # Try gh CLI (most reliable for GitHub username)
    try:
        result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return f"@{result.stdout.strip()}"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Try git config github.user
    try:
        result = subprocess.run(
            ["git", "config", "github.user"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return f"@{result.stdout.strip()}"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None


def require_author(author_flag: str | None) -> str:
    """Resolve author, guiding the user through setup if needed."""
    if author_flag:
        a = author_flag.strip()
        return a if a.startswith("@") else f"@{a}"

    detected = detect_author()
    if detected:
        return detected

    # Fall back to git user.name (better than prompting)
    try:
        result = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            name = result.stdout.strip()
            console.print(f"[yellow]Using git user.name [cyan]{name}[/cyan] as author.[/yellow]")
            console.print("[dim]Tip: set [cyan]git config --global github.user YOUR_USERNAME[/cyan] for your GitHub handle.[/dim]\n")
            return f"@{name}"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Nothing at all — prompt
    console.print(Panel(
        "[yellow]Could not detect your identity.[/yellow]\n\n"
        "Set it up (pick one):\n"
        "  [bold]1.[/bold] [cyan]git config --global github.user YOUR_USERNAME[/cyan]  (recommended, one-time)\n"
        "  [bold]2.[/bold] Install [cyan]gh[/cyan] CLI and run [cyan]gh auth login[/cyan]\n"
        "  [bold]3.[/bold] Pass [cyan]--author @username[/cyan] each time",
        title="Author Setup",
        border_style="yellow",
    ))
    username = Prompt.ask("Enter your GitHub username for now")
    username = username.strip().lstrip("@")
    if not username:
        raise typer.Exit(1)

    # Offer to save it
    if Confirm.ask(f"Save [cyan]@{username}[/cyan] to git config for future use?", default=True):
        subprocess.run(["git", "config", "--global", "github.user", username], check=True)
        console.print(f"[green]Saved:[/green] git config --global github.user {username}")

    return f"@{username}"


@link_app.command()
def add(
    url: str = typer.Argument(..., help="URL of the link to add"),
    week: int | None = typer.Option(None, "--week", "-w", help="Week number (default: current)"),
    year: int | None = typer.Option(None, "--year", "-y", help="Year (default: current)"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip duplicate check"),
    unattended: bool = typer.Option(False, "--unattended", "-u", help="Auto-accept all metadata, no prompts"),
    use_link_date: bool = typer.Option(False, "--use-link-date", "-d", help="Use the link's publication date instead of today"),
    screenshot: str | None = typer.Option(None, "--screenshot", "-s", help="Path to a screenshot image file"),
) -> None:
    """Add a new link to the campfire collection."""
    # Determine year/week
    default_year, default_week = current_iso_week()
    year = year or default_year
    week = week or default_week

    # Duplicate check
    if not force:
        dup = find_duplicate_url(url)
        if dup:
            console.print(Panel(
                f"[yellow]Duplicate found![/yellow]\n"
                f"URL already exists at: [cyan]{dup.relative_to(content_dir())}[/cyan]\n"
                f"Use [bold]--force[/bold] to add anyway.",
                title="Duplicate Link",
                border_style="yellow",
            ))
            raise typer.Exit(1)

    # Fetch metadata
    meta = fetch_metadata(url)

    # Display extracted data
    console.print(f"[bold]Title:[/bold] {meta['title']}")
    console.print(f"[bold]Description:[/bold] {meta['description'][:200]}{'...' if len(meta['description']) > 200 else ''}" if meta['description'] else "[bold]Description:[/bold] (none)")
    console.print(f"[bold]Tags:[/bold] {', '.join(meta['tags']) if meta['tags'] else '(none)'}")

    if unattended:
        title = meta["title"]
        description = meta["description"]
        tags = meta["tags"]
    else:
        title = Prompt.ask("Title", default=meta["title"])
        description = Prompt.ask("Description", default=meta["description"])
        tags_str = Prompt.ask("Tags (comma-separated)", default=", ".join(meta["tags"]))
        tags = [t.strip().lower() for t in tags_str.split(",") if t.strip()]

    # Generate slug and write file
    slug = slugify(title)

    link_date = datetime.date.today()
    if use_link_date:
        pub_date = _extract_date_from_url(url)
        if not pub_date and _is_twitter_url(url):
            tw = _fetch_twitter_metadata(url)
            if tw and tw.get("date"):
                pub_date = tw["date"]
        if not pub_date:
            with console.status(f"Fetching publication date for [cyan]{url}[/cyan]..."):
                pub_date = _fetch_published_date(url)
        if pub_date:
            link_date = pub_date
            pub_year, pub_week, _ = pub_date.isocalendar()
            year = pub_year
            week = pub_week
            console.print(f"[green]Using link date:[/green] {pub_date} ({year}/w{week:02d})")
        else:
            console.print("[yellow]Could not detect link date, using today.[/yellow]")

    # Re-ensure week dir in case date changed it
    week_dir = ensure_week_dir(year, week)
    file_path = week_dir / f"{slug}.md"

    fm = {
        "title": title,
        "url_link": url,
        "tags": tags,
        "description": description,
        "date": link_date.isoformat(),
        "year": year,
        "week": week,
        "comments": [],
    }
    write_front_matter(file_path, fm)

    console.print(f"\n[green]Link saved to:[/green] {file_path.relative_to(find_repo_root())}")

    # Preview image
    if screenshot:
        # User provided a screenshot file
        src = Path(screenshot).expanduser()
        if src.exists():
            out_dir = screenshots_dir()
            out_dir.mkdir(parents=True, exist_ok=True)
            dest = out_dir / f"{slug}.png"
            shutil.copy2(src, dest)
            console.print(f"[green]Screenshot copied:[/green] {dest.relative_to(find_repo_root())}")
        else:
            console.print(f"[yellow]Screenshot file not found:[/yellow] {screenshot}")
    else:
        capture_screenshot(url, slug, soup=meta.get("_soup"), title=title, description=description, tags=tags)

    # Rebuild
    run_hugo()


@link_app.command()
def comment(
    permalink: str | None = typer.Argument(None, help="Permalink path (e.g. 2026/w12/kubernetes-networking)"),
    text: str = typer.Argument(..., help="Comment text"),
    author: str | None = typer.Option(None, "--author", "-a", help="Author (@username)"),
    search: str | None = typer.Option(None, "--search", "-s", help="Search for a link instead of using permalink"),
) -> None:
    """Add a comment to a link."""
    cdir = content_dir()
    target: Path | None = None

    if permalink:
        # Direct permalink resolution
        candidate = cdir / f"{permalink}.md"
        if candidate.exists():
            target = candidate
        else:
            console.print(f"[red]File not found:[/red] {candidate}")
            raise typer.Exit(1)

    if search and not target:
        # Search mode
        query = search.lower()
        matches: list[tuple[Path, dict]] = []
        for md_file in cdir.rglob("*.md"):
            if md_file.name == "_index.md":
                continue
            try:
                fm, _ = parse_front_matter(md_file)
                if not fm.get("url_link"):
                    continue
                searchable = f"{fm.get('title', '')} {fm.get('url_link', '')} {' '.join(fm.get('tags', []))}".lower()
                if query in searchable:
                    matches.append((md_file, fm))
            except Exception:
                continue

        if not matches:
            console.print(f"[yellow]No links found matching:[/yellow] {search}")
            raise typer.Exit(1)

        if len(matches) == 1:
            target = matches[0][0]
        else:
            table = Table(title="Matching Links")
            table.add_column("#", style="cyan")
            table.add_column("Title")
            table.add_column("Path", style="dim")
            for i, (path, fm) in enumerate(matches, 1):
                table.add_row(str(i), fm.get("title", ""), str(path.relative_to(cdir)))
            console.print(table)
            choice = Prompt.ask("Select link number", default="1")
            idx = int(choice) - 1
            if 0 <= idx < len(matches):
                target = matches[idx][0]
            else:
                console.print("[red]Invalid selection[/red]")
                raise typer.Exit(1)

    if not target:
        console.print("[red]Provide a permalink or use --search[/red]")
        raise typer.Exit(1)

    # Resolve author
    author = require_author(author)

    # Add comment
    fm, body = parse_front_matter(target)
    comments = fm.get("comments") or []
    comment_entry: dict = {
        "author": author,
        "date": datetime.date.today().isoformat(),
        "text": text,
    }
    # Include email for Gravatar avatar if available
    email = _detect_email()
    if email:
        comment_entry["email"] = email
    comments.append(comment_entry)
    fm["comments"] = comments
    write_front_matter(target, fm, body)

    console.print(Panel(
        f"[green]Comment added![/green]\n"
        f"[bold]File:[/bold] {target.relative_to(find_repo_root())}\n"
        f"[bold]Author:[/bold] {author}\n"
        f"[bold]Text:[/bold] {text}",
        title="Comment Added",
        border_style="green",
    ))

    run_hugo()


@app.command(name="list")
def list_links(
    week: int | None = typer.Option(None, "--week", "-w", help="Week number (default: current)"),
    year: int | None = typer.Option(None, "--year", "-y", help="Year (default: current)"),
) -> None:
    """List links for a given week, year, or all."""
    default_year, default_week = current_iso_week()

    # If neither provided, show current week
    if year is None and week is None:
        year = default_year
        week = default_week

    # If only year provided, show all weeks for that year
    if year is not None and week is None:
        title = f"Links — {year}"
    elif year is None and week is not None:
        year = default_year
        title = f"Links — {year} / Week {week:02d}"
    else:
        title = f"Links — {year} / Week {week:02d}"

    table = Table(title=title)
    table.add_column("Permalink", style="dim", no_wrap=True)
    table.add_column("Title", style="bold")
    table.add_column("Tags", style="cyan", max_width=20)

    cdir = content_dir()
    year_dir = cdir / str(year)
    if not year_dir.exists():
        console.print(f"[yellow]No content found for {year}[/yellow]")
        raise typer.Exit(1)

    if week is not None:
        week_dirs = [year_dir / f"w{week:02d}"]
    else:
        week_dirs = sorted(d for d in year_dir.iterdir() if d.is_dir() and d.name.startswith("w"))

    for week_dir in week_dirs:
        if not week_dir.exists():
            continue
        for md_file in sorted(week_dir.glob("*.md")):
            if md_file.name == "_index.md":
                continue
            fm, _ = parse_front_matter(md_file)
            if not fm.get("url_link"):
                continue
            slug = md_file.stem
            w = fm.get("week", 0)
            y = fm.get("year", year)
            permalink = f"{y}/w{w:02d}/{slug}"
            tags = ", ".join(fm.get("tags", []))
            table.add_row(permalink, fm.get("title", ""), tags)

    console.print(table)




@link_app.command()
def tag(
    permalink: str = typer.Argument(..., help="Permalink of the link (e.g. 2026/w12/my-link)"),
    unattended: bool = typer.Option(False, "--unattended", "-u", help="Auto-accept suggested tags"),
) -> None:
    """Tag or retag a link. Fetches page content and suggests tags via LLM."""
    found = _find_link_by_permalink(permalink)
    if not found:
        console.print(f"[red]No link found for permalink:[/red] {permalink}")
        raise typer.Exit(1)

    md_file, fm, slug = found
    url = fm.get("url_link", "")
    current_tags = fm.get("tags", [])

    if current_tags:
        console.print(f"[bold]Current tags:[/bold] {', '.join(current_tags)}")

    # Fetch page content for LLM
    existing_tags = get_existing_tags()
    with console.status(f"Fetching [cyan]{url}[/cyan]..."):
        page_text = _fetch_page_text(url)

    title = fm.get("title", "")
    description = fm.get("description", "")
    suggested = suggest_tags_with_llm(title, description, page_text, existing_tags)

    if not suggested and not current_tags:
        console.print("[yellow]No tags suggested and no existing tags.[/yellow]")
        if unattended:
            return

    tags = suggested if suggested else current_tags

    if unattended:
        console.print(f"[green]Tags:[/green] {', '.join(tags)}")
    else:
        default = ", ".join(tags) if tags else ", ".join(current_tags)
        tags_str = Prompt.ask("Tags (comma-separated)", default=default)
        tags = [t.strip().lower() for t in tags_str.split(",") if t.strip()]
        # Filter to allowed tags
        tags = [t for t in tags if t in ALLOWED_TAGS]

    if tags == current_tags:
        console.print("[dim]Tags unchanged.[/dim]")
        return

    # Update frontmatter
    _, body = parse_front_matter(md_file)
    fm["tags"] = tags
    write_front_matter(md_file, fm, body)
    console.print(f"[green]Updated tags:[/green] {', '.join(tags)}")
    run_hugo()


@link_app.command()
def delete(
    permalink: str = typer.Option(..., "--permalink", "-p", help="Permalink of the link (e.g. 2026/w12/my-link)"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
) -> None:
    """Delete a link and its screenshot by permalink."""
    sdir = screenshots_dir()

    found = _find_link_by_permalink(permalink)
    if not found:
        console.print(f"[red]No link found for permalink:[/red] {permalink}")
        raise typer.Exit(1)

    md_file, fm, slug = found
    console.print(f"[bold]Title:[/bold] {fm.get('title', '')}")
    console.print(f"[bold]URL:[/bold] {fm.get('url_link', '')}")
    console.print(f"[bold]File:[/bold] {md_file.relative_to(find_repo_root())}")

    if not force:
        if not Confirm.ask("\n[red]Delete this link?[/red]"):
            console.print("Aborted.")
            return

    md_file.unlink()
    console.print(f"[green]Deleted:[/green] {md_file.relative_to(find_repo_root())}")

    # Remove screenshot and generated marker
    for ext in (".png", ".generated"):
        f = sdir / f"{slug}{ext}"
        if f.exists():
            f.unlink()
            console.print(f"[green]Deleted:[/green] {f.relative_to(find_repo_root())}")

    # Clean up empty week directory
    week_dir = md_file.parent
    remaining = [f for f in week_dir.iterdir() if f.is_file() and f.name != "_index.md"]
    if not remaining:
        shutil.rmtree(week_dir, ignore_errors=True)
        console.print(f"[dim]Removed empty week directory[/dim]")

    run_hugo()


@link_app.command(name="screenshot")
def screenshot_cmd(
    permalink: str = typer.Argument(..., help="Permalink of the link (e.g. 2026/w12/my-link)"),
) -> None:
    """Capture or re-capture the screenshot for a link."""
    found = _find_link_by_permalink(permalink)
    if not found:
        console.print(f"[red]No link found for permalink:[/red] {permalink}")
        raise typer.Exit(1)

    md_file, fm, slug = found
    out_dir = screenshots_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Remove existing screenshot and marker
    for ext in (".png", ".generated"):
        (out_dir / f"{slug}{ext}").unlink(missing_ok=True)

    url = fm["url_link"]
    if capture_screenshot(url, slug, title=fm.get("title", ""), description=fm.get("description", ""), tags=fm.get("tags", [])):
        console.print(f"[green]Done.[/green]")
    else:
        console.print(f"[yellow]Screenshot capture failed.[/yellow]")


@site_app.command(name="wipe")
def wipe(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
) -> None:
    """DESTRUCTIVE: Wipe ALL CONTENT."""
    cdir = content_dir()
    sdir = screenshots_dir()

    # Count what will be removed
    link_files = [f for f in cdir.rglob("*.md") if f.name != "_index.md" and f.parent != cdir]
    screenshots = list(sdir.glob("*.png")) if sdir.exists() else []
    week_dirs = [d for d in cdir.rglob("*") if d.is_dir() and re.match(r"w\d{2}$", d.name)]
    year_dirs = [d for d in cdir.iterdir() if d.is_dir() and re.match(r"\d{4}$", d.name)]

    if not link_files and not screenshots:
        console.print("[yellow]Nothing to clean.[/yellow]")
        return

    console.print(f"This will remove:")
    console.print(f"  [bold]{len(link_files)}[/bold] link files")
    console.print(f"  [bold]{len(screenshots)}[/bold] screenshots")
    console.print(f"  [bold]{len(week_dirs)}[/bold] week directories")
    console.print(f"  [bold]{len(year_dirs)}[/bold] year directories")

    if not force:
        if not Confirm.ask("\n[red]Are you sure?[/red]"):
            console.print("Aborted.")
            return

    # Remove link files
    for f in link_files:
        f.unlink()

    # Remove screenshots
    for f in screenshots:
        f.unlink()

    # Remove week directories (now empty)
    for d in sorted(week_dirs, reverse=True):
        shutil.rmtree(d, ignore_errors=True)

    # Remove year directories (now empty except maybe _index.md)
    for d in sorted(year_dirs, reverse=True):
        shutil.rmtree(d, ignore_errors=True)

    console.print(f"\n[green]Cleaned:[/green] {len(link_files)} links, {len(screenshots)} screenshots removed.")

    # Rebuild
    run_hugo()


@site_app.command()
def rebuild() -> None:
    """Rebuild the Hugo site (clean + regenerate public/)."""
    if not run_hugo():
        raise typer.Exit(1)


@site_app.command()
def backup(
    output: str = typer.Option("campfire-backup.md", "--output", "-o", help="Output markdown file path"),
) -> None:
    """Backup all links to a markdown file, organized by week."""
    cdir = content_dir()

    # Collect all links grouped by year/week
    weeks: dict[tuple[int, int], list[dict]] = {}
    for md_file in sorted(cdir.rglob("*.md")):
        if md_file.name == "_index.md":
            continue
        try:
            fm, _ = parse_front_matter(md_file)
        except Exception:
            continue
        if not fm.get("url_link"):
            continue
        key = (fm.get("year", 0), fm.get("week", 0))
        weeks.setdefault(key, []).append(fm)

    if not weeks:
        console.print("[yellow]No links found to backup.[/yellow]")
        return

    # Write markdown file
    out_path = Path(output)
    lines: list[str] = []
    lines.append("# Campfire Backup")
    lines.append("")
    lines.append(f"Generated: {datetime.date.today().isoformat()}")
    lines.append("")

    total = 0
    for (y, w) in sorted(weeks.keys()):
        lines.append(f"## {y}/w{w:02d}")
        lines.append("")
        for link in sorted(weeks[(y, w)], key=lambda l: l.get("date", "")):
            url = link["url_link"]
            title = link.get("title", url)
            lines.append(f"- [{title}]({url})")
            total += 1
        lines.append("")

    out_path.write_text("\n".join(lines))
    console.print(f"[green]Backup saved:[/green] {out_path} ({total} links across {len(weeks)} weeks)")


@site_app.command()
def restore(
    backup_file: str = typer.Argument(..., help="Path to the backup markdown file"),
    unattended: bool = typer.Option(False, "--unattended", "-u", help="Run without prompts, auto-accept all metadata"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip duplicate check"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be restored without writing files"),
) -> None:
    """Restore links from a backup markdown file.

    Re-fetches title, description, and tags from each URL.
    Use --unattended to skip all prompts.
    """
    backup_path = Path(backup_file)
    if not backup_path.exists():
        console.print(f"[red]File not found:[/red] {backup_file}")
        raise typer.Exit(1)

    text = backup_path.read_text()

    # Parse the markdown: look for ## year/wNN headers and - [title](url) links
    current_year: int | None = None
    current_week: int | None = None
    entries: list[tuple[int, int, str]] = []

    week_re = re.compile(r"^##\s+(\d{4})/w(\d{1,2})\s*$")
    link_re = re.compile(r"^-\s+\[.*?\]\((https?://\S+)\)\s*$")

    for line in text.splitlines():
        week_match = week_re.match(line)
        if week_match:
            current_year = int(week_match.group(1))
            current_week = int(week_match.group(2))
            continue
        link_match = link_re.match(line)
        if link_match and current_year and current_week:
            entries.append((current_year, current_week, link_match.group(1)))

    if not entries:
        console.print("[yellow]No links found in backup file.[/yellow]")
        return

    console.print(f"Found [bold]{len(entries)}[/bold] links to restore.\n")

    if dry_run:
        for year, week, url in entries:
            console.print(f"  [dim]{year}/w{week:02d}[/dim] {url}")
        console.print(f"\n[yellow]Dry run:[/yellow] no files written.")
        return

    success = 0
    skipped = 0
    failed = 0

    for i, (year, week, url) in enumerate(entries, 1):
        console.print(f"\n[bold][{i}/{len(entries)}][/bold] {url}")
        console.print(f"  → {year}/w{week:02d}")

        # Duplicate check
        if not force:
            dup = find_duplicate_url(url)
            if dup:
                console.print(f"  [yellow]Skipped (duplicate):[/yellow] {dup.relative_to(content_dir())}")
                skipped += 1
                continue

        # Fetch metadata
        try:
            meta = fetch_metadata(url)
        except Exception as e:
            console.print(f"  [red]Failed to fetch metadata:[/red] {e}")
            failed += 1
            continue

        title = meta.get("title", "")
        description = meta.get("description", "")
        tags = meta.get("tags", [])

        # Always show what we got
        console.print(f"  [bold]Title:[/bold] {title or '(none)'}")
        console.print(f"  [bold]Description:[/bold] {description[:100]}{'...' if len(description) > 100 else ''}" if description else "  [bold]Description:[/bold] (none)")
        console.print(f"  [bold]Tags:[/bold] {', '.join(tags) if tags else '(none)'}")

        if not unattended:
            # Show metadata and prompt for edits
            console.print(Panel(
                f"[bold]Title:[/bold] {title}\n"
                f"[bold]Description:[/bold] {description[:200]}{'...' if len(description) > 200 else ''}\n"
                f"[bold]Tags:[/bold] {', '.join(tags) if tags else '(none)'}",
                title="Extracted Metadata",
                border_style="blue",
            ))
            title = Prompt.ask("Title", default=title)
            description = Prompt.ask("Description", default=description)
            tags_str = Prompt.ask("Tags (comma-separated)", default=", ".join(tags))
            tags = [t.strip().lower() for t in tags_str.split(",") if t.strip()]

        if not title:
            title = url
            console.print(f"  [yellow]No title found, using URL as title[/yellow]")

        # Write file
        slug = slugify(title)
        week_dir = ensure_week_dir(year, week)
        file_path = week_dir / f"{slug}.md"

        today = datetime.date.today().isoformat()
        fm = {
            "title": title,
            "url_link": url,
            "tags": tags,
            "description": description,
            "date": today,
            "year": year,
            "week": week,
            "comments": [],
        }
        write_front_matter(file_path, fm)
        console.print(f"  [green]Saved:[/green] {file_path.relative_to(find_repo_root())}")

        # Capture screenshot
        capture_screenshot(url, slug, soup=meta.get("_soup"), title=title, description=description, tags=tags)

        success += 1

    console.print(f"\n[green]Restore complete:[/green] {success} added, {skipped} skipped, {failed} failed")

    # Rebuild
    if success > 0:
        run_hugo()


def _extract_date_from_url(url: str) -> datetime.date | None:
    """Try to extract a publication date from the URL path."""
    # Match patterns like /2026-03-16- or /2026/03/16/ or /2026/03/09/
    patterns = [
        r"/(\d{4})-(\d{2})-(\d{2})",       # /2026-03-16-slug
        r"/(\d{4})/(\d{2})/(\d{2})/",       # /2026/03/16/slug
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            try:
                return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                continue
    return None


def _parse_date_string(s: str) -> datetime.date | None:
    """Try to parse a date from various formats."""
    s = s.strip()
    # ISO format: 2025-04-25 or 2025-04-25T02:24:11+00:00
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    # US format: January 14, 2020 / Jan 14, 2020
    m = re.search(r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s*(\d{4})", s, re.IGNORECASE)
    if m:
        month = _MONTHS.get(m.group(1)[:3].lower())
        if month:
            try:
                return datetime.date(int(m.group(3)), month, int(m.group(2)))
            except ValueError:
                pass
    # Format: 14 Jan 2020
    m = re.search(r"(\d{1,2})\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?),?\s*(\d{4})", s, re.IGNORECASE)
    if m:
        month = _MONTHS.get(m.group(2)[:3].lower())
        if month:
            try:
                return datetime.date(int(m.group(3)), month, int(m.group(1)))
            except ValueError:
                pass
    return None


def _fetch_published_date(url: str) -> datetime.date | None:
    """Try to get the publication date from page content using multiple strategies."""
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=10.0, headers=HTTP_HEADERS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # 1. Meta tags (most reliable)
        for prop in ("article:published_time", "og:article:published_time",
                      "datePublished", "date", "DC.date.issued", "publish_date"):
            tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop}) or soup.find("meta", attrs={"itemprop": prop})
            if tag and tag.get("content"):
                d = _parse_date_string(tag["content"])
                if d:
                    return d

        # 2. JSON-LD structured data
        for script in soup.find_all("script", type="application/ld+json"):
            text = script.string or ""
            for field in ("datePublished", "dateCreated"):
                m = re.search(rf'"{field}"\s*:\s*"([^"]+)"', text)
                if m:
                    d = _parse_date_string(m.group(1))
                    if d:
                        return d

        # 3. <time> elements with datetime attribute
        for time_el in soup.find_all("time", attrs={"datetime": True}):
            d = _parse_date_string(time_el["datetime"])
            if d:
                return d

        # 4. <time> elements with text content
        for time_el in soup.find_all("time"):
            d = _parse_date_string(time_el.get_text(strip=True))
            if d:
                return d

        # 5. Common date CSS classes
        for cls_pattern in ("date", "post-date", "published", "entry-date", "pubdate",
                            "post-meta", "article-date", "publish-date", "created"):
            el = soup.find(class_=re.compile(cls_pattern, re.IGNORECASE))
            if el:
                d = _parse_date_string(el.get_text(strip=True))
                if d:
                    return d

    except Exception:
        pass
    return None


@link_app.command()
def redate(
    permalink: str = typer.Argument(..., help="Permalink of the link (e.g. 2026/w12/my-link)"),
    fetch: bool = typer.Option(False, "--fetch", help="Fetch page to find published date"),
) -> None:
    """Move a link to the correct year/week based on its publication date."""
    found = _find_link_by_permalink(permalink)
    if not found:
        console.print(f"[red]No link found for permalink:[/red] {permalink}")
        raise typer.Exit(1)

    md_file, fm, slug = found
    url = fm.get("url_link", "")

    # Try to find the real date
    pub_date = _extract_date_from_url(url)
    if not pub_date and _is_twitter_url(url):
        tw = _fetch_twitter_metadata(url)
        if tw and tw.get("date"):
            pub_date = tw["date"]
    if not pub_date and fetch:
        with console.status(f"Fetching date for [cyan]{url}[/cyan]..."):
            pub_date = _fetch_published_date(url)

    if not pub_date:
        console.print(f"[yellow]Could not detect publication date for this link.[/yellow]")
        raise typer.Exit(1)

    target_year, target_week, _ = pub_date.isocalendar()
    current_year = fm.get("year", 0)
    current_week = fm.get("week", 0)

    if target_year == current_year and target_week == current_week:
        console.print(f"[green]Already in the correct week:[/green] {target_year}/w{target_week:02d}")
        return

    console.print(f"  {current_year}/w{current_week:02d} → {target_year}/w{target_week:02d}  [dim]({pub_date})[/dim]")

    # Update frontmatter
    _, body = parse_front_matter(md_file)
    fm["date"] = pub_date.isoformat()
    fm["year"] = target_year
    fm["week"] = target_week

    # Write to new location
    target_dir = ensure_week_dir(target_year, target_week)
    target_file = target_dir / md_file.name
    write_front_matter(target_file, fm, body)

    # Remove old file
    md_file.unlink()

    # Clean up empty week directory
    old_week_dir = md_file.parent
    if old_week_dir.is_dir() and not any(f.name != "_index.md" for f in old_week_dir.iterdir() if f.is_file()):
        shutil.rmtree(old_week_dir, ignore_errors=True)

    new_permalink = f"{target_year}/w{target_week:02d}/{slug}"
    console.print(f"[green]Moved to:[/green] {new_permalink}")
    run_hugo()


@site_app.command()
def retag(
    year: int = typer.Option(..., "--year", "-y", help="Year to retag"),
    week: int | None = typer.Option(None, "--week", "-w", help="Week number (omit for entire year)"),
) -> None:
    """Retag all links for a year or specific week using the LLM."""
    targets = list(_iter_link_files(year=year, week=week))
    if not targets:
        console.print(f"[yellow]No links found for {year}{f'/w{week:02d}' if week else ''}[/yellow]")
        return

    console.print(f"Retagging [bold]{len(targets)}[/bold] links for {year}{f'/w{week:02d}' if week else ''}...\n")

    updated = 0
    for i, (md_file, fm, body) in enumerate(targets, 1):
        url = fm.get("url_link", "")
        title = fm.get("title", "")
        old_tags = fm.get("tags", [])
        slug = md_file.stem
        w = fm.get("week", 0)
        permalink = f"{year}/w{w:02d}/{slug}"

        console.print(f"[bold][{i}/{len(targets)}][/bold] {permalink}")
        console.print(f"  [dim]{title}[/dim]")
        if old_tags:
            console.print(f"  [dim]Current: {', '.join(old_tags)}[/dim]")

        # Fetch page content
        description = fm.get("description", "")
        page_text = _fetch_page_text(url)
        existing_tags = get_existing_tags()
        new_tags = suggest_tags_with_llm(title, description, page_text, existing_tags)

        if not new_tags:
            console.print(f"  [yellow]No tags suggested, keeping current[/yellow]")
            continue

        if new_tags == old_tags:
            console.print(f"  [dim]Tags unchanged[/dim]")
            continue

        fm["tags"] = new_tags
        write_front_matter(md_file, fm, body)
        updated += 1

    console.print(f"\n[green]Done:[/green] {updated}/{len(targets)} links retagged.")
    if updated > 0:
        run_hugo()


@site_app.command(name="redate")
def redate_bulk(
    year: int = typer.Option(..., "--year", "-y", help="Year to redate"),
    week: int | None = typer.Option(None, "--week", "-w", help="Week number (omit for entire year)"),
    fetch: bool = typer.Option(False, "--fetch", help="Fetch pages to find published dates (slower)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would change without moving files"),
) -> None:
    """Redate all links for a year or specific week based on publication dates."""
    targets = list(_iter_link_files(year=year, week=week))
    if not targets:
        console.print(f"[yellow]No links found for {year}{f'/w{week:02d}' if week else ''}[/yellow]")
        return

    console.print(f"Checking dates for [bold]{len(targets)}[/bold] links...\n")

    moves: list[tuple[Path, dict, str, datetime.date, int, int]] = []
    for md_file, fm, body in targets:
        url = fm.get("url_link", "")
        current_year = fm.get("year", 0)
        current_week = fm.get("week", 0)

        pub_date = _extract_date_from_url(url)
        if not pub_date and _is_twitter_url(url):
            tw = _fetch_twitter_metadata(url)
            if tw and tw.get("date"):
                pub_date = tw["date"]
        if not pub_date and fetch:
            with console.status(f"Fetching date for [cyan]{url}[/cyan]..."):
                pub_date = _fetch_published_date(url)

        if not pub_date:
            continue

        target_year, target_week, _ = pub_date.isocalendar()
        if target_year == current_year and target_week == current_week:
            continue

        moves.append((md_file, fm, body, pub_date, target_year, target_week))

    if not moves:
        console.print("[green]All links are in the correct week.[/green]")
        return

    console.print(f"Found [bold]{len(moves)}[/bold] links to move:\n")
    for md_file, fm, _, pub_date, target_year, target_week in moves:
        current = f"{fm.get('year')}/w{fm.get('week', 0):02d}"
        target = f"{target_year}/w{target_week:02d}"
        console.print(f"  {current} → {target}  [dim]({pub_date})[/dim]  {fm.get('title', md_file.name)}")

    if dry_run:
        console.print(f"\n[yellow]Dry run:[/yellow] no files moved.")
        return

    moved = 0
    for md_file, fm, body, pub_date, target_year, target_week in moves:
        slug = md_file.stem
        fm["date"] = pub_date.isoformat()
        fm["year"] = target_year
        fm["week"] = target_week

        target_dir = ensure_week_dir(target_year, target_week)
        target_file = target_dir / md_file.name
        write_front_matter(target_file, fm, body)
        md_file.unlink()
        moved += 1

    # Clean up empty week directories
    cdir = content_dir()
    for d in sorted(cdir.rglob("w*"), reverse=True):
        if d.is_dir() and re.match(r"w\d{2}$", d.name) and not any(f.name != "_index.md" for f in d.iterdir() if f.is_file()):
            shutil.rmtree(d, ignore_errors=True)

    console.print(f"\n[green]Moved {moved} links.[/green]")
    run_hugo()


if __name__ == "__main__":
    app()
