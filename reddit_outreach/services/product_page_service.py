"""CRUD helpers for `ProductPage`."""

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from django.db import IntegrityError, transaction
from django.utils import timezone

from reddit_outreach.models import ProductPage


class ProductPageService:
    """Service for creating and querying `ProductPage` rows."""

    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize a Reddit URL to a canonical form for deduplication."""
        if not url:
            return ""

        url = url.strip()

        # Ensure scheme (LLMs sometimes omit it).
        if url.startswith("reddit.com/") or url.startswith("www.reddit.com/"):
            url = f"https://{url}"

        parsed = urlparse(url)
        netloc = (parsed.netloc or "").lower()
        if netloc in {"old.reddit.com", "new.reddit.com", "reddit.com"}:
            netloc = "www.reddit.com"

        # Drop common tracking params but keep others (rarely used on Reddit).
        query_params = [
            (k, v) for (k, v) in parse_qsl(parsed.query) if not k.startswith("utm_")
        ]
        query = urlencode(query_params, doseq=True)

        # Normalize path: remove trailing slash (except root).
        path = parsed.path or ""
        if path != "/":
            path = path.rstrip("/")

        normalized = parsed._replace(
            netloc=netloc, scheme="https", path=path, query=query
        )
        return urlunparse(normalized)

    @staticmethod
    def extract_subreddit(url):
        """Extract subreddit name from Reddit URL."""
        try:
            url = ProductPageService.normalize_url(url)
            # Pattern: reddit.com/r/subreddit_name/...
            match = re.search(r"/r/([^/]+)", url)
            if match:
                return match.group(1)
            return "unknown"
        except Exception:
            return "unknown"

    @staticmethod
    def create(product, url, html=None, text=None, status="pending"):
        """Create a new ProductPage."""
        url = ProductPageService.normalize_url(url)
        subreddit = ProductPageService.extract_subreddit(url)

        try:
            with transaction.atomic():
                page, created = ProductPage.objects.get_or_create(
                    product=product,
                    url=url,
                    defaults={
                        "subreddit": subreddit,
                        "scraped_html": html or "",
                        "scraped_text": text or "",
                        "status": status,
                    },
                )
        except IntegrityError:
            # In case of a race, fall back to fetching the existing row.
            page = ProductPage.objects.get(product=product, url=url)
            created = False

        if not created and html:
            # Update existing page
            page.scraped_html = html
            page.scraped_text = text or ""
            page.status = status
            page.save()

        return page, created

    @staticmethod
    def update_status(page, status):
        """Update the status of a ProductPage."""
        page.status = status
        if status == "scraped":
            page.scraped_at = timezone.now()
        page.save()

    @staticmethod
    def get_by_product(product):
        """Get all pages for a product."""
        return ProductPage.objects.filter(product=product)

    @staticmethod
    def get_pending():
        """Get all pending pages."""
        return ProductPage.objects.filter(status="pending")
