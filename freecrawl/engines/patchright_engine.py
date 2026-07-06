"""Patchright engine — undetected browser for DataDome, Cloudflare, etc."""
import time, os
from .base import BaseEngine, ScrapeResult
from patchright.sync_api import sync_playwright

class PatchrightEngine(BaseEngine):
    name = "patchright"
    def __init__(self, config):
        super().__init__(config)
        self._pw = None
        self._browser = None
        self._context = None

    def _ensure_browser(self):
        if self._context is not None:
            return
        self._pw = sync_playwright().start()
        launch_args = ["--disable-blink-features=AutomationControlled"]
        if self.config.block_ads:
            launch_args.append("--load-extension=/tmp/freecrawl-ubo")
        proxy_conf = {"server": self.config.proxy_url} if self.config.proxy_url else None
        if self.config.user_data_dir:
            self._context = self._pw.chromium.launch_persistent_context(
                user_data_dir=self.config.user_data_dir,
                channel=self.config.channel if self.config.channel != "chromium" else None,
                headless=self.config.headless,
                no_viewport=True,
                args=launch_args,
                proxy=proxy_conf,
            )
        else:
            self._browser = self._pw.chromium.launch(
                channel=self.config.channel if self.config.channel != "chromium" else None,
                headless=self.config.headless,
                args=launch_args,
                proxy=proxy_conf,
            )
            self._context = self._browser.new_context(
                viewport={"width": self.config.viewport_width, "height": self.config.viewport_height},
                locale=self.config.locale,
            )

    def scrape(self, url, actions=None, screenshot=False, wait_for=0,
               mobile=False, include_tags=None, exclude_tags=None,
               headers=None, **kwargs) -> ScrapeResult:
        start = time.time()
        result = ScrapeResult(url=url, engine_used=self.name)
        try:
            self._ensure_browser()
            ctx = self._context
            if mobile:
                # Create a mobile context overlay
                page = ctx.new_page()
                page.set_viewport_size({"width": 390, "height": 844})
            else:
                page = ctx.new_page()
            if headers:
                page.set_extra_http_headers(headers)
            page.goto(url, timeout=self.config.timeout, wait_until=self.config.wait_until)
            time.sleep(self.config.wait_after_load)
            if wait_for:
                time.sleep(wait_for / 1000.0)
            # Execute custom JS actions
            if actions:
                for action in actions:
                    atype = action.get("type")
                    if atype == "click":
                        page.click(action["selector"], timeout=5000)
                        time.sleep(action.get("delay", 1))
                    elif atype == "scroll":
                        page.evaluate(f"window.scrollBy(0, {action.get('amount', 500)})")
                        time.sleep(0.5)
                    elif atype == "wait":
                        try: page.wait_for_selector(action["selector"], timeout=action.get("timeout", 10000))
                        except: pass
                    elif atype == "type":
                        page.fill(action["selector"], action["text"])
                    elif atype == "evaluate":
                        page.evaluate(action["script"])
                    elif atype == "press":
                        page.keyboard.press(action["key"])
                    elif atype == "screenshot":
                        ss_path = f"/tmp/freecrawl_screenshot_{int(time.time()*1000)}.png"
                        page.screenshot(path=ss_path, full_page=action.get("fullPage", False))
                        result.screenshots.append(ss_path)
            # Include/exclude tags: remove excluded elements before extracting
            if exclude_tags:
                for sel in exclude_tags:
                    page.evaluate(f"""() => {{ document.querySelectorAll('{sel}').forEach(e => e.remove()); }}""")
            if include_tags:
                # Extract only matching elements
                html_parts = page.evaluate(f"""() => {{
                    let els = document.querySelectorAll('{', '.join(include_tags)}');
                    return Array.from(els).map(e => e.outerHTML).join('\\n');
                }}""")
                result.html = html_parts or page.content()
            else:
                result.html = page.content()
            result.title = page.title()
            result.text = page.evaluate("document.body ? document.body.innerText : ''")
            result.status_code = 200
            for c in page.context.cookies():
                result.cookies[c["name"]] = c["value"]
            if screenshot:
                ss_path = f"/tmp/freecrawl_screenshot_{int(time.time())}.png"
                page.screenshot(path=ss_path, full_page=True)
                result.screenshots.append(ss_path)
            page.close()
        except Exception as e:
            result.error = str(e)
        result.elapsed = time.time() - start
        return result

    def close(self):
        try:
            if self._context: self._context.close()
        except: pass
        try:
            if self._browser: self._browser.close()
        except: pass
        try:
            if self._pw: self._pw.stop()
        except: pass
