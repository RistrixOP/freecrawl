"""
Diff tracking between scrapes.
Stores previous scrape, compares, returns diff.
"""
import json, os, time, hashlib
from typing import Dict, Any, Optional, List
from difflib import unified_diff, HtmlDiff
from .config import Config
from .scraper import Scraper


class ChangeTracker:
    """Track changes in web page content over time."""

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.scraper = Scraper(self.config)
        os.makedirs(self.config.changetracking_dir, exist_ok=True)

    def _storage_path(self, url: str) -> str:
        """Get the storage file path for a URL."""
        key = hashlib.md5(url.encode()).hexdigest()
        return os.path.join(self.config.changetracking_dir, f"{key}.json")

    def _load_snapshot(self, url: str) -> Optional[Dict]:
        """Load previous snapshot for a URL."""
        path = self._storage_path(url)
        if os.path.exists(path):
            try:
                with open(path) as f:
                    return json.load(f)
            except:
                pass
        return None

    def _save_snapshot(self, url: str, data: Dict):
        """Save current snapshot for a URL."""
        path = self._storage_path(url)
        with open(path, 'w') as f:
            json.dump(data, f, default=str)

    def snapshot(self, url: str, formats: List[str] = None,
                 store_content: bool = True) -> Dict[str, Any]:
        """Create a snapshot of a URL and optionally compare with previous.

        Args:
            url: URL to snapshot
            formats: Scrape formats
            store_content: Store content for future diffing

        Returns:
            Dict with snapshot data and optional diff
        """
        formats = formats or ["markdown", "text"]
        previous = self._load_snapshot(url)

        # Scrape current state
        page = self.scraper.scrape(url, formats=formats)
        current_content = page.get("markdown") or page.get("text") or ""

        snapshot_data = {
            "url": url,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "title": page.get("title", ""),
            "content": current_content if store_content else "",
            "content_length": len(current_content),
            "metadata": page.get("metadata", {}),
        }

        diff_result = None
        if previous and previous.get("content"):
            diff_result = self._compute_diff(
                previous["content"],
                current_content,
                previous.get("title", url),
                page.get("title", url),
            )

        # Save current snapshot
        if store_content:
            self._save_snapshot(url, snapshot_data)

        result = {
            "url": url,
            "current": {
                "timestamp": snapshot_data["timestamp"],
                "title": snapshot_data["title"],
                "content_length": snapshot_data["content_length"],
                "content": current_content,
            },
            "has_previous": previous is not None,
            "metadata": snapshot_data["metadata"],
        }

        if diff_result:
            result["diff"] = diff_result

        return result

    def _compute_diff(self, old_text: str, new_text: str,
                      old_title: str = "", new_title: str = "") -> Dict[str, Any]:
        """Compute diff between two text contents."""
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)

        diff_lines = list(unified_diff(
            old_lines, new_lines,
            fromfile=old_title or "previous",
            tofile=new_title or "current",
            lineterm="",
        ))

        # Count changes
        additions = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
        deletions = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))

        # HTML diff
        html_diff = HtmlDiff(wrapcolumn=80).make_file(old_lines, new_lines,
                                                       fromdesc="Previous",
                                                       todesc="Current")

        return {
            "additions": additions,
            "deletions": deletions,
            "total_changes": additions + deletions,
            "diff_text": "\n".join(diff_lines),
            "diff_html": html_diff,
            "old_length": len(old_text),
            "new_length": len(new_text),
        }

    def get_history(self, url: str) -> Optional[Dict]:
        """Get stored snapshot history for a URL."""
        return self._load_snapshot(url)

    def clear_history(self, url: str = None):
        """Clear stored snapshots."""
        if url:
            path = self._storage_path(url)
            if os.path.exists(path):
                os.remove(path)
        else:
            import shutil
            shutil.rmtree(self.config.changetracking_dir, ignore_errors=True)
            os.makedirs(self.config.changetracking_dir, exist_ok=True)

    def close(self):
        self.scraper.close()
