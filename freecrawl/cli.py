
"""Freecrawl CLI — scrape, crawl, extract from terminal.

Usage:
  freecrawl scrape https://example.com
  freecrawl scrape https://example.com --format markdown,links,json
  freecrawl scrape https://example.com --engine patchright --screenshot
  freecrawl crawl https://example.com --depth 2 --max-pages 20
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

    # serve
    svp = sub.add_parser("serve", help="Start REST API server")
    svp.add_argument("--port", "-p", type=int, default=9100)
    svp.add_argument("--host", default="0.0.0.0")

    # extract
    ep = sub.add_parser("extract", help="Extract structured data with CSS selectors")
    ep.add_argument("url")
    ep.add_argument("--schema", "-s", required=True, help='JSON schema: \'{"title":"h1","price":".price"}\'')

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
        # Print summary
        print(json.dumps({
            "stats": result["stats"],
            "pages": [{"url": p.get("metadata",{}).get("url",""), "title": p.get("title",""), "engine": p.get("metadata",{}).get("engineUsed","")} for p in result["pages"]]
        }, indent=2, ensure_ascii=False))

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
