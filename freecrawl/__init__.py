
"""
Freecrawl — Open-source web scraping API with anti-bot bypass.
Drop-in Firecrawl alternative. No API keys, no credits, no limits.

Engine chain: httpx -> flaresolverr -> patchright (auto-escalation)
Features: scrape, crawl, extract, search, map, batch, llm-extract, changes, pdf
AI-first: MCP server + OpenAI-compatible tool definitions.
"""

__version__ = "1.0.0"
__author__ = "Richard Gschwend"
__license__ = "MIT"

from freecrawl.config import Config
from freecrawl.scraper import Scraper
from freecrawl.crawler import Crawler
from freecrawl.search import Searcher
from freecrawl.mapper import Mapper
from freecrawl.batch import BatchScraper
from freecrawl.llm_extract import LLMExtractor
from freecrawl.changetracking import ChangeTracker
from freecrawl.pdf_parser import PDFParser
from freecrawl.ai_tools import get_tools
