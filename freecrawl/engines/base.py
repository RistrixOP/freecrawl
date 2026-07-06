"""Base class for all scraping engines."""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

@dataclass
class ScrapeResult:
    url: str
    status_code: int = 0
    html: str = ""
    text: str = ""
    title: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None
    engine_used: str = ""
    elapsed: float = 0.0
    screenshots: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.error is None and self.status_code in (200, 301, 302) and len(self.html) > 500

    @property
    def blocked(self) -> bool:
        if not self.html:
            return True
        low = self.html.lower()
        indicators = [
            "datadome", "just a moment", "cloudflare", "challenge-platform",
            "dd={", "cf-challenge", "access denied", "captcha", "are you human",
            "bot detection", "enable javascript"
        ]
        return any(ind in low for ind in indicators) and len(self.text) < 200

class BaseEngine:
    name = "base"
    def __init__(self, config):
        self.config = config
    def scrape(self, url, **kwargs) -> ScrapeResult:
        raise NotImplementedError
    def close(self):
        pass
