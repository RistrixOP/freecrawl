
"""BFS site crawler with sitemap discovery."""
import asyncio, time, re
from typing import List, Set, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from .config import Config
from .scraper import Scraper


class Crawler:
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.scraper = Scraper(self.config)

    def _same_domain(self, url1: str, url2: str) -> bool:
        return urlparse(url1).netloc == urlparse(url2).netloc

    def _normalize_url(self, url: str) -> str:
        """Remove fragments and normalize."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}" + (f"?{parsed.query}" if parsed.query else "")

    def _discover_from_sitemap(self, base_url: str) -> List[str]:
        """Try to discover URLs from sitemap.xml."""
        urls = []
        try:
            import httpx
            for sm_path in ["/sitemap.xml", "/sitemap/sitemap.xml", "/sitemap_index.xml"]:
                sm_url = urljoin(base_url, sm_path)
                r = httpx.get(sm_url, timeout=10, follow_redirects=True)
                if r.status_code == 200 and "<urlset" in r.text or "<sitemapindex" in r.text:
                    urls = re.findall(r"<loc>(.*?)</loc>", r.text)
                    if urls:
                        break
        except: pass
        return urls

    def _extract_page_links(self, html: str, base_url: str) -> List[str]:
        """Extract all links from a page."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        links = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:"):
                continue
            full = urljoin(base_url, href)
            full = self._normalize_url(full)
            if full not in seen:
                seen.add(full)
                links.append(full)
        return links

    def crawl(self, url: str, max_depth: int = None, max_pages: int = None,
              same_domain: bool = None, formats: List[str] = None) -> Dict[str, Any]:
        """BFS crawl starting from a URL.
        Returns dict with "pages" list and "stats".
        """
        max_depth = max_depth if max_depth is not None else self.config.max_depth
        max_pages = max_pages if max_pages is not None else self.config.max_pages
        same_domain = same_domain if same_domain is not None else self.config.same_domain_only
        formats = formats or ["markdown"]

        visited: Set[str] = set()
        queue: List[tuple] = [(url, 0)]  # (url, depth)
        results: List[Dict] = []
        start_time = time.time()

        # Try sitemap first for broader discovery
        sitemap_urls = []
        if max_pages > 10:
            sitemap_urls = self._discover_from_sitemap(url)
            for sm_url in sitemap_urls[:max_pages]:
                if sm_url not in visited:
                    queue.append((sm_url, 0))

        while queue and len(results) < max_pages:
            current_url, depth = queue.pop(0)
            current_url = self._normalize_url(current_url)
            if current_url in visited:
                continue
            visited.add(current_url)

            if same_domain and not self._same_domain(current_url, url):
                continue

            if depth > max_depth:
                continue

            page = self.scraper.scrape(current_url, formats=formats)
            results.append(page)

            # Extract links for next depth level
            if depth < max_depth and page.get("html"):
                page_links = self._extract_page_links(page["html"], current_url)
                for link in page_links:
                    if link not in visited:
                        if not same_domain or self._same_domain(link, url):
                            queue.append((link, depth + 1))

        elapsed = time.time() - start_time
        return {
            "pages": results,
            "stats": {
                "totalPages": len(results),
                "totalVisited": len(visited),
                "maxDepth": max_depth,
                "elapsed": round(elapsed, 2),
                "fromSitemap": len(sitemap_urls),
            },
        }

    def close(self):
        self.scraper.close()
