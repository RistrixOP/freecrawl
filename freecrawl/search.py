"""
Web search via DuckDuckGo HTML + optional SearXNG.
Returns URLs, titles, snippets, optionally scrapes results.
"""
import time, re, json
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus, urlparse, urljoin
from .config import Config

class SearchResult:
    """Single search result."""
    def __init__(self, title: str, url: str, snippet: str = ""):
        self.title = title
        self.url = url
        self.snippet = snippet

    def to_dict(self) -> Dict:
        return {"title": self.title, "url": self.url, "snippet": self.snippet}


class Searcher:
    """Web search using DuckDuckGo HTML endpoint."""

    def __init__(self, config: Config = None):
        self.config = config or Config()

    def search(self, query: str, num_results: int = 10, scrape_results: bool = False,
               site_filter: str = None) -> Dict[str, Any]:
        """Search the web and return results.

        Args:
            query: Search query string
            num_results: Max results to return (default 10)
            scrape_results: If True, scrape each result URL for content
            site_filter: Optional site:domain filter

        Returns:
            Dict with "results" list and "stats"
        """
        import httpx
        from bs4 import BeautifulSoup

        # Build DuckDuckGo HTML search URL
        search_query = query
        if site_filter:
            search_query = f"site:{site_filter} {query}"

        params = {"q": search_query}
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        start_time = time.time()
        results = []
        error = None

        try:
            client = httpx.Client(timeout=15, follow_redirects=True)
            resp = client.get("https://html.duckduckgo.com/html/", params=params, headers=headers)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "lxml")
            result_links = soup.select(".result__body, .web-result")

            for link in result_links[:num_results]:
                a_tag = link.select_one("a.result__a, .result__title a, a[href]")
                snippet_el = link.select_one(".result__snippet, .snippet, .result__snippet a")

                if not a_tag:
                    continue

                title = a_tag.get_text(strip=True)
                href = a_tag.get("href", "")
                # DuckDuckGo wraps URLs in redirect
                if "uddg=" in href or "redirect?" in href:
                    from urllib.parse import parse_qs, urlparse as up
                    parsed = up(href)
                    qs = parse_qs(parsed.query or "")
                    href = qs.get("uddg", [href])[0]
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                if href and not href.startswith("javascript:"):
                    results.append(SearchResult(title, href, snippet))

            # Fallback: try scraping the result links table
            if not results:
                for a in soup.select("a[href]"):
                    href = a.get("href", "")
                    if "uddg=" in href:
                        from urllib.parse import parse_qs
                        qs = parse_qs(urlparse(href).query)
                        real_url = qs.get("uddg", [""])[0]
                        if real_url:
                            results.append(SearchResult(a.get_text(strip=True), real_url, ""))

            client.close()
        except Exception as e:
            error = str(e)

        elapsed = time.time() - start_time

        output = {
            "results": [r.to_dict() for r in results[:num_results]],
            "stats": {
                "total": len(results),
                "elapsed": round(elapsed, 2),
                "engine": "duckduckgo",
                "error": error,
            },
        }

        # Optionally scrape each result
        if scrape_results and results:
            from .scraper import Scraper
            scraper = Scraper(self.config)
            scraped = []
            for r in results[:min(num_results, 5)]:  # Max 5 to be reasonable
                try:
                    page = scraper.scrape(r.url, formats=["markdown"])
                    scraped.append({"url": r.url, "title": r.title, "content": page.get("markdown", "")})
                except:
                    scraped.append({"url": r.url, "title": r.title, "content": None})
            scraper.close()
            output["scraped"] = scraped

        return output


class SearXNGSearch:
    """Search via SearXNG instance."""

    def __init__(self, searxng_url: str):
        self.base_url = searxng_url.rstrip("/")

    def search(self, query: str, num_results: int = 10,
               categories: List[str] = None) -> Dict[str, Any]:
        import httpx
        params = {
            "q": query,
            "format": "json",
            "language": "en-US",
        }
        if categories:
            params["categories"] = ",".join(categories)

        start = time.time()
        results = []
        error = None

        try:
            client = httpx.Client(timeout=15)
            resp = client.get(f"{self.base_url}/search", params=params)
            data = resp.json()
            for r in data.get("results", [])[:num_results]:
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    snippet=r.get("content", ""),
                ))
            client.close()
        except Exception as e:
            error = str(e)

        return {
            "results": [r.to_dict() for r in results],
            "stats": {
                "total": len(results),
                "elapsed": round(time.time() - start, 2),
                "engine": "searxng",
                "error": error,
            },
        }
