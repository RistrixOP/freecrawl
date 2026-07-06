"""Content extraction: Markdown, HTML, text, JSON-LD, links, images, metadata, summary, product, menu."""
import re, json
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup, Tag
from .config import Config

class Extractor:
    def __init__(self, config: Config):
        self.config = config

    def extract(self, result, formats=None, extract_schema=None) -> Dict[str, Any]:
        formats = formats or ["markdown"]
        out = {}
        html = result.html or ""
        if not html:
            return out

        if "html" in formats or "rawHtml" in formats:
            out["html"] = html
        if "text" in formats:
            out["text"] = result.text or ""
        if "markdown" in formats:
            out["markdown"] = self._to_markdown(result)
        if "links" in formats:
            out["links"] = self._extract_links(html, result.url)
        if "images" in formats:
            out["images"] = self._extract_images(html, result.url)
        if "json" in formats or "jsonld" in formats:
            out["json"] = self._extract_json_ld(html)
        if "metadata" in formats:
            out["metadata"] = self._extract_meta(html, result)
        if "summary" in formats:
            out["summary"] = self._summarize(result)
        if "product" in formats:
            prod = self._extract_product(html)
            if prod: out["product"] = prod
        if "menu" in formats:
            menu = self._extract_menu(html)
            if menu: out["menu"] = menu
        if "branding" in formats:
            brand = self._extract_branding(html, result.url)
            if brand: out["branding"] = brand
        if extract_schema:
            out["extract"] = self._css_extract(html, extract_schema)
        out["title"] = result.title or self._extract_title(html)
        return out

    def _to_markdown(self, result) -> str:
        try:
            markdown = __import__("trafilatura").extract(
                result.html, output_format="markdown",
                include_links=self.config.include_links,
                include_images=self.config.include_images,
                include_tables=True, favor_recall=True,
            )
            if markdown: return markdown
        except: pass
        return result.text or ""

    def _extract_links(self, html, base_url) -> List[Dict]:
        from urllib.parse import urljoin
        soup = BeautifulSoup(html, "lxml")
        links, seen = [], set()
        for a in soup.find_all("a", href=True):
            full = __import__("urllib.parse").urljoin(base_url, a["href"])
            if full not in seen:
                seen.add(full)
                links.append({"text": a.get_text(strip=True), "url": full})
        return links

    def _extract_images(self, html, base_url) -> List[Dict]:
        from urllib.parse import urljoin
        soup = BeautifulSoup(html, "lxml")
        imgs, seen = [], set()
        for img in soup.find_all("img", src=True):
            full = urljoin(base_url, img["src"])
            if full not in seen:
                seen.add(full)
                imgs.append({"url": full, "alt": img.get("alt", "")})
        return imgs

    def _extract_json_ld(self, html) -> List[Dict]:
        soup = BeautifulSoup(html, "lxml")
        results = []
        for script in soup.find_all("script", type="application/ld+json"):
            try: results.append(json.loads(script.string.strip()))
            except: pass
        for script in soup.find_all("script", id="__NEXT_DATA__"):
            try: results.append(json.loads(script.string.strip()))
            except: pass
        return results

    def _extract_meta(self, html, result) -> Dict:
        soup = BeautifulSoup(html, "lxml")
        meta = {}
        for tag in soup.find_all("meta"):
            name = tag.get("name") or tag.get("property") or tag.get("itemprop")
            content = tag.get("content")
            if name and content: meta[name] = content
        meta["title"] = result.title or self._extract_title(html)
        meta["statusCode"] = result.status_code
        return meta

    def _extract_title(self, html) -> str:
        soup = BeautifulSoup(html, "lxml")
        if soup.title and soup.title.string: return soup.title.string.strip()
        return ""

    def _css_extract(self, html, schema: Dict) -> Dict:
        soup = BeautifulSoup(html, "lxml")
        result = {}
        for field, selector in schema.items():
            el = soup.select_one(selector)
            result[field] = el.get_text(strip=True) if el else None
        return result

    def _summarize(self, result) -> str:
        """Generate a summary using the configured LLM."""
        if not self.config.llm_api_key:
            # Fallback: first 500 chars of text
            text = result.text or ""
            return text[:500] + ("..." if len(text) > 500 else "")
        try:
            import httpx
            text = (result.text or "")[:4000]
            r = httpx.post(
                f"{self.config.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.config.llm_api_key}"},
                json={
                    "model": self.config.llm_model,
                    "messages": [
                        {"role": "system", "content": "Summarize the following web page content in 2-3 sentences."},
                        {"role": "user", "content": text},
                    ],
                    "max_tokens": 200,
                },
                timeout=30,
            )
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Summary error: {e}"

    def _extract_product(self, html) -> Optional[Dict]:
        """Extract product information from e-commerce pages."""
        # Try JSON-LD Product first
        jsonld = self._extract_json_ld(html)
        for block in jsonld:
            if isinstance(block, dict):
                t = block.get("@type", "")
                if t == "Product" or (isinstance(t, str) and "Product" in t):
                    offers = block.get("offers", {})
                    return {
                        "name": block.get("name"),
                        "price": offers.get("price") if isinstance(offers, dict) else None,
                        "currency": offers.get("priceCurrency") if isinstance(offers, dict) else None,
                        "availability": offers.get("availability") if isinstance(offers, dict) else None,
                        "image": block.get("image"),
                        "description": block.get("description"),
                        "brand": block.get("brand", {}).get("name") if isinstance(block.get("brand"), dict) else block.get("brand"),
                        "rating": block.get("aggregateRating", {}).get("ratingValue") if isinstance(block.get("aggregateRating"), dict) else None,
                        "reviews": block.get("aggregateRating", {}).get("reviewCount") if isinstance(block.get("aggregateRating"), dict) else None,
                    }
        # Fallback: Open Graph product tags
        soup = BeautifulSoup(html, "lxml")
        og = {}
        for tag in soup.find_all("meta"):
            prop = tag.get("property", "")
            if prop.startswith("og:product:") or prop.startswith("product:"):
                og[prop] = tag.get("content", "")
        return og if og else None

    def _extract_menu(self, html) -> Optional[List[Dict]]:
        """Extract restaurant menu items."""
        soup = BeautifulSoup(html, "lxml")
        items = []
        # Common menu selectors
        for sel in [".menu-item", "[class*='menuItem']", ".dish", ".food-item",
                     "[data-menu-item]", ".menu-list-item", ".menu__item"]:
            elements = soup.select(sel)
            if elements:
                for el in elements:
                    name_el = el.select_one(".name, .title, h3, h4, strong")
                    price_el = el.select_one(".price, .cost, [class*='price']")
                    desc_el = el.select_one(".description, .desc, p")
                    items.append({
                        "name": name_el.get_text(strip=True) if name_el else None,
                        "price": price_el.get_text(strip=True) if price_el else None,
                        "description": desc_el.get_text(strip=True) if desc_el else None,
                    })
                break
        return items if items else None

    def _extract_branding(self, html, base_url) -> Optional[Dict]:
        """Extract branding info: logo, colors, fonts."""
        from urllib.parse import urljoin
        soup = BeautifulSoup(html, "lxml")
        branding = {}
        # Logo
        logo = soup.select_one("link[rel*='icon'], link[rel='shortcut icon']")
        if logo: branding["favicon"] = urljoin(base_url, logo.get("href", ""))
        og_image = soup.select_one("meta[property='og:image']")
        if og_image: branding["ogImage"] = og_image.get("content")
        # Theme color
        theme = soup.select_one("meta[name='theme-color']")
        if theme: branding["themeColor"] = theme.get("content")
        # Site name
        og_site = soup.select_one("meta[property='og:site_name']")
        if og_site: branding["siteName"] = og_site.get("content")
        return branding if branding else None

    def extract_structured(self, html, schema: Dict, base_url="") -> List[Dict]:
        soup = BeautifulSoup(html, "lxml")
        items = []
        for el in soup.select(schema.get("selector", "")):
            item = {}
            for field, sel in schema.get("fields", {}).items():
                child = el.select_one(sel)
                item[field] = child.get_text(strip=True) if child else None
            items.append(item)
        return items
