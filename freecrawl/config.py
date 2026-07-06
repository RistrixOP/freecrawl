"""Global configuration for Freecrawl."""
import os
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Config:
    engine: str = "auto"
    headless: bool = True
    channel: str = "chromium"
    user_data_dir: Optional[str] = None
    viewport_width: int = 1920
    viewport_height: int = 1080
    locale: str = "de-CH"
    timeout: int = 30000
    wait_until: str = "domcontentloaded"
    wait_after_load: float = 2.0
    proxy_url: Optional[str] = None
    proxy_rotation: bool = False
    proxy_list: List[str] = field(default_factory=list)
    flaresolverr_url: str = "http://127.0.0.1:8191"
    max_concurrency: int = 5
    max_depth: int = 3
    max_pages: int = 50
    same_domain_only: bool = True
    cache_enabled: bool = True
    cache_dir: str = "/tmp/freecrawl-cache"
    cache_ttl: int = 3600
    include_links: bool = True
    include_images: bool = True
    include_metadata: bool = True
    server_host: str = "0.0.0.0"
    server_port: int = 9100
    api_key: Optional[str] = None
    # --- NEW v2 fields ---
    llm_api_key: Optional[str] = None
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    search_engine_url: str = "https://html.duckduckgo.com/html/"
    searxng_url: Optional[str] = None
    pdf_cache_dir: str = "/tmp/freecrawl-pdf"
    changetracking_dir: str = "/tmp/freecrawl-changes"
    block_ads: bool = True

    @classmethod
    def from_env(cls):
        def eb(k, d=False): return os.environ.get(k, str(d)).lower() in ("true","1","yes")
        pls = os.environ.get("FREECRAWL_PROXY_LIST","")
        pl = [p.strip() for p in pls.split(",") if p.strip()] if pls else []
        return cls(
            engine=os.environ.get("FREECRAWL_ENGINE","auto"),
            headless=eb("FREECRAWL_HEADLESS", True),
            channel=os.environ.get("FREECRAWL_CHANNEL","chromium"),
            timeout=int(os.environ.get("FREECRAWL_TIMEOUT","30000")),
            proxy_url=os.environ.get("FREECRAWL_PROXY_URL"),
            proxy_rotation=eb("FREECRAWL_PROXY_ROTATION", False),
            proxy_list=pl,
            flaresolverr_url=os.environ.get("FREECRAWL_FLARESOLVERR_URL","http://127.0.0.1:8191"),
            max_concurrency=int(os.environ.get("FREECRAWL_MAX_CONCURRENCY","5")),
            max_depth=int(os.environ.get("FREECRAWL_MAX_DEPTH","3")),
            max_pages=int(os.environ.get("FREECRAWL_MAX_PAGES","50")),
            cache_enabled=eb("FREECRAWL_CACHE_ENABLED", True),
            cache_dir=os.environ.get("FREECRAWL_CACHE_DIR","/tmp/freecrawl-cache"),
            server_host=os.environ.get("FREECRAWL_HOST","0.0.0.0"),
            server_port=int(os.environ.get("FREECRAWL_PORT","9100")),
            api_key=os.environ.get("FREECRAWL_API_KEY"),
            llm_api_key=os.environ.get("FREECRAWL_LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY"),
            llm_base_url=os.environ.get("FREECRAWL_LLM_BASE_URL","https://api.deepseek.com/v1"),
            llm_model=os.environ.get("FREECRAWL_LLM_MODEL","deepseek-chat"),
            searxng_url=os.environ.get("FREECRAWL_SEARXNG_URL"),
            block_ads=eb("FREECRAWL_BLOCK_ADS", True),
        )
