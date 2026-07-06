# Freecrawl

> Open-source web scraping API with anti-bot bypass. Drop-in Firecrawl alternative.
> No API keys, no credits, no limits.

## Features

- **Anti-Bot Engine Chain**: httpx (fast) -> Flaresolverr (Cloudflare) -> Patchright (DataDome, Akamai, etc.)
- **Auto-Escalation**: Automatically tries faster engines first, falls back to anti-bot browsers
- **Multiple Output Formats**: Markdown, HTML, text, JSON-LD, links, images
- **BFS Site Crawler**: Discover pages via links + sitemap.xml
- **CSS Extraction**: Extract structured data with CSS selectors
- **JS Actions**: Click, scroll, type, evaluate before extracting
- **Screenshots**: Full-page screenshots
- **Proxy Support**: Single proxy or rotation pool
- **Caching**: Avoid redundant requests
- **REST API**: Firecrawl-compatible endpoints
- **CLI**: Scrape from terminal
- **Docker**: One-command deployment

## Quick Start

```bash
# Install
pip install -r requirements.txt
patchright install chromium

# CLI scrape
python -m freecrawl scrape https://example.com

# Start API server
python -m freecrawl serve

# API call
curl -X POST http://localhost:9100/v1/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "formats": ["markdown", "links"]}'
```

## Docker

```bash
docker-compose up -d
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/scrape` | POST | Scrape single URL |
| `/v1/crawl` | POST | Crawl entire site |
| `/v1/extract` | POST | Structured data extraction |
| `/v1/status` | GET | Engine status |
| `/health` | GET | Health check |

## Engine Comparison

| Engine | Speed | Anti-Bot | JS | Cost |
|--------|-------|----------|----|------|
| httpx | Fastest | None | No | Free |
| flaresolverr | Medium | Cloudflare | No | Free |
| patchright | Slowest | DataDome, Akamai, Cloudflare | Yes | Free |

## License

MIT
