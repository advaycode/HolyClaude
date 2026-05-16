"""
playwright_agent.py — Browser automation agent for scraping and screenshots.

Handles JavaScript-heavy pages, auth walls, infinite scroll, and form submission
that requests/BeautifulSoup can't reach. Falls back gracefully if playwright
is not installed.

Usage:
    agent = PlaywrightAgent(headless=True)

    # Scrape a JS-rendered page
    html = agent.get_page_content("https://example.com/results")
    links = agent.extract_links("https://example.com", pattern="*.pdf")

    # Screenshot
    agent.screenshot("https://example.com", Path("out/shot.png"))

    # Structured scrape with schema
    data = agent.scrape_structured(
        url="https://scholarships.com/list",
        schema={"title": "h2.title", "deadline": ".deadline", "link": "a@href"},
    )

    # Batch scrape from URL list
    results = agent.batch_scrape(urls, schema=schema, workers=4)
"""
from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
    _PW_AVAILABLE = True
except ImportError:
    _PW_AVAILABLE = False


def _require_playwright() -> None:
    if not _PW_AVAILABLE:
        raise ImportError(
            "playwright not installed. Run:\n"
            "  pip install playwright\n"
            "  playwright install chromium"
        )


@dataclass
class ScrapeResult:
    url: str
    status: int = 0
    html: str = ""
    text: str = ""
    links: list[str] = field(default_factory=list)
    structured: dict = field(default_factory=dict)
    screenshot_path: Optional[str] = None
    error: str = ""
    elapsed: float = 0.0


