"""Management command: find and save relevant product pages from Reddit."""

import logging

from django.core.management.base import BaseCommand, CommandError

from reddit_outreach.workflows.find_reddit_pages import FindRedditPagesWorkflow

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Find and scrape relevant Reddit pages for a given product."""

    help = "Find and scrape Reddit pages for a specific product"

    def add_arguments(self, parser):
        """Add CLI arguments."""
        parser.add_argument(
            "--product",
            type=str,
            required=True,
            help="Product name to search for",
        )
        parser.add_argument(
            "--max-pages",
            type=int,
            default=100,
            help="Target number of relevant Reddit pages to save (default: 100)",
        )
        parser.add_argument(
            "--max-urls",
            type=int,
            default=200,
            help=(
                "Maximum number of candidate Reddit URLs per LLM provider "
                "(default: 200)"
            ),
        )

    def handle(self, *args, **options):
        """Run the command."""
        product_name = options["product"]
        max_pages = options.get("max_pages", 100)
        max_urls = options.get("max_urls", 200)

        if not product_name:
            raise CommandError("Product name is required")

        self.stdout.write(
            self.style.SUCCESS(f"Finding Reddit pages for product: {product_name}")
        )
        self.stdout.write("Using LLM providers: OpenAI, Gemini, Grok")
        self.stdout.write(f"Target relevant pages: {max_pages}")
        self.stdout.write(f"Candidate URLs per LLM provider: {max_urls}")

        try:
            # Find and scrape Reddit pages
            find_pages_workflow = FindRedditPagesWorkflow()
            result = find_pages_workflow.execute(
                product_name,
                max_pages=max_pages,
                max_urls_per_provider=max_urls,
            )

            # Display results
            self.stdout.write(self.style.SUCCESS("\n=== Results ==="))
            self.stdout.write(f"Product: {result['product'].name}")
            self.stdout.write(f"URLs Found: {result['urls_found']}")
            self.stdout.write(f"Pages Scraped: {result['pages_scraped']}")
            self.stdout.write(f"Status: {'Success' if result['success'] else 'Failed'}")
            self.stdout.write(f"Message: {result['message']}")

            if result["success"]:
                self.stdout.write(
                    self.style.SUCCESS(
                        "\n✓ Successfully found and scraped Reddit pages!"
                    )
                )
                if result.get("pages"):
                    self.stdout.write("\nScraped pages:")
                    for page in result["pages"]:
                        self.stdout.write(f"  - {page.url}")
            else:
                self.stdout.write(self.style.WARNING(f'\n⚠ {result["message"]}'))

        except Exception as e:
            logger.error(f"Error finding product pages: {e}", exc_info=True)
            raise CommandError(f"Command failed: {str(e)}")
