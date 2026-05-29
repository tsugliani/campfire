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
├── link add <url> [-u] [-d] [-f] [--no-build]  # add a link (--no-build skips Hugo)
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
├── site normalize-tags [--apply] [--drop-singletons]  # canonicalize tags (permalink-safe)
├── site suggest-aliases                   # LLM proposes TAG_ALIASES entries (review-only)
├── site wipe [-f]                         # DESTRUCTIVE: wipe all content
├── queue add <url>...  [-d]               # enqueue links instantly (no network/build)
├── queue list                             # show pending/done/failed jobs
├── queue process [-w N] [-y N] [--no-build] [--retry-failed]  # fetch all + ONE rebuild
├── queue review [--no-build]              # validate/fix processed links (title/desc/tags)
└── queue clear [--all]                    # drop done jobs (or everything)
```

Commands use Typer subgroups: `link_app` (single-link ops), `site_app` (site management), `queue_app` (batch queue), `app` (top-level list).

## Performance notes

- **Hugo rebuild is the dominant cost** of any mutation (~15s, scales with site size). `link add` rebuilds by default; use `--no-build`, or the **queue** (`queue process` rebuilds once for the whole batch) to amortize it.
- **Batch workflow**: `queue add <url>...` (instant) → `queue process` (fetch all + one rebuild, records each result's permalink + prints a summary table) → `queue review` (step through to validate/fix title/description/tags; editing the title renames the .md + screenshot files to keep the slug in sync — safe because the batch isn't indexed yet). Screenshot latency is irrelevant here since it's all batched.
- **`_scan_links()`** does a single cached disk walk + parse; `find_duplicate_url` and `get_existing_tags` both derive from it (no double scan per `add`).
- **`SCREENSHOT_SETTLE_MS`** env var tunes the Playwright settle wait (default 1200ms).
- The LLM tag call is intentionally *not* optimized for latency — it can take as long as it needs.

## Tag canonicalization

- **`TAG_ALIASES`** (in `main.py`, next to `ALLOWED_TAGS`) maps variants → canonical tags. It is the single place to maintain the vocabulary. Applied at write-time (via `suggest_tags_with_llm`) and in bulk by `site normalize-tags`.
- Automatic rules in `normalize_tag`: lowercase/trim, strip hyphens/underscores/spaces, and **depluralize only when the singular already exists in the corpus** (`_NEVER_SINGULARIZE` guards proper nouns like `https`, `kubernetes`, `windows`).
- **Permalink-safe**: `normalize-tags` rewrites *only* the `tags` field — it never moves/renames/re-dates files, so article URLs (`/{year}/w{week}/{slug}/`) are untouched. Tags are NOT part of article permalinks; they only generate `/tags/<tag>/` taxonomy pages.
- Monthly maintenance: run `site suggest-aliases` → review → paste into `TAG_ALIASES` → `site normalize-tags --apply`. `--drop-singletons` is the aggressive option (deletes rare tags rather than remapping them).

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
- `LLM_TIMEOUT` env var (seconds) overrides the request timeout. Resolution: `$LLM_TIMEOUT` if set, else the caller's `timeout` arg, else 120. `site suggest-aliases` passes 600 by default since clustering the whole vocabulary on a large local model can exceed 2 minutes.
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
