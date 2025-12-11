from reddit_outreach.models import ProductPage
from django.utils import timezone
import re


class ProductPageService:
    @staticmethod
    def extract_subreddit(url):
        """Extract subreddit name from Reddit URL."""
        try:
            # Pattern: reddit.com/r/subreddit_name/...
            match = re.search(r'/r/([^/]+)', url)
            if match:
                return match.group(1)
            return 'unknown'
        except Exception:
            return 'unknown'

    @staticmethod
    def create(product, url, html=None, text=None, status='pending'):
        """Create a new ProductPage."""
        subreddit = ProductPageService.extract_subreddit(url)
        
        page, created = ProductPage.objects.get_or_create(
            product=product,
            url=url,
            defaults={
                'subreddit': subreddit,
                'scraped_html': html or '',
                'scraped_text': text or '',
                'status': status,
            }
        )
        
        if not created and html:
            # Update existing page
            page.scraped_html = html
            page.scraped_text = text or ''
            page.status = status
            page.save()
        
        return page, created

    @staticmethod
    def update_status(page, status):
        """Update the status of a ProductPage."""
        page.status = status
        if status == 'scraped':
            page.scraped_at = timezone.now()
        page.save()

    @staticmethod
    def get_by_product(product):
        """Get all pages for a product."""
        return ProductPage.objects.filter(product=product)

    @staticmethod
    def get_pending():
        """Get all pending pages."""
        return ProductPage.objects.filter(status='pending')

