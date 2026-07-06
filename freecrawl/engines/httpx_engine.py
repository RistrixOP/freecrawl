
"""Fast HTTP engine — no JS, no anti-bot. For unprotected pages."""
import httpx, time
from .base import BaseEngine, ScrapeResult
from bs4 import BeautifulSoup

class HttpxEngine(BaseEngine):
    name = "httpx"
    def __init__(self, config):
        super().__init__(config)
        proxies = config.proxy_url if config.proxy_url else None
        self.client = httpx.Client(
            timeout=config.timeout / 1000,
            follow_redirects=True,
            proxy=proxies,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"}
        )

    def scrape(self, url, **kwargs) -> ScrapeResult:
        start = time.time()
        result = ScrapeResult(url=url, engine_used=self.name)
        try:
            r = self.client.get(url)
            result.status_code = r.status_code
            result.html = r.text
            result.headers = dict(r.headers)
            soup = BeautifulSoup(r.text, "lxml")
            result.title = soup.title.string.strip() if soup.title and soup.title.string else ""
            result.text = soup.get_text(separator="\n", strip=True)
        except Exception as e:
            result.error = str(e)
        result.elapsed = time.time() - start
        return result

    def close(self):
        self.client.close()
