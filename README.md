# 🔥 Freecrawl

> Open-source web scraping API with anti-bot bypass. Drop-in Firecrawl alternative.
> **AI-first**: MCP server, OpenAI tool definitions, REST API — any AI model can use it.
> No API keys, no credits, no limits.

## Quick Start

```bash
pip install -r requirements.txt
patchright install chromium
python -m freecrawl serve  # REST API on :9100
```

## AI Integration

### MCP Server (Claude, Cursor, any MCP client)
```json
{"mcpServers":{"freecrawl":{"command":"python","args":["-m","freecrawl.mcp_server"]}}}
```

### OpenAI Tool Definitions
```python
from freecrawl.ai_tools import get_tools
tools = get_tools()  # 9 tool definitions, pass to any LLM
```

### REST API
```bash
curl -X POST http://localhost:9100/v1/scrape \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","formats":["markdown"]}'
```

## Features

| Feature | Status |
|---------|:------:|
| Scrape (URL→Markdown/HTML/text) | ✅ |
| Anti-bot bypass (Cloudflare, DataDome) | ✅ |
| Auto-escalation engine chain | ✅ |
| Crawl (BFS + sitemap) | ✅ |
| Search (DuckDuckGo/SearXNG) | ✅ |
| Map (fast URL discovery) | ✅ |
| Batch scrape (parallel) | ✅ |
| LLM extraction (structured JSON) | ✅ |
| Change tracking (diff) | ✅ |
| PDF parsing | ✅ |
| CSS extraction | ✅ |
| Screenshots | ✅ |
| JS actions (click/scroll/type) | ✅ |
| Product/Menu/Branding extractors | ✅ |
| Summary (LLM) | ✅ |
| Proxy rotation | ✅ |
| MCP server | ✅ |
| OpenAI tool definitions | ✅ |
| Docker deployment | ✅ |
| CLI tool | ✅ |

## Architecture

```
Engine Chain (auto-escalation):
  httpx (fast) → flaresolverr (Cloudflare) → patchright (DataDome/Akamai)
```

## License

MIT
