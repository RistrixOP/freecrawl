
"""Freecrawl CLI — scrape, crawl, extract, search, map, batch, serve from terminal.

Usage:
  freecrawl scrape https://example.com
  freecrawl search "python web scraping"
  freecrawl map https://example.com
  freecrawl batch urls.json
  freecrawl llm-extract https://example.com --schema '{"name":"h1","price":".price"}'
  freecrawl serve [--port 9100]
"""
import sys, json, argparse
from .config import Config


def main():
    parser = argparse.ArgumentParser(prog="freecrawl", description="Open-source web scraper")
    sub = parser.add_subparsers(dest="command")

    # scrape
    sp = sub.add_parser("scrape", help="Scrape a single URL")
    sp.add_argument("url")
    sp.add_argument("--engine", "-e", choices=["auto","httpx","flaresolverr","patchright"], default="auto")
    sp.add_argument("--format", "-f", default="markdown", help="Comma-separated: markdown,html,text,json,links,images")
    sp.add_argument("--screenshot", "-s", action="store_true")
    sp.add_argument("--no-cache", action="store_true")
    sp.add_argument("--timeout", type=int, default=30000)
    sp.add_argument("--headless", action="store_true", default=True)
    sp.add_argument("--no-headless", dest="headless", action="store_false")

    # crawl
    cp = sub.add_parser("crawl", help="Crawl a website")
    cp.add_argument("url")
    cp.add_argument("--depth", "-d", type=int, default=3)
    cp.add_argument("--max-pages", "-m", type=int, default=50)
    cp.add_argument("--format", "-f", default="markdown")

    # search
    sp_search = sub.add_parser("search", help="Search the web")
    sp_search.add_argument("query", nargs="+", help="Search query")
    sp_search.add_argument("--num-results", "-n", type=int, default=10)
    sp_search.add_argument("--scrape", action="store_true", help="Scrape each result URL")
    sp_search.add_argument("--site", "-s", help="Filter by site:domain")

    # map
    sp_map = sub.add_parser("map", help="Map all URLs on a domain")
    sp_map.add_argument("url", help="Base URL (e.g. https://example.com)")
    sp_map.add_argument("--no-common", action="store_true", help="Skip common path checking")
    sp_map.add_argument("--no-sitemap", action="store_true", help="Skip sitemap discovery")

    # batch
    sp_batch = sub.add_parser("batch", help="Batch scrape multiple URLs")
    sp_batch.add_argument("input", help="JSON file with URLs array or comma-separated URLs")
    sp_batch.add_argument("--format", "-f", default="markdown")
    sp_batch.add_argument("--concurrency", "-c", type=int, default=5)
    sp_batch.add_argument("--engine", "-e", default="auto")

    # llm-extract
    sp_llm = sub.add_parser("llm-extract", help="Extract structured data using LLM")
    sp_llm.add_argument("url")
    sp_llm.add_argument("--schema", "-s", help='JSON schema: \'{"name":"extract page title"}\'')
    sp_llm.add_argument("--instruction", "-i", help="Custom LLM instruction")
    sp_llm.add_argument("--summary", action="store_true", help="Get a summary instead of structured JSON")
    sp_llm.add_argument("--model", "-m", default=None, help="LLM model override")

    # serve
    svp = sub.add_parser("serve", help="Start REST API server")
    svp.add_argument("--port", "-p", type=int, default=9100)
    svp.add_argument("--host", default="0.0.0.0")

    # extract
    ep = sub.add_parser("extract", help="Extract structured data with CSS selectors")
    ep.add_argument("url")
    ep.add_argument("--schema", "-s", required=True, help='JSON schema: \'{"title":"h1","price":".price"}\'')

    # changes
    sp_changes = sub.add_parser("changes", help="Track changes on a URL")
    sp_changes.add_argument("url", help="URL to check for changes")

    # pdf
    sp_pdf = sub.add_parser("pdf", help="Extract text from a PDF URL")
    sp_pdf.add_argument("url", help="URL to a PDF file")
    sp_pdf.add_argument("--no-markdown", action="store_true", help="Return plain text, not markdown")

    # tools
    sp_tools = sub.add_parser("tools", help="List all AI tool definitions")

    # mcp-server
    sp_mcp = sub.add_parser("mcp-server", help="Start MCP stdio server")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    config = Config.from_env()
    if hasattr(args, "engine"):
        config.engine = args.engine
    if hasattr(args, "timeout"):
        config.timeout = args.timeout

    if args.command == "scrape":
        from .scraper import Scraper
        formats = args.format.split(",")
        if args.no_cache:
            config.cache_enabled = False
        config.headless = args.headless
        scraper = Scraper(config)
        result = scraper.scrape(args.url, formats=formats, screenshot=args.screenshot)
        scraper.close()
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

    elif args.command == "crawl":
        from .crawler import Crawler
        formats = args.format.split(",")
        crawler = Crawler(config)
        result = crawler.crawl(args.url, max_depth=args.depth, max_pages=args.max_pages, formats=formats)
        crawler.close()
        print(json.dumps({
            "stats": result["stats"],
            "pages": [{"url": p.get("metadata",{}).get("url",""), "title": p.get("title",""), "engine": p.get("metadata",{}).get("engineUsed","")} for p in result["pages"]]
        }, indent=2, ensure_ascii=False))

    elif args.command == "search":
        from .search import Searcher
        query = " ".join(args.query)
        searcher = Searcher(config)
        result = searcher.search(query=query, num_results=args.num_results,
                                 scrape_results=args.scrape, site_filter=args.site)
        searcher = None
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "map":
        from .mapper import Mapper
        mapper = Mapper(config)
        result = mapper.map_domain(
            url=args.url,
            check_common=not args.no_common,
            discover_sitemap=not args.no_sitemap,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "batch":
        from .batch import BatchScraper
        # Parse input: either JSON file with URLs array, or comma-separated
        if args.input.endswith(".json"):
            with open(args.input) as f:
                urls = json.load(f)
        else:
            urls = [u.strip() for u in args.input.split(",") if u.strip()]
        batcher = BatchScraper(config)
        result = batcher.scrape_batch(
            urls=urls,
            formats=args.format.split(","),
            max_concurrency=args.concurrency,
            engine=args.engine if args.engine != "auto" else None,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "llm-extract":
        from .llm_extract import LLMExtractor
        schema = json.loads(args.schema) if args.schema else None
        extractor = LLMExtractor(config)
        result = extractor.extract(
            url=args.url,
            schema=schema,
            instruction=args.instruction,
            model=args.model,
            format_type="summary" if args.summary else "json",
        )
        extractor.close()
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

    elif args.command == "changes":
        from .changetracking import ChangeTracker
        tracker = ChangeTracker(config)
        result = tracker.snapshot(url=args.url, formats=["markdown", "text"])
        tracker.close()
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

    elif args.command == "pdf":
        from .pdf_parser import PDFParser
        parser = PDFParser(config)
        result = parser.parse(url=args.url, to_markdown=not args.no_markdown)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

    elif args.command == "tools":
        from .ai_tools import get_tools
        tools = get_tools()
        print(json.dumps({"tools": tools, "total": len(tools)}, indent=2, ensure_ascii=False))

    elif args.command == "mcp-server":
        from .mcp_server import run_stdio
        run_stdio(config)

    elif args.command == "serve":
        config.server_port = args.port
        config.server_host = args.host
        from .api import init_server, app
        import uvicorn
        init_server(config)
        print(f"Freecrawl on {args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port)

    elif args.command == "extract":
        from .scraper import Scraper
        schema = json.loads(args.schema)
        scraper = Scraper(config)
        result = scraper.scrape(args.url, formats=["html"], extract=schema)
        scraper.close()
        print(json.dumps(result.get("extract",{}), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
