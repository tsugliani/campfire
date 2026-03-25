# CLAUDE.md

## Project overview

Campfire is a Hugo static website + Python CLI for curating weekly tech links. Links are stored as markdown files with YAML frontmatter, organized by year/week.

## Repository structure

```
campfire/
├── content/               # Hugo content (links organized by year/week)
│   ├── {year}/w{week}/    # Week directories with _index.md + link .md files
│   ├── about/             # About page
│   └── weeks/             # Archive page (_index.md with layout: weeks)
├── layouts/               # Hugo templates
│   └── partials/all-weeks.html  # Shared partial for collecting all week sections
├── static/
│   ├── css/style.css      # All styles (Catppuccin Mocha theme)
│   ├── js/                # Search (search.js) and card navigation (card-nav.js)
│   ├── images/            # Site images (campfire.png)
│   ├── screenshots/       # Link preview images (.png + .generated markers)
│   ├── favicon.svg        # Animated campfire favicon
│   └── CNAME              # Custom domain for GitHub Pages
├── cli/                   # Python CLI tool
│   ├── campfire_cli/main.py  # All CLI commands
│   └── pyproject.toml
├── hugo.toml              # Hugo configuration
├── public/                # Generated site (gitignored, built by CI)
└── .github/workflows/     # GitHub Actions deployment
```

## CLI structure

```
campfire-cli
├── list [-w N] [-y N]                     # list links (week, year, or current)
├── link add <url> [-u] [-d] [-f]          # add a link
├── link delete -p <permalink> [-f]        # delete a link
├── link comment <permalink> "text"        # comment on a link
├── link tag <permalink> [-u]              # tag/retag a link via LLM
├── link screenshot <permalink>            # capture/recapture screenshot
├── link redate <permalink> [--fetch]      # fix date from publication date
├── site rebuild                           # rebuild Hugo site
├── site backup [-o file]                  # export links to markdown
├── site restore <file> [-u] [-f]          # import from backup
├── site retag -y <year> [-w N]            # bulk retag via LLM
├── site redate -y <year> [-w N] [--fetch] # bulk redate from publication dates
└── site wipe [-f]                         # DESTRUCTIVE: wipe all content
```

Commands use Typer subgroups: `link_app` (single-link ops), `site_app` (site management), `app` (top-level list).

## Key conventions

- **Week format**: Always zero-padded 2 digits (w01, w12, w52)
- **Year/week separator**: Use `/` in display (e.g. "2026 / Week 12")
- **Slugs**: ASCII-only, accented chars transliterated (é→e, ü→u), non-Latin chars stripped
- **Tags**: `ALLOWED_TAGS` constant provides guidance but LLM may suggest others; no hard filter
- **Screenshots**: `.generated` marker files indicate fallback card images (hidden on detail pages, shown on list pages)
- **`public/` directory**: Gitignored. Built fresh by Hugo on CI. Never commit it.
- **`content/weeks/_index.md`**: Required for the archive page. Must not be deleted by wipe/redate commands.
- **Frontmatter parsing**: Uses regex `\n---\s*\n` to find closing `---` (not `split("---")` which breaks on URLs containing `---`)

## Platform-specific handlers

- **YouTube**: oEmbed API for title, page scrape for description (from `attributedDescription` in JS data), `i.ytimg.com` for thumbnails, timestamp links converted to `&t=` URLs (supports both `01:43 - Topic` and `01:43 Topic` formats)
- **X/Twitter**: fxtwitter API for metadata (title, description, article content, cover images, dates). Site blocks all scrapers.
- **Cloudflare-protected sites**: Detected by page title ("Just a moment"), falls through to generated card
- **Cookie banners**: Playwright dismisses known banners (OneTrust, CookieBot, Funding Choices, Blogspot, etc.) before screenshots

## LLM integration

- Tags suggested via any OpenAI-compatible LLM endpoint
- `ALLOWED_TAGS` is guidance in the prompt, not a hard filter
- `LLM_MAX_CHARS` env var controls page content cap (default 12000, increase for larger context models)
- Requests retry 3 times on failure, with timing and payload info on errors
- Temperature: 0.1 for deterministic tag suggestions
- Recommended: `qwen2.5-72b-instruct` for best accuracy, `qwen2.5-14b-instruct` for speed

## Hugo templates

- Templates use `partial "all-weeks.html"` to collect all week sections (not `.Site.Pages` which misses section pages)
- Week dates show Monday–Sunday range
- Descriptions use `replaceRE` for URL linking and newline handling, with `safeHTML` always last in the pipe
- Link cards clamp descriptions to 10 lines via CSS `-webkit-line-clamp`
- `enableAddComment` param in `hugo.toml` toggles the "Leave a comment" section

## Build and deploy

- Local: `campfire-cli site rebuild` or `hugo server`
- CI: `hugo --minify` → `actions/upload-pages-artifact` → `actions/deploy-pages`
- `run_hugo()` always uses `--cleanDestinationDir` to remove stale files from `public/`
