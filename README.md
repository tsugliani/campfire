# Campfire

Weekly curated links, shared around the tech campfire.

A monorepo containing a [Hugo](https://gohugo.io/) static website and a Python CLI tool for collecting and sharing interesting links each week. The site uses the Catppuccin Mocha color scheme and deploys automatically to GitHub Pages.

## Quick Start

### Prerequisites

- [Hugo](https://gohugo.io/installation/) (extended edition)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Playwright](https://playwright.dev/python/) (optional, for browser screenshots)
- An LLM endpoint for tag suggestions (Ollama, LM Studio, or any OpenAI-compatible API)

### Setup

```bash
git clone https://github.com/tsugliani/campfire.git
cd campfire

# Optional: configure LLM for tag suggestions
cp .env.example .env
# Edit .env — or just run Ollama/LM Studio locally (auto-detected)

# Install the CLI
cd cli
uv sync
```

### Run the site locally

```bash
# From the repo root
hugo server
```

## CLI Commands

All commands run from the `cli/` directory with `uv run campfire-cli <command>`.

```
campfire-cli
├── list [-w N] [-y N]                     # list links (current week, specific week, or whole year)
│
├── link add <url> [-u] [-d] [-f]          # add a link (-u unattended, -d use link date, -f force)
├── link delete -p <permalink> [-f]        # delete a link by permalink
├── link comment <permalink> "text"        # add a comment to a link
├── link tag <permalink> [-u]              # tag/retag a link (-u auto-accept LLM tags)
├── link screenshot <permalink>            # capture or re-capture a screenshot
├── link redate <permalink> [--fetch]      # fix date from publication date
│
├── site rebuild                           # rebuild the Hugo site
├── site backup [-o file]                  # export all links to a markdown file
├── site restore <file> [-u] [-f]          # import links from a backup file
├── site retag -y <year> [-w N]            # retag all links for a year/week via LLM
├── site redate -y <year> [-w N] [--fetch] # redate all links for a year/week
└── site wipe [-f]                         # DESTRUCTIVE: wipe ALL CONTENT
```

### Examples

```bash
# Add a link (interactive)
campfire-cli link add "https://example.com/article"

# Add a link unattended with auto-detected publication date
campfire-cli link add "https://example.com/article" -u -d

# List current week (shows permalinks for use with other commands)
campfire-cli list

# List all links for 2025
campfire-cli list -y 2025

# Tag/retag a specific link
campfire-cli link tag 2026/w12/my-link
campfire-cli link tag 2026/w12/my-link -u    # auto-accept LLM tags

# Re-capture a screenshot
campfire-cli link screenshot 2026/w12/my-link

# Fix a link's date by fetching its page
campfire-cli link redate 2026/w13/my-link --fetch

# Delete a link
campfire-cli link delete -p 2026/w12/my-link

# Bulk retag all links for a year
campfire-cli site retag -y 2025

# Bulk redate a specific week
campfire-cli site redate -y 2026 -w 13 --fetch

# Backup, wipe, and restore
campfire-cli site backup -o my-backup.md
campfire-cli site wipe --force
campfire-cli site restore my-backup.md --unattended --force
campfire-cli site rebuild
```

### Tag categories

Tags are suggested by the LLM from a preferred list of broad IT categories, but the LLM may use other relevant tags when needed:

`ai` `api` `automation` `career` `cli` `cloud` `containers` `database` `desktop` `development` `devops` `docker` `git` `golang` `hardware` `homelab` `infrastructure` `kubernetes` `linux` `macos` `monitoring` `networking` `opensource` `performance` `python` `rust` `security` `ssh` `storage` `terminal` `testing` `troubleshooting` `ux` `virtualization` `vmware` `web` `windows`

## LLM Configuration

The CLI uses an LLM for tag suggestions when adding or retagging links. It supports any OpenAI-compatible API.

```bash
cp .env.example .env
# Edit .env — uncomment the provider you want to use
```

**Local (auto-detected, no config needed):**
- **Ollama** — just run `ollama serve`, detected on `localhost:11434`
- **LM Studio** — start the local server, detected on `localhost:1234`

**Cloud (any OpenAI-compatible endpoint):**
- Set `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`

The CLI works without any LLM configured — tag suggestions are skipped and you set tags manually.

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_BASE_URL` | API base URL | Auto-detect local Ollama/LM Studio |
| `LLM_API_KEY` | API key | `no-key` (for local servers) |
| `LLM_MODEL` | Model name | Auto-detect from server |
| `LLM_MAX_CHARS` | Max page content chars sent to LLM | `12000` |

> **Tip:** `qwen2.5-72b-instruct` with a 32K context gives excellent tag suggestions. For smaller setups, `qwen2.5-14b-instruct` is a good balance of speed and accuracy. Set `LLM_MAX_CHARS=60000` for models with 32K+ context.

## Site Structure

| Page | URL | Description |
|------|-----|-------------|
| Homepage | `/` | Latest week's links |
| Archive | `/weeks/` | All weeks, newest first |
| Week | `/2026/w12/` | Links for a specific week |
| Link | `/2026/w12/my-link/` | Single link detail page |
| Tags | `/tags/` | All tags with counts |
| Tag | `/tags/kubernetes/` | Links with a specific tag |
| About | `/about/` | About page |
| RSS | `/index.xml` | RSS feed of all links |

## Content Format

Each link is a markdown file in `content/{year}/w{week}/`:

```yaml
---
title: "Kubernetes Networking Deep Dive"
url_link: "https://example.com/article"
tags: ["kubernetes", "devops", "networking"]
description: "A deep-dive into K8s networking internals."
date: 2026-03-18
year: 2026
week: 12
comments:
  - author: "@tsugliani"
    date: 2026-03-25
    text: "Excellent walkthrough of CNI plugins."
---
```

## Deployment

The `public/` directory is **not committed to the repository**. It is generated at build time by Hugo and is listed in `.gitignore`.

### GitHub Pages (automated)

Pushes to `main` trigger a GitHub Actions workflow (`.github/workflows/deploy.yml`) that:

1. Checks out the repo
2. Installs Hugo (extended edition)
3. Runs `hugo --minify` to generate the `public/` folder
4. Uploads `public/` as a GitHub Pages artifact
5. Deploys to GitHub Pages

The workflow uses `actions/upload-pages-artifact` and `actions/deploy-pages`. No `public/` folder needs to exist in the repo — it's built fresh on every push.

**Custom domain:** If you fork this project and use your own custom domain, update these two files:

- `static/CNAME` — replace `campfire.tsugliani.fr` with your domain (this gets copied to `public/` during build so GitHub Pages keeps the custom domain across deploys)
- `hugo.toml` — update `baseURL` to match your domain

### Local development

For local development, `hugo server` serves from memory. To generate a local build:

```bash
campfire-cli site rebuild    # or: hugo --cleanDestinationDir
```

## Contributing via PR

### Adding a link

1. Fork the repo and clone your fork
2. `cd cli && uv sync`
3. `uv run campfire-cli link add "https://your-link"`
4. Commit the new `.md` file and screenshot
5. Push and open a PR

### Adding a comment to an existing link

1. Fork & clone the repo
2. Find the link: `uv run campfire-cli list` or browse the site
3. Add your comment: `uv run campfire-cli link comment 2026/w12/my-link "Great article!"`
4. Commit & push the modified `.md` file
5. Open a PR

## Backup & Restore

```bash
# Export all links to a markdown file
campfire-cli site backup -o my-backup.md

# Wipe the site
campfire-cli site wipe --force

# Restore from backup (re-fetches metadata for each link)
campfire-cli site restore my-backup.md --unattended --force

# Fix dates and retag
campfire-cli site redate -y 2025 --fetch
campfire-cli site retag -y 2025
```

## License

MIT
