
"""FastAPI server — Firecrawl-compatible REST API.

Endpoints:
  POST /v1/scrape    — Scrape single URL
  POST /v1/crawl     — Crawl entire site
  POST /v1/extract   — Structured data extraction
  GET  /v1/status    — Engine status
  GET  /health       — Health check
"""
import time, os
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Header, Query
from pydantic import BaseModel, Field
from .config import Config
from .scraper import Scraper
from .crawler import Crawler

app = FastAPI(
    title="Freecrawl",
    description="Open-source web scraping API with anti-bot bypass. Drop-in Firecrawl alternative.",
    version="1.0.0",
)

_config: Config = None
_scraper: Scraper = None
_crawler: Crawler = None


def init_server(config: Config = None):
    global _config, _scraper, _crawler
    _config = config or Config.from_env()
    _scraper = Scraper(_config)
    _crawler = Crawler(_config)


# --- Auth ---
def _check_auth(authorization: Optional[str] = None):
    if _config and _config.api_key:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Missing API key")
        token = authorization.split(" ", 1)[1]
        if token != _config.api_key:
            raise HTTPException(403, "Invalid API key")


# --- Models ---
class ScrapeRequest(BaseModel):
    url: str
    engine: Optional[str] = None  # "httpx", "flaresolverr", "patchright"
    formats: List[str] = Field(default=["markdown"], description="Output formats: markdown, html, text, json, links, images")
    actions: Optional[List[Dict[str, Any]]] = None  # JS actions
    screenshot: bool = False
    extract: Optional[Dict[str, str]] = None  # CSS extraction schema
    timeout: Optional[int] = None

class CrawlRequest(BaseModel):
    url: str
    max_depth: Optional[int] = None
    max_pages: Optional[int] = None
    same_domain: Optional[bool] = None
    formats: List[str] = Field(default=["markdown"])

class ExtractRequest(BaseModel):
    urls: List[str]
    schema: Dict[str, str] = Field(description="CSS extraction: {field: selector}")


# --- Routes ---
@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "engines": list(_scraper._engines.keys()) if _scraper else []}


@app.get("/v1/status")
async def status():
    engines = {}
    if _scraper:
        for name, eng in _scraper._engines.items():
            engines[name] = {"available": True, "name": eng.name}
    return {
        "status": "ok",
        "engine": _config.engine if _config else "auto",
        "engines": engines,
        "cache_enabled": _config.cache_enabled if _config else False,
        "version": "1.0.0",
    }


@app.post("/v1/scrape")
async def scrape(req: ScrapeRequest, authorization: Optional[str] = Header(None)):
    _check_auth(authorization)
    result = _scraper.scrape(
        url=req.url,
        engine=req.engine,
        actions=req.actions,
        screenshot=req.screenshot,
        formats=req.formats,
        extract=req.extract,
    )
    return result


@app.post("/v1/crawl")
async def crawl(req: CrawlRequest, authorization: Optional[str] = Header(None)):
    _check_auth(authorization)
    result = _crawler.crawl(
        url=req.url,
        max_depth=req.max_depth,
        max_pages=req.max_pages,
        same_domain=req.same_domain,
        formats=req.formats,
    )
    return result


@app.post("/v1/extract")
async def extract(req: ExtractRequest, authorization: Optional[str] = Header(None)):
    _check_auth(authorization)
    results = []
    for url in req.urls:
        page = _scraper.scrape(url=url, formats=["html"])
        if page.get("html"):
            from .extractor import Extractor
            ext = Extractor(_config)
            data = ext._css_extract(page["html"], req.schema)
            data["_url"] = url
            results.append(data)
    return {"results": results, "total": len(results)}


# --- Main ---
def run():
    import uvicorn
    config = Config.from_env()
    init_server(config)
    print(f"Freecrawl v1.0.0 starting on {config.server_host}:{config.server_port}")
    print(f"Engines: {list(_scraper._engines.keys())}")
    print(f"Cache: {'ON' if config.cache_enabled else 'OFF'}")
    uvicorn.run(app, host=config.server_host, port=config.server_port)


if __name__ == "__main__":
    run()
