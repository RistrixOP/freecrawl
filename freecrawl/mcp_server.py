"""
MCP (Model Context Protocol) server exposing all Freecrawl tools.
Uses stdio transport. Tools: scrape, crawl, search, map, extract, batch_scrape.
"""
import json, sys, traceback
from typing import Any, Dict
from .config import Config
from .scraper import Scraper
from .crawler import Crawler
from .search import Searcher
from .mapper import Mapper
from .batch import BatchScraper
from .extractor import Extractor

try:
    from mcp.server.fastmcp import FastMCP
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

_config: Config = None
_scraper: Scraper = None
_crawler: Crawler = None
_searcher: Searcher = None
_mapper: Mapper = None
_batcher: BatchScraper = None


def init(config: Config = None):
    global _config, _scraper, _crawler, _searcher, _mapper, _batcher
    _config = config or Config.from_env()
    _scraper = Scraper(_config)
    _crawler = Crawler(_config)
    _searcher = Searcher(_config)
    _mapper = Mapper(_config)
    _batcher = BatchScraper(_config)


def _make_mcp_server() -> Any:
    """Create and configure the MCP server if mcp package is available."""
    if not HAS_MCP:
        return None

    mcp = FastMCP("Freecrawl", instructions="Freecrawl web scraping tools: scrape, crawl, search, map, extract, batch_scrape")

    @mcp.tool(description="Scrape a single URL and return extracted content")
    def scrape(
        url: str,
        formats: str = "markdown",
        engine: str = None,
        screenshot: bool = False,
    ) -> str:
        try:
            result = _scraper.scrape(
                url=url,
                formats=formats.split(",") if formats else ["markdown"],
                engine=engine or None,
                screenshot=screenshot,
            )
            return json.dumps(result, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e), "url": url})

    @mcp.tool(description="Crawl a website starting from a URL")
    def crawl(
        url: str,
        max_depth: int = 3,
        max_pages: int = 50,
        same_domain: bool = True,
        formats: str = "markdown",
    ) -> str:
        try:
            result = _crawler.crawl(
                url=url,
                max_depth=max_depth,
                max_pages=max_pages,
                same_domain=same_domain,
                formats=formats.split(","),
            )
            return json.dumps(result, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e), "url": url})

    @mcp.tool(description="Search the web using DuckDuckGo")
    def search(
        query: str,
        num_results: int = 10,
        scrape_results: bool = False,
    ) -> str:
        try:
            result = _searcher.search(
                query=query,
                num_results=num_results,
                scrape_results=scrape_results,
            )
            return json.dumps(result, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e), "query": query})

    @mcp.tool(description="Map all URLs on a domain via sitemap and common paths")
    def map_domain(
        url: str,
        check_common: bool = True,
        discover_sitemap: bool = True,
    ) -> str:
        try:
            result = _mapper.map_domain(
                url=url,
                check_common=check_common,
                discover_sitemap=discover_sitemap,
            )
            return json.dumps(result, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e), "url": url})

    @mcp.tool(description="Extract structured data with CSS selectors")
    def extract(
        url: str,
        schema: str = None,
    ) -> str:
        try:
            schema_dict = json.loads(schema) if schema else None
            page = _scraper.scrape(url=url, formats=["html"], extract=schema_dict)
            return json.dumps(page, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e), "url": url})

    @mcp.tool(description="Batch scrape multiple URLs with concurrency control")
    def batch_scrape(
        urls: str,
        formats: str = "markdown",
        max_concurrency: int = 5,
    ) -> str:
        try:
            url_list = json.loads(urls) if isinstance(urls, str) else urls
            result = _batcher.scrape_batch(
                urls=url_list,
                formats=formats.split(","),
                max_concurrency=max_concurrency,
            )
            return json.dumps(result, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    return mcp


def run_stdio(config: Config = None):
    """Run MCP server with stdio transport."""
    if not HAS_MCP:
        print("ERROR: 'mcp' package not installed. Install with: pip install mcp", file=sys.stderr)
        sys.exit(1)

    init(config)
    mcp = _make_mcp_server()
    if mcp is None:
        print("ERROR: Failed to create MCP server", file=sys.stderr)
        sys.exit(1)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_stdio()
