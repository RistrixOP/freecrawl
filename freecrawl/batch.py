"""
Async batch scrape with concurrency control.
Takes list of URLs, returns results.
"""
import asyncio, time, json, os
from typing import List, Dict, Any, Optional, Callable
from .config import Config
from .scraper import Scraper
from concurrent.futures import ThreadPoolExecutor, as_completed


class BatchScraper:
    """Batch scrape multiple URLs with concurrency control."""

    def __init__(self, config: Config = None):
        self.config = config or Config()

    def scrape_batch(self, urls: List[str], formats: List[str] = None,
                     max_concurrency: int = None, engine: str = None,
                     progress_callback: Callable = None) -> Dict[str, Any]:
        """Scrape multiple URLs in parallel.

        Args:
            urls: List of URLs to scrape
            formats: Output formats
            max_concurrency: Max parallel requests (default from config)
            engine: Force a specific engine
            progress_callback: Optional fn(url, index, total)

        Returns:
            Dict with "results" list and "stats"
        """
        formats = formats or ["markdown"]
        max_concurrency = max_concurrency or self.config.max_concurrency
        total = len(urls)
        results = []
        errors = []
        start = time.time()

        def _scrape_one(url: str, idx: int) -> Dict:
            scraper = Scraper(self.config)
            try:
                if progress_callback:
                    progress_callback(url, idx, total)
                result = scraper.scrape(url, formats=formats, engine=engine)
                result["_index"] = idx
                return result
            except Exception as e:
                return {
                    "_index": idx,
                    "error": str(e),
                    "metadata": {"url": url, "blocked": True, "error": str(e)}
                }
            finally:
                scraper.close()

        with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
            fut_map = {executor.submit(_scrape_one, url, i): (url, i)
                       for i, url in enumerate(urls)}
            for future in as_completed(fut_map):
                url, idx = fut_map[future]
                try:
                    result = future.result()
                    if "error" in result and result.get("error") and not result.get("metadata", {}).get("markdown"):
                        errors.append({"url": url, "error": result["error"]})
                    results.append(result)
                except Exception as e:
                    errors.append({"url": url, "error": str(e)})
                    results.append({"_index": idx, "error": str(e),
                                    "metadata": {"url": url, "error": str(e)}})

        # Sort by original index
        results.sort(key=lambda r: r.get("_index", 0))

        elapsed = time.time() - start
        return {
            "results": results,
            "stats": {
                "total": total,
                "success": total - len(errors),
                "errors": len(errors),
                "elapsed": round(elapsed, 2),
                "concurrency": max_concurrency,
            },
            "errors": errors if errors else None,
        }
