"""
Freecrawl — Open-source web scraping API with anti-bot bypass.
Drop-in Firecrawl alternative. No API keys, no credits, no limits.

Engine chain: httpx → flaresolver ™ patchright (auto-escalation)
Features: scrape, crawl, extract, screenshots, JS execution, proxy rotation
"""

__version__ = "1.0.0"
__author__ = "Richard Gschwend"
__license__ = "MIT"

from freecrawl.config import Config
from freecrawl.scraper import Scraper
from freecrawl.crawler import Crawler
