"""
OpenAI-compatible function/tool definitions for every feature.
JSON schema definitions that any LLM can use.
"""
from typing import List, Dict, Any


# Each tool definition follows OpenAI's tool/function calling format

SCRAPE_TOOL = {
    "type": "function",
    "function": {
        "name": "freecrawl_scrape",
        "description": "Scrape a single URL and extract content (markdown, text, links, images, JSON-LD)",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Target URL to scrape",
                },
                "formats": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["markdown", "html", "text", "json", "links", "images", "metadata", "summary", "product", "menu"]},
                    "description": "Output formats to return",
                    "default": ["markdown"],
                },
                "engine": {
                    "type": "string",
                    "enum": ["auto", "httpx", "flaresolverr", "patchright"],
                    "description": "Engine to use for scraping (auto = auto-escalate)",
                    "default": "auto",
                },
                "screenshot": {
                    "type": "boolean",
                    "description": "Take a full-page screenshot",
                    "default": False,
                },
                "extract": {
                    "type": "object",
                    "description": "CSS extraction schema: {field_name: css_selector}",
                    "additionalProperties": {"type": "string"},
                },
                "actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["click", "scroll", "wait", "type", "evaluate", "press"]},
                            "selector": {"type": "string"},
                            "text": {"type": "string"},
                            "amount": {"type": "integer"},
                            "delay": {"type": "number"},
                        },
                    },
                    "description": "JavaScript actions to execute after page load",
                },
            },
            "required": ["url"],
        },
    },
}

CRAWL_TOOL = {
    "type": "function",
    "function": {
        "name": "freecrawl_crawl",
        "description": "Crawl a website using BFS, discovering pages via sitemap.xml and link extraction",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Starting URL for the crawl",
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum crawl depth",
                    "default": 3,
                },
                "max_pages": {
                    "type": "integer",
                    "description": "Maximum pages to crawl",
                    "default": 50,
                },
                "same_domain": {
                    "type": "boolean",
                    "description": "Stay on the same domain only",
                    "default": True,
                },
                "formats": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Output formats",
                    "default": ["markdown"],
                },
            },
            "required": ["url"],
        },
    },
}

SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "freecrawl_search",
        "description": "Search the web using DuckDuckGo (optionally SearXNG) and return URLs, titles, and snippets",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Maximum number of search results to return",
                    "default": 10,
                },
                "scrape_results": {
                    "type": "boolean",
                    "description": "If true, also scrape each result URL for full content",
                    "default": False,
                },
                "site_filter": {
                    "type": "string",
                    "description": "Optional site:domain filter (e.g., 'example.com')",
                },
            },
            "required": ["query"],
        },
    },
}

MAP_TOOL = {
    "type": "function",
    "function": {
        "name": "freecrawl_map",
        "description": "Discover all URLs on a domain via sitemap.xml parsing and common path checking",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Base URL of the domain to map",
                },
                "check_common": {
                    "type": "boolean",
                    "description": "Check common paths like /about, /contact, /blog",
                    "default": True,
                },
                "discover_sitemap": {
                    "type": "boolean",
                    "description": "Parse sitemap.xml for URLs",
                    "default": True,
                },
            },
            "required": ["url"],
        },
    },
}

EXTRACT_TOOL = {
    "type": "function",
    "function": {
        "name": "freecrawl_extract",
        "description": "Extract structured data from a page using CSS selectors",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to extract data from",
                },
                "schema": {
                    "type": "object",
                    "description": "CSS extraction schema: {field_name: css_selector}",
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["url", "schema"],
        },
    },
}

BATCH_SCRAPE_TOOL = {
    "type": "function",
    "function": {
        "name": "freecrawl_batch_scrape",
        "description": "Scrape multiple URLs in parallel with configurable concurrency control",
        "parameters": {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of URLs to scrape",
                },
                "formats": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Output formats",
                    "default": ["markdown"],
                },
                "max_concurrency": {
                    "type": "integer",
                    "description": "Maximum number of parallel requests",
                    "default": 5,
                },
                "engine": {
                    "type": "string",
                    "description": "Force a specific engine",
                    "default": "auto",
                },
            },
            "required": ["urls"],
        },
    },
}

LLM_EXTRACT_TOOL = {
    "type": "function",
    "function": {
        "name": "freecrawl_llm_extract",
        "description": "Extract structured data from a URL using an LLM (DeepSeek). Scrapes the page, sends content to LLM with a schema, returns structured JSON.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to extract data from",
                },
                "schema": {
                    "type": "object",
                    "description": "JSON schema defining the output structure",
                },
                "instruction": {
                    "type": "string",
                    "description": "Custom instruction for the LLM",
                },
                "format_type": {
                    "type": "string",
                    "enum": ["json", "summary"],
                    "description": "Output format: 'json' for structured data, 'summary' for text summary",
                    "default": "json",
                },
            },
            "required": ["url"],
        },
    },
}

PDF_PARSE_TOOL = {
    "type": "function",
    "function": {
        "name": "freecrawl_pdf_parse",
        "description": "Download and extract text from a PDF file. Returns text, markdown, page-by-page content.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to a PDF file",
                },
                "to_markdown": {
                    "type": "boolean",
                    "description": "Convert extracted text to markdown format",
                    "default": True,
                },
            },
            "required": ["url"],
        },
    },
}

CHANGE_TRACK_TOOL = {
    "type": "function",
    "function": {
        "name": "freecrawl_changes",
        "description": "Track changes in web page content. Creates a snapshot and compares with previous version, returning a diff.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to check for changes",
                },
                "formats": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Scrape formats",
                    "default": ["markdown"],
                },
            },
            "required": ["url"],
        },
    },
}

_ALL_TOOLS = [
    SCRAPE_TOOL,
    CRAWL_TOOL,
    SEARCH_TOOL,
    MAP_TOOL,
    EXTRACT_TOOL,
    BATCH_SCRAPE_TOOL,
    LLM_EXTRACT_TOOL,
    PDF_PARSE_TOOL,
    CHANGE_TRACK_TOOL,
]


def get_tools() -> List[Dict]:
    """Return all Freecrawl tool definitions in OpenAI format."""
    return list(_ALL_TOOLS)


def get_tool_names() -> List[str]:
    """Return list of all tool names."""
    return [t["function"]["name"] for t in _ALL_TOOLS]


def get_tool_by_name(name: str) -> Dict:
    """Get a specific tool definition by name."""
    for t in _ALL_TOOLS:
        if t["function"]["name"] == name:
            return t
    return None
