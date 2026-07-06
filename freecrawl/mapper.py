"""
Fast URL discovery via sitemap.xml + common paths.
Returns all URLs on a domain.
"""
import time, re
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urlparse, urljoin
from .config import Config

COMMON_PATHS = [
    "/", "/about", "/contact", "/blog", "/products", "/services",
    "/pricing", "/faq", "/docs", "/documentation", "/support",
    "/terms", "/privacy", "/login", "/signup", "/register",
    "/features", "/solutions", "/use-cases", "/testimonials",
    "/careers", "/team", "/company", "/partners", "/integrations",
    "/api", "/status", "/changelog", "/roadmap", "/news",
    "/events", "/webinars", "/podcast", "/press", "/sitemap",
    "/sitemap.xml", "/sitemap_index.xml", "/sitemap/sitemap.xml",
    "/robots.txt", "/security", "/legal", "/gdpr",
    "/images", "/assets", "/downloads", "/resources",
    "/guides", "/tutorials", "/examples", "/showcase",
    "/search", "/shop", "/store", "/cart", "/checkout",
]


class Mapper:
    """Fast URL discovery for a domain."""

    def __init__(self, config: Config = None):
        self.config = config or Config()

    def discover_sitemap(self, base_url: str) -> List[str]:
        """Discover URLs from sitemap.xml."""
        from bs4 import BeautifulSoup
        import httpx

        urls = []
        parsed = urlparse(base_url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        sitemap_paths = [
            "/sitemap.xml", "/sitemap_index.xml",
            "/sitemap/sitemap.xml", "/sitemaps/sitemap.xml",
            "/sitemap/sitemap.xml.gz",
        ]

        # Also check robots.txt for Sitemap: directive
        try:
            client = httpx.Client(timeout=10, follow_redirects=True)
            r = client.get(f"{base}/robots.txt")
            if r.status_code == 200:
                sitemaps = re.findall(r'(?i)Sitemap:\s*(.*)', r.text)
                sitemap_paths = list(set(sitemaps + sitemap_paths))
            client.close()
        except:
            pass

        for sm_path in sitemap_paths:
            if sm_path.startswith("http"):
                sm_url = sm_path
            else:
                sm_url = urljoin(base, sm_path)
            try:
                client = httpx.Client(timeout=10, follow_redirects=True)
                r = client.get(sm_url)
                if r.status_code == 200:
                    # Parse sitemap
                    soup = BeautifulSoup(r.text, "lxml")
                    locs = soup.find_all("loc")
                    if locs:
                        urls.extend([loc.get_text(strip=True) for loc in locs if loc.get_text(strip=True)])
                        break  # Found a valid sitemap
                    # Check for sitemap index
                    sitemaps = soup.find_all("sitemap")
                    if sitemaps:
                        sub_locs = [s.find("loc").get_text(strip=True) for s in sitemaps if s.find("loc")]
                        for sub_url in sub_locs:
                            try:
                                sr = client.get(sub_url)
                                if sr.status_code == 200:
                                    sub_soup = BeautifulSoup(sr.text, "lxml")
                                    sub_locs = [l.get_text(strip=True) for l in sub_soup.find_all("loc") if l.get_text(strip=True)]
                                    urls.extend(sub_locs)
                            except:
                                pass
                        break
                client.close()
            except:
                pass

        return urls

    def check_common_paths(self, base_url: str) -> List[str]:
        """Check common paths and return those that exist."""
        import httpx
        parsed = urlparse(base_url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        found_urls = []
        try:
            client = httpx.Client(timeout=5, follow_redirects=True)
            for path in COMMON_PATHS:
                url = urljoin(base, path)
                try:
                    r = client.head(url, timeout=3)
                    if r.status_code in (200, 301, 302, 403):
                        found_urls.append(url)
                except:
                    pass
            client.close()
        except:
            pass
        return found_urls

    def map_domain(self, url: str, check_common: bool = True,
                   discover_sitemap: bool = True) -> Dict[str, Any]:
        """Discover all URLs on a domain.

        Args:
            url: Base URL to map
            check_common: Check common paths like /about, /contact
            discover_sitemap: Parse sitemap.xml for URLs

        Returns:
            Dict with "urls" list and "stats"
        """
        start = time.time()
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        all_urls: Set[str] = set()
        sources = {}

        # Sitemap discovery
        if discover_sitemap:
            sm_urls = self.discover_sitemap(url)
            if sm_urls:
                all_urls.update(sm_urls)
                sources["sitemap"] = len(sm_urls)

        # Common paths
        if check_common:
            common_urls = self.check_common_paths(url)
            if common_urls:
                all_urls.update(common_urls)
                sources["commonPaths"] = len(common_urls)

        # Always include base URL
        if base not in all_urls:
            all_urls.add(base)

        url_list = sorted(all_urls)

        return {
            "urls": url_list,
            "stats": {
                "total": len(url_list),
                "sources": sources,
                "domain": parsed.netloc,
                "elapsed": round(time.time() - start, 2),
            },
        }
