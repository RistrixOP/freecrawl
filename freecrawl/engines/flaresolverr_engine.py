
"""Flaresolverr engine — solves Cloudflare challenges using existing instance."""
import httpx, time, json
from .base import BaseEngine, ScrapeResult
from bs4 import BeautifulSoup

class FlaresolverrEngine(BaseEngine):
    name = "flaresolverr"
    def __init__(self, config):
        super().__init__(config)
        self.url = config.flaresolverr_url
        self.client = httpx.Client(timeout=120)

    def scrape(self, url, **kwargs) -> ScrapeResult:
        start = time.time()
        result = ScrapeResult(url=url, engine_used=self.name)
        try:
            # Flaresolverr v1 endpoint
            resp = self.client.post(f"{self.url}/v1", json={
                "cmd": "request.get",
                "url": url,
                "maxTimeout": self.config.timeout
            })
            data = resp.json()
            if data.get("status") == "ok":
                sol = data.get("solution", {})
                result.status_code = sol.get("status", 200)
                result.html = sol.get("response", "")
                result.headers = sol.get("headers", {})
                ua = sol.get("userAgent", "")
                for c in sol.get("cookies", []):
                    result.cookies[c["name"]] = c["value"]
                soup = BeautifulSoup(result.html, "lxml")
                result.title = soup.title.string.strip() if soup.title and soup.title.string else ""
                result.text = soup.get_text(separator="\n", strip=True)
            else:
                result.error = f"Flaresolverr error: {data.get('error','unknown')}"
        except Exception as e:
            result.error = str(e)
        result.elapsed = time.time() - start
        return result

    def close(self):
        self.client.close()
