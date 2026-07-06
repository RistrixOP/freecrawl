
"""Main scraper with auto-escalation engine chain.

Strategy: httpx (fast) -> flaresolverr (Cloudflare) -> patchright (anti-bot)
"""
import hashlib, os, json, time
from typing import Optional, List, Dict, Any
from .config import Config
from .engines.base import ScrapeResult
from .engines.httpx_engine import HttpxEngine
from .engines.flaresolverr_engine import FlaresolverrEngine
from .engines.patchright_engine import PatchrightEngine
from .extractor import Extractor


class Scraper:
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.extractor = Extractor(self.config)
        self._engines = {}
        self._init_engines()
        self._cache = {}
        if self.config.cache_enabled:
            os.makedirs(self.config.cache_dir, exist_ok=True)

    def _init_engines(self):
        if self.config.engine in ("auto", "httpx"):
            self._engines["httpx"] = HttpxEngine(self.config)
        if self.config.engine in ("auto", "flaresolverr"):
            try:
                self._engines["flaresolverr"] = FlaresolverrEngine(self.config)
            except: pass
        if self.config.engine in ("auto", "patchright"):
            self._engines["patchright"] = PatchrightEngine(self.config)

    def _cache_key(self, url):
        return hashlib.md5(url.encode()).hexdigest()

    def _get_cached(self, url):
        if not self.config.cache_enabled:
            return None
        key = self._cache_key(url)
        path = os.path.join(self.config.cache_dir, f"{key}.json")
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            if time.time() - mtime < self.config.cache_ttl:
                with open(path) as f:
                    return json.load(f)
        return None

    def _set_cached(self, url, data):
        if not self.config.cache_enabled:
            return
        key = self._cache_key(url)
        path = os.path.join(self.config.cache_dir, f"{key}.json")
        with open(path, "w") as f:
            json.dump(data, f, default=str)

    def _proxy_for_request(self):
        """Get proxy URL, with rotation if enabled."""
        if self.config.proxy_rotation and self.config.proxy_list:
            import random
            return random.choice(self.config.proxy_list)
        return self.config.proxy_url

    def scrape(self, url: str, engine: str = None, actions: List[Dict] = None,
               screenshot: bool = False, formats: List[str] = None,
               extract: Dict = None, **kwargs) -> Dict[str, Any]:
        """Scrape a single URL and return extracted content.

        Args:
            url: Target URL
            engine: Force engine ("httpx", "flaresolverr", "patchright")
            actions: JS actions [{type: "click", selector: "..."}]
            screenshot: Take full-page screenshot
            formats: Output formats ["markdown", "html", "text", "json", "links", "screenshot"]
            extract: CSS extraction schema {field: "selector"}
        Returns:
            Dict with content in requested formats + metadata
        """
        formats = formats or ["markdown"]
        cached = self._get_cached(url)
        if cached and not actions and not screenshot:
            return cached

        forced = engine or self.config.engine
        if forced != "auto":
            order = [forced]
        else:
            order = ["httpx", "flaresolverr", "patchright"]

        result = None
        engines_tried = []
        for eng_name in order:
            eng = self._engines.get(eng_name)
            if not eng:
                continue
            engines_tried.append(eng_name)
            # Update proxy for this attempt
            if self.config.proxy_rotation:
                self.config.proxy_url = self._proxy_for_request()

            need_browser = eng_name in ("patchright",) and (actions or screenshot)
            result = eng.scrape(url, actions=actions if need_browser else None,
                               screenshot=screenshot if need_browser else False, **kwargs)

            if result.ok and not result.blocked:
                break

        if not result:
            result = ScrapeResult(url=url, error="No engines available")
            result.elapsed = 0.1

        # Extract content
        output = self.extractor.extract(result, formats=formats, extract_schema=extract)

        # Metadata
        output["metadata"] = {
            "url": url,
            "statusCode": result.status_code,
            "engineUsed": result.engine_used,
            "enginesTried": engines_tried,
            "elapsed": round(result.elapsed, 2),
            "blocked": result.blocked,
            "error": result.error,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        if result.screenshots:
            output["screenshot"] = result.screenshots[0]

        if not actions and not screenshot:
            self._set_cached(url, output)
        return output

    def close(self):
        for eng in self._engines.values():
            try: eng.close()
            except: pass
