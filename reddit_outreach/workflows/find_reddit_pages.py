"""Workflow to find and save relevant Reddit pages for a product."""

import logging

from reddit_outreach.agents.product_page_finder import ProductPageFinder
from reddit_outreach.services.product_service import ProductService

logger = logging.getLogger(__name__)


class FindRedditPagesWorkflow:
    """Find and scrape Reddit pages for a product."""

    def __init__(self):
        """Initialize the workflow."""
        self.llm_providers = ["openai", "gemini", "grok"]
        self.product_service = ProductService()

    def execute(
        self, product_name: str, max_pages: int = 100, max_urls_per_provider: int = 200
    ):
        """
        Execute the workflow.

        Given a product, find, scrape, and save relevant Reddit pages.

        Args:
            product_name: Name of the product to find Reddit pages for
            max_pages: Target number of relevant pages to save
            max_urls_per_provider: Max candidate URLs to consider per provider

        Returns:
            dict with summary of results
        """
        logger.info(
            f"Starting workflow to find Reddit pages for product: {product_name}"
        )

        # Get or create product
        product, created = self.product_service.get_or_create(product_name)
        created_str = "created" if created else "existing"
        logger.info("Product: %s (%s)", product.name, created_str)

        # Step 1: Find + scrape pages using multiple LLMs.
        # ProductPageFinder saves ProductPage rows.
        logger.info("Step 1: Find + scrape Reddit pages using multiple LLMs...")
        pages = self._find_product_pages_all_llms(
            product_name,
            max_pages=max_pages,
            max_urls_per_provider=max_urls_per_provider,
        )

        if not pages:
            logger.warning(f"No relevant Reddit pages found for {product_name}")
            return {
                "product": product,
                "urls_found": 0,
                "pages_scraped": 0,
                "success": False,
                "message": "No relevant Reddit pages found",
            }

        # Deduplicate by URL
        pages_by_url = {p.url: p for p in pages}
        pages = list(pages_by_url.values())

        urls_found = len(pages)
        pages_scraped = len([p for p in pages if p.status == "scraped"])

        logger.info(
            f"Found {urls_found} unique ProductPage rows (scraped: {pages_scraped})"
        )

        return {
            "product": product,
            "urls_found": urls_found,
            "pages_scraped": pages_scraped,
            "pages": pages,
            "success": pages_scraped > 0,
            "message": (
                f"Successfully found {urls_found} page(s) and scraped "
                f"{pages_scraped} page(s)"
            ),
        }

    def _find_product_pages_all_llms(
        self, product_name: str, max_pages: int = 100, max_urls_per_provider: int = 200
    ):
        """
        Find + scrape ProductPages using all LLM providers and aggregate results.

        Args:
            product_name: Name of the product to search for
            max_pages: Stop after reaching this many unique pages
            max_urls_per_provider: Max candidate URLs to consider per provider

        Returns:
            list of ProductPage rows (may include duplicates across providers)
        """
        all_pages = []
        successful_providers = []
        failed_providers = []

        for llm_provider in self.llm_providers:
            try:
                logger.info(f"Trying {llm_provider} for product: {product_name}")
                page_finder = ProductPageFinder(
                    product=product_name, llm_option=llm_provider
                )
                pages = page_finder.find_product_pages_sync(
                    max_results=max_urls_per_provider
                )
                all_pages.extend(pages)

                logger.info(
                    f"{llm_provider} produced {len(pages)} ProductPage row(s) "
                    f"(total rows: {len(all_pages)})"
                )
                successful_providers.append(llm_provider)

                # Stop early if we already have enough (dedupe by URL)
                if len({p.url for p in all_pages}) >= max_pages:
                    logger.info(
                        f"Reached target of {max_pages} relevant pages, stopping early."
                    )
                    break

            except ValueError as e:
                # Missing API key - skip this provider
                logger.warning(f"Skipping {llm_provider}: {e}")
                failed_providers.append(f"{llm_provider} (missing API key)")
                continue
            except ImportError as e:
                # Package not installed - skip this provider
                logger.warning(f"Skipping {llm_provider}: {e}")
                failed_providers.append(f"{llm_provider} (package not installed)")
                continue
            except Exception as e:
                logger.warning(
                    f"Error using {llm_provider} to search for Reddit pages: {e}"
                )
                failed_providers.append(f"{llm_provider} (error: {str(e)[:50]})")
                continue

        if successful_providers:
            providers_str = ", ".join(successful_providers)
            logger.info(
                "Successfully used %s LLM provider(s): %s",
                len(successful_providers),
                providers_str,
            )
        if failed_providers:
            failed_str = ", ".join(failed_providers)
            logger.warning(
                "Failed to use %s LLM provider(s): %s",
                len(failed_providers),
                failed_str,
            )

        return all_pages
