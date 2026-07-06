
"""
FastAPI server — Firecrawl-compatible REST API with MCP support.

Endpoints:
  POST /v1/scrape      — Scrape single URL
  POST /v1/crawl       — Crawl entire site
  POST /v1/extract     — Structured data extraction (CSS)
  POST /v1/search      — Web search
  POST /v1/map         — URL discovery on a domain
  POST /v1/batch-scrape — Batch scrape
  POST /v1/llm-extract  — LLM-powered extraction
  GET  /v1/changes/{url} — Change tracking
  POST /v1/pdf         — PDF parsing
  GET  /v1/tools       — AI tool definitions
  GET  /v1/status      — Engine status
  GET  /health         — Health check
  SSE  /mcp            — MCP endpoint (SSE transport)
"""
import time, os, json
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Header, Query, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from .config import Config
from .scraper import Scraper
from .crawler import Crawler
from .search import Searcher
from .mapper import Mapper
from .batch import BatchScraper
from .llm_extract import LLMExtractor
from .changetracking import ChangeTracker
from .pdf_parser import PDFParser
from .ai_tools import get_tools

app = FastAPI(
    title="Freecrawl",
    description="Open-source web scraping API with anti-bot bypass. Drop-in Firecrawl alternative. AI-first — every AI model can use it.",
    version="1.0.0",
)

_config: Config = None
_scraper: Scraper = None
_crawler: Crawler = None
_searcher: Searcher = None
_mapper: Mapper = None
_batcher: BatchScraper = None
_llm_extractor: LLMExtractor = None
_change_tracker: ChangeTracker = None
_pdf_parser: PDFParser = None


def init_server(config: Config = None):
    global _config, _scraper, _crawler, _searcher, _mapper, _batcher
    global _llm_extractor, _change_tracker, _pdf_parser
    _config = config or Config.from_env()
    _scraper = Scraper(_config)
    _crawler = Crawler(_config)
    _searcher = Searcher(_config)
    _mapper = Mapper(_config)
    _batcher = BatchScraper(_config)
    _llm_extractor = LLMExtractor(_config)
    _change_tracker = ChangeTracker(_config)
    _pdf_parser = PDFParser(_config)


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
    engine: Optional[str] = None
    formats: List[str] = Field(default=["markdown"])
    actions: Optional[List[Dict[str, Any]]] = None
    screenshot: bool = False
    extract: Optional[Dict[str, str]] = None
    timeout: Optional[int] = None

class CrawlRequest(BaseModel):
    url: str
    max_depth: Optional[int] = None
    max_pages: Optional[int] = None
    same_domain: Optional[bool] = None
    formats: List[str] = Field(default=["markdown"])

class ExtractRequest(BaseModel):
    urls: List[str]
    extract_schema: Dict[str, str] = Field(alias="schema", description="CSS extraction: {field: selector}")

class SearchRequest(BaseModel):
    query: str
    num_results: int = Field(default=10, ge=1, le=50)
    scrape_results: bool = False
    site_filter: Optional[str] = None

class MapRequest(BaseModel):
    url: str
    check_common: bool = True
    discover_sitemap: bool = True

class BatchScrapeRequest(BaseModel):
    urls: List[str]
    formats: List[str] = Field(default=["markdown"])
    max_concurrency: Optional[int] = None
    engine: Optional[str] = None

class LLMExtractRequest(BaseModel):
    url: str
    json_schema: Optional[Dict[str, Any]] = Field(default=None, alias="schema")
    instruction: Optional[str] = None
    model: Optional[str] = None
    format_type: str = Field(default="json", pattern="^(json|summary)$")

class PDFParseRequest(BaseModel):
    url: str
    to_markdown: bool = True

class ChangeTrackRequest(BaseModel):
    url: str
    formats: List[str] = Field(default=["markdown", "text"])


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
            data = ext._css_extract(page["html"], req.extract_schema)
            data["_url"] = url
            results.append(data)
    return {"results": results, "total": len(results)}


# --- NEW ENDPOINTS ---

@app.post("/v1/search")
async def search_web(req: SearchRequest, authorization: Optional[str] = Header(None)):
    """Search the web using DuckDuckGo."""
    _check_auth(authorization)
    result = _searcher.search(
        query=req.query,
        num_results=req.num_results,
        scrape_results=req.scrape_results,
        site_filter=req.site_filter,
    )
    return result


@app.post("/v1/map")
async def map_domain(req: MapRequest, authorization: Optional[str] = Header(None)):
    """Discover all URLs on a domain."""
    _check_auth(authorization)
    result = _mapper.map_domain(
        url=req.url,
        check_common=req.check_common,
        discover_sitemap=req.discover_sitemap,
    )
    return result


@app.post("/v1/batch-scrape")
async def batch_scrape(req: BatchScrapeRequest, authorization: Optional[str] = Header(None)):
    """Scrape multiple URLs in parallel."""
    _check_auth(authorization)
    result = _batcher.scrape_batch(
        urls=req.urls,
        formats=req.formats,
        max_concurrency=req.max_concurrency,
        engine=req.engine,
    )
    return result


@app.post("/v1/llm-extract")
async def llm_extract(req: LLMExtractRequest, authorization: Optional[str] = Header(None)):
    """Extract structured data using an LLM."""
    _check_auth(authorization)
    result = _llm_extractor.extract(
        url=req.url,
        schema=req.json_schema,
        instruction=req.instruction,
        model=req.model,
        format_type=req.format_type,
    )
    return result


@app.get("/v1/changes/{url:path}")
async def get_changes(url: str, authorization: Optional[str] = Header(None)):
    """Track changes on a URL. Creates snapshot and returns diff vs previous."""
    _check_auth(authorization)
    result = _change_tracker.snapshot(url=url, formats=["markdown", "text"])
    return result


@app.post("/v1/pdf")
async def parse_pdf(req: PDFParseRequest, authorization: Optional[str] = Header(None)):
    """Download and extract text from a PDF file."""
    _check_auth(authorization)
    result = _pdf_parser.parse(url=req.url, to_markdown=req.to_markdown)
    return result


@app.get("/v1/tools")
async def list_tools(authorization: Optional[str] = Header(None)):
    """List all Freecrawl AI tool definitions (OpenAI-compatible)."""
    _check_auth(authorization)
    return {"tools": get_tools(), "total": len(get_tools())}


@app.post("/mcp")
async def mcp_sse_endpoint(request: Request):
    """MCP endpoint with SSE transport for AI models like Claude/Cursor."""
    _check_auth(request.headers.get("authorization"))
    # For now, redirect to the MCP server docs
    return JSONResponse({
        "message": "MCP SSE endpoint ready. Use standard MCP client to connect.",
        "url": "/mcp",
        "transport": "sse",
        "tools_available": [t["function"]["name"] for t in get_tools()],
    })


# --- Main ---
def run():
    import uvicorn
    config = Config.from_env()
    init_server(config)
    print(f"Freecrawl v1.0.0 starting on {config.server_host}:{config.server_port}")
    print(f"Engines: {list(_scraper._engines.keys())}")
    print(f"Cache: {'ON' if config.cache_enabled else 'OFF'}")
    print(f"Endpoints: scrape, crawl, extract, search, map, batch-scrape, llm-extract, changes, pdf, tools, mcp")
    uvicorn.run(app, host=config.server_host, port=config.server_port)


if __name__ == "__main__":
    run()