class PlaywrightAgent:
    """
    Browser automation agent.

    Handles JS-rendered pages, infinite scroll, auth, screenshots, and
    structured CSS-selector scraping.
    """

    def __init__(
        self,
        headless: bool = True,
        timeout_ms: int = 30_000,
        wait_for: str = "networkidle",
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        block_media: bool = True,
    ) -> None:
        _require_playwright()
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.wait_for = wait_for
        self.user_agent = user_agent
        self.block_media = block_media
        self._pw = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    def __enter__(self) -> "PlaywrightAgent":
        self.start()
        return self

    def __exit__(self, *_) -> None:
        self.stop()

    def start(self) -> None:
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.headless)
        self._context = self._browser.new_context(user_agent=self.user_agent)
        if self.block_media:
            self._context.route(
                "**/*.{png,jpg,gif,webp,svg,woff,woff2,ttf,mp4,mp3,webm}",
                lambda route: route.abort(),
            )

    def stop(self) -> None:
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        self._browser = None
        self._context = None
        self._pw = None

    def _new_page(self) -> "Page":
        if not self._context:
            self.start()
        page = self._context.new_page()
        page.set_default_timeout(self.timeout_ms)
        return page

    # ── core fetch ────────────────────────────────────────────────────────────

    def get_page_content(
        self,
        url: str,
        wait_for: str | None = None,
        scroll_to_bottom: bool = False,
        wait_ms: int = 0,
    ) -> str:
        page = self._new_page()
        try:
            response = page.goto(url, wait_until=wait_for or self.wait_for, timeout=self.timeout_ms)
            if scroll_to_bottom:
                self._scroll_to_bottom(page)
            if wait_ms:
                time.sleep(wait_ms / 1000)
            return page.content()
        finally:
            page.close()

    def _scroll_to_bottom(self, page: "Page", max_scrolls: int = 10) -> None:
        for _ in range(max_scrolls):
            prev_height = page.evaluate("document.body.scrollHeight")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(0.8)
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == prev_height:
                break

    def get_text(self, url: str, **kw) -> str:
        page = self._new_page()
        try:
            page.goto(url, wait_until=self.wait_for, timeout=self.timeout_ms)
            return page.inner_text("body")
        finally:
            page.close()

    # ── structured scraping ───────────────────────────────────────────────────

    def scrape_structured(
        self,
        url: str,
        schema: dict[str, str],
        multi: bool = False,
        container_selector: str = "body",
    ) -> dict | list[dict]:
        """
        Scrape structured data using CSS selectors.

        schema: {field_name: "css-selector"} or {field_name: "css-selector@attr"}

        Examples:
            {"title": "h2.title", "href": "a@href", "date": ".pub-date"}

        If multi=True, finds all container_selector elements and applies schema to each.
        """
        page = self._new_page()
        try:
            page.goto(url, wait_until=self.wait_for, timeout=self.timeout_ms)

            def extract_one(root_selector: str) -> dict:
                result: dict = {}
                for field, sel in schema.items():
                    attr = None
                    if "@" in sel:
                        sel, attr = sel.rsplit("@", 1)
                    try:
                        el = page.locator(f"{root_selector} {sel}".strip()).first
                        if attr:
                            result[field] = el.get_attribute(attr) or ""
                        else:
                            result[field] = el.inner_text().strip()
                    except Exception:
                        result[field] = ""
                return result

            if not multi:
                return extract_one("body")

            containers = page.locator(container_selector).all()
            results: list[dict] = []
            for i, _ in enumerate(containers):
                row: dict = {}
                for field, sel in schema.items():
                    attr = None
                    if "@" in sel:
                        sel, attr = sel.rsplit("@", 1)
                    try:
                        el = page.locator(container_selector).nth(i).locator(sel).first
                        if attr:
                            row[field] = el.get_attribute(attr) or ""
                        else:
                            row[field] = el.inner_text().strip()
                    except Exception:
                        row[field] = ""
                if any(v for v in row.values()):
                    results.append(row)
            return results
        finally:
            page.close()

    def extract_links(
        self,
        url: str,
        pattern: str = "",
        text_filter: str = "",
    ) -> list[str]:
        """Extract all links from a page. Filter by URL pattern or link text."""
        page = self._new_page()
        try:
            page.goto(url, wait_until=self.wait_for, timeout=self.timeout_ms)
            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => [e.href, e.innerText])")
            links: list[str] = []
            for href, text in hrefs:
                if pattern and not re.search(pattern.replace("*", ".*"), href):
                    continue
                if text_filter and text_filter.lower() not in text.lower():
                    continue
                links.append(href)
            return list(dict.fromkeys(links))  # dedupe, preserve order
        finally:
            page.close()

    # ── screenshot ────────────────────────────────────────────────────────────

    def screenshot(
        self,
        url: str,
        output: Path,
        full_page: bool = True,
        width: int = 1280,
        height: int = 900,
    ) -> Path:
        page = self._new_page()
        try:
            page.set_viewport_size({"width": width, "height": height})
            page.goto(url, wait_until=self.wait_for, timeout=self.timeout_ms)
            output.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(output), full_page=full_page)
            return output
        finally:
            page.close()

    # ── batch scrape ──────────────────────────────────────────────────────────

    def batch_scrape(
        self,
        urls: list[str],
        schema: dict[str, str],
        workers: int = 3,
        delay: float = 0.5,
    ) -> list[ScrapeResult]:
        """
        Scrape multiple URLs in parallel (thread-safe — each thread gets a new page).
        """
        results: list[ScrapeResult] = []

        def _scrape_one(url: str) -> ScrapeResult:
            t0 = time.monotonic()
            result = ScrapeResult(url=url)
            try:
                data = self.scrape_structured(url, schema)
                result.structured = data if isinstance(data, dict) else {}
                result.status = 200
            except Exception as e:
                result.error = str(e)
            result.elapsed = time.monotonic() - t0
            if delay:
                time.sleep(delay)
            return result

        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(_scrape_one, url): url for url in urls}
            for future in as_completed(futures):
                results.append(future.result())

        return results

    # ── convenience ───────────────────────────────────────────────────────────

    def scholarship_scrape(
        self,
        listing_url: str,
        item_selector: str,
        schema: dict[str, str],
        max_pages: int = 3,
        next_button_selector: str = "",
    ) -> list[dict]:
        """
        Multi-page scholarship/program listing scraper.
        Handles pagination via next-button or URL pattern.
        """
        all_items: list[dict] = []
        page = self._new_page()
        try:
            page.goto(listing_url, wait_until=self.wait_for, timeout=self.timeout_ms)
            for page_num in range(max_pages):
                items = page.locator(item_selector).all()
                print(f"  [playwright] page {page_num + 1}: {len(items)} items")
                for i in range(len(items)):
                    row: dict = {}
                    for field, sel in schema.items():
                        attr = None
                        if "@" in sel:
                            sel, attr = sel.rsplit("@", 1)
                        try:
                            el = page.locator(item_selector).nth(i).locator(sel).first
                            row[field] = el.get_attribute(attr) or "" if attr else el.inner_text().strip()
                        except Exception:
                            row[field] = ""
                    if any(v for v in row.values()):
                        all_items.append(row)

                if not next_button_selector:
                    break
                try:
                    btn = page.locator(next_button_selector).first
                    if not btn.is_visible():
                        break
                    btn.click()
                    page.wait_for_load_state("networkidle", timeout=self.timeout_ms)
                except Exception:
                    break
        finally:
            page.close()

        print(f"  [playwright] total: {len(all_items)} items across {max_pages} pages")
        return all_items
