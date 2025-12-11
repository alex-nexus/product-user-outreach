from dataclasses import dataclass
from typing import Optional

import html2text
from playwright.async_api import async_playwright
from tenacity import retry, stop_after_attempt, wait_random_exponential


@dataclass
class WebPageScraper:
    url: str
    raw_html: Optional[str] = None
    raw_text: Optional[str] = None

    @retry(
        wait=wait_random_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(3),
    )
    async def scrape_page_html(self) -> str:
        try:
            raw_html = await self._scrape_html_by_playwright()
            if self.is_valid_page(raw_html):
                print(f"+ Playwright succeeded: {self.url}")
                self.raw_html = raw_html
                return self.raw_html

            length = len(raw_html) if raw_html else 0
            print(f"  - Playwright failed (length: {length}): {self.url}")
            return ""
        except Exception as e:
            print(f"  - Scraping failed: {e}")
            return ""

    async def _scrape_html_by_playwright(self) -> str:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(self.url, wait_until="networkidle", timeout=30000)
                html = await page.content()
                await browser.close()
                return html
        except Exception as e:
            print(f"Playwright error: {e}")
            return ""

    def is_valid_page(self, html: str) -> bool:
        """Validate page by checking text content instead of HTML."""
        if not html:
            return False

        # Convert HTML to text for validation
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        text = h.handle(html)

        # Check text length - error pages usually have very little text
        if len(text.strip()) < 200:
            return False

        text_lower = text.lower()

        # For pages with substantial text (>1000 chars), trust they're valid
        # Only check for error patterns if text is relatively short
        if len(text) < 1000:
            # Check for common error page patterns in early text
            first_500 = text_lower[:500]
            error_patterns = [
                "404",
                "page not found",
                "not found",
                "error 404",
                "access denied",
                "forbidden",
            ]
            # Only reject if multiple error indicators are present
            # (to avoid false positives)
            error_count = sum(1 for pattern in error_patterns if pattern in first_500)
            if error_count >= 2:
                return False

        return True

    def scrape_page_text(self) -> str:
        if not self.raw_html:
            return ""
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        self.raw_text = h.handle(self.raw_html)
        return self.raw_text
