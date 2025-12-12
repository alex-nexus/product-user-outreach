"""Find, scrape, classify, and save relevant Reddit pages for a product."""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import List

from asgiref.sync import sync_to_async
from pydantic import BaseModel, Field

from reddit_outreach.agents.product_page_classifier import ProductPageClassifier
from reddit_outreach.clients.llm import BaseLLM, create_llm_client
from reddit_outreach.models import ProductPage
from reddit_outreach.services.product_page_service import ProductPageService
from reddit_outreach.services.product_service import ProductService
from reddit_outreach.services.web_page_scraper import WebPageScraper

logger = logging.getLogger(__name__)


class RedditUrlsResponse(BaseModel):
    """Structured response model for Reddit URLs."""

    urls: List[str] = Field(description="List of Reddit URLs related to the product")


@dataclass
class ProductPageFinder:
    """LLM agent to find and save relevant Reddit product pages via web search."""

    product: str
    llm_option: str = "openai"
    llm: BaseLLM = field(init=False, repr=False)
    product_service: ProductService = field(default_factory=ProductService, repr=False)
    product_page_service: ProductPageService = field(
        default_factory=ProductPageService, repr=False
    )
    classifier: ProductPageClassifier = field(init=False, repr=False)

    def __post_init__(self):
        """Initialize the LLM client after dataclass initialization."""
        self.llm_option = self.llm_option.lower()
        self.llm = create_llm_client(
            provider=self.llm_option,
            enable_web_search=True,
        )
        # Use OpenAI classifier by default (no web search)
        self.classifier = ProductPageClassifier(
            product=self.product, llm_option="openai"
        )

    async def find_product_pages(self, max_results: int = 20) -> List[ProductPage]:
        """
        Find Reddit product pages for the given product.

        Save and return ProductPage rows.

        Uses the LLM's built-in web search to find Reddit URLs, then scrapes each URL
        and upserts a ProductPage row (status: scraped). Irrelevant pages are not saved.

        Args:
            max_results: Maximum number of Reddit URLs to find/scrape

        Returns:
            List of ProductPage objects (created/updated)
        """
        try:
            logger.info(
                "Finding Reddit pages for product: %s using %s",
                self.product,
                self.llm_option,
            )

            product_obj, _ = await sync_to_async(
                self.product_service.get_or_create, thread_sensitive=True
            )(self.product)

            system_prompt = (
                "You find Reddit URLs about a product. "
                "Use web search. Return only URLs on reddit.com "
                "(including www/old/new). "
                "Prefer direct post/comment URLs. Avoid login pages and non-Reddit "
                "domains."
            )

            prompt = (
                "Find Reddit URLs where users discuss or mention the product "
                f'"{self.product}".\n\n'
                "Use web search queries like:\n"
                f"- site:reddit.com {self.product}\n"
                f'- site:reddit.com ("{self.product}" OR '
                f"\"{self.product.replace('.', ' ')}\")\n\n"
                "Requirements:\n"
                "- Return only reddit.com URLs (including www/old/new).\n"
                "- Prefer /r/*/comments/* and direct discussion threads.\n"
                "- Do NOT invent URLs. Only return URLs that appear in actual "
                "web search results.\n"
                f"- Provide at least {max_results} unique URLs if possible.\n\n"
                "Output as a plain list of URLs, one per line."
            )

            # Run the LLM with web search enabled
            response = await self.llm.run(
                prompt=prompt,
                system_prompt=system_prompt,
            )

            response_text = str(response)
            # Extract URLs from the response
            urls = self._extract_urls(response_text)

            # If no URLs found, retry with a broader query + explicit instruction
            if not urls:
                logger.info(
                    "No URLs extracted from initial response; retrying. "
                    "Response snippet: %r",
                    response_text[:400],
                )
                retry_prompt = (
                    f'Find Reddit URLs about the product "{self.product}".\n\n'
                    "You MUST use web search and return reddit.com URLs.\n"
                    "Do NOT invent URLs.\n\n"
                    "Try multiple queries and synonyms:\n"
                    "- fyxer\n"
                    "- fyxer ai\n"
                    "- fyxer.ai\n"
                    "- fyxer email assistant\n"
                    "- fyxer outlook\n"
                    "- fyxer gmail\n"
                    '- "fyxer" reddit\n'
                    '- "fyxer.ai" reddit\n'
                    "- site:reddit.com fyxer\n\n"
                    f"Return up to {max_results} unique URLs, one per line. "
                    "If you truly find none, return an empty list."
                )
                response2 = await self.llm.run(
                    prompt=retry_prompt, system_prompt=system_prompt
                )
                response2_text = str(response2)
                urls = self._extract_urls(response2_text)
                if not urls:
                    logger.info(
                        "Still no URLs after retry. Response snippet: %r",
                        response2_text[:400],
                    )

            # Limit to max_results
            urls = urls[:max_results]

            logger.info(
                "Found %s candidate Reddit URLs for %s using %s; "
                "scraping + classifying.",
                len(urls),
                self.product,
                self.llm_option,
            )

            # Limit concurrent scraping to avoid overwhelming Playwright
            sem = asyncio.Semaphore(4)

            async def run_one(u: str):
                async with sem:
                    return await self._scrape_classify_and_save_product_page(
                        product_obj, u
                    )

            results = await asyncio.gather(
                *(run_one(u) for u in urls), return_exceptions=True
            )
            pages: List[ProductPage] = []
            for r in results:
                if isinstance(r, Exception):
                    logger.warning(f"Scrape/classify task failed: {r}")
                    continue
                if r is not None:
                    pages.append(r)

            return pages

        except Exception as e:
            logger.error(
                "Error finding Reddit pages for %s using %s: %s",
                self.product,
                self.llm_option,
                e,
            )
            return []

    def find_product_pages_sync(self, max_results: int = 20) -> List[ProductPage]:
        """
        Return product pages synchronously.

        Args:
            max_results: Maximum number of Reddit URLs to find/scrape

        Returns:
            List of ProductPage objects
        """
        return asyncio.run(self.find_product_pages(max_results=max_results))

    async def _scrape_classify_and_save_product_page(
        self, product_obj, url: str
    ) -> ProductPage | None:
        """
        Scrape a single URL, classify relevance, and only then save a ProductPage row.

        IMPORTANT: We only save if the page is relevant.
        """
        try:

            def _get_existing_page():
                existing_pages = self.product_page_service.get_by_product(product_obj)
                return next((p for p in existing_pages if p.url == url), None)

            existing_page = await sync_to_async(
                _get_existing_page, thread_sensitive=True
            )()

            # If already saved/scraped, return it (we only save relevant pages).
            if existing_page and existing_page.status == "scraped":
                return existing_page

            scraper = WebPageScraper(url=url)
            html = await scraper.scrape_page_html()

            if html and scraper.is_valid_page(html):
                text = scraper.scrape_page_text()

                relevance = await self.classifier.classify(url=url, page_text=text)
                if not relevance.relevant:
                    logger.info(
                        "Skipping irrelevant page: %s (confidence=%.2f)",
                        url,
                        relevance.confidence,
                    )
                    return None

                def _create_scraped():
                    return self.product_page_service.create(
                        product=product_obj,
                        url=url,
                        html=html,
                        text=text,
                        status="scraped",
                    )[0]

                page = await sync_to_async(_create_scraped, thread_sensitive=True)()
                return page

            # Not valid / couldn't scrape => do not save anything (per requirement)
            return None
        except Exception as e:
            logger.warning(f"Failed to scrape/save ProductPage for {url}: {e}")
            return None

    # Backward-compatible URL-returning methods
    async def find_reddit_pages(self, max_results: int = 20) -> List[str]:
        """Backward-compatible wrapper returning URLs."""
        pages = await self.find_product_pages(max_results=max_results)
        return [p.url for p in pages]

    def find_reddit_pages_sync(self, max_results: int = 20) -> List[str]:
        """Backward-compatible wrapper returning URLs."""
        return [p.url for p in self.find_product_pages_sync(max_results=max_results)]

    def _extract_urls(self, text: str) -> List[str]:
        """Extract Reddit URLs from LLM response text."""
        urls = []

        # Pattern to match Reddit URLs
        reddit_url_pattern = r"https?://(?:[a-z]+\.)?reddit\.com/[^\s\)]+"
        redd_it_pattern = r"https?://redd\.it/[^\s\)]+"

        matches = re.findall(reddit_url_pattern, text)
        matches += re.findall(redd_it_pattern, text)

        for url in matches:
            # Clean up URL (remove trailing punctuation)
            url = url.rstrip(".,;!?)")
            if url not in urls:
                urls.append(url)

        # Also try to find URLs without protocol
        no_protocol_pattern = r"(?:[a-z]+\.)?reddit\.com/[^\s\)]+"
        matches = re.findall(no_protocol_pattern, text)

        for match in matches:
            url = f"https://{match.rstrip('.,;!?)')}"
            if url not in urls:
                urls.append(url)

        return urls
