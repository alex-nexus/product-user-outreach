import asyncio
import logging
from reddit_outreach.agents.product_page_finder import ProductPageFinder
from reddit_outreach.services.web_page_scraper import WebPageScraper
from reddit_outreach.services.product_service import ProductService
from reddit_outreach.services.product_page_service import ProductPageService

logger = logging.getLogger(__name__)


class FindRedditPagesWorkflow:
    """Workflow to find and scrape Reddit pages for a given product."""
    
    def __init__(self):
        """
        Initialize the workflow.
        """
        self.llm_providers = ['openai', 'gemini', 'grok']
        self.product_service = ProductService()
        self.product_page_service = ProductPageService()
    
    def execute(self, product_name: str, max_urls: int = 20):
        """
        Main entry point for the workflow.
        
        Given a product, find all Reddit pages where it's discussed.
        
        Args:
            product_name: Name of the product to find Reddit pages for
            max_urls: Maximum number of Reddit URLs to search for
            
        Returns:
            dict with summary of results
        """
        logger.info(f"Starting workflow to find Reddit pages for product: {product_name}")
        
        # Get or create product
        product, created = self.product_service.get_or_create(product_name)
        logger.info(f"Product: {product.name} ({'created' if created else 'existing'})")
        
        # Step 1: Search for Reddit pages using multiple LLMs
        logger.info("Step 1: Searching for Reddit pages using multiple LLMs...")
        reddit_urls = self._search_reddit_pages_all_llms(product_name, max_urls)
        
        if not reddit_urls:
            logger.warning(f"No Reddit URLs found for {product_name}")
            return {
                'product': product,
                'urls_found': 0,
                'pages_scraped': 0,
                'success': False,
                'message': 'No Reddit URLs found'
            }
        
        logger.info(f"Found {len(reddit_urls)} unique Reddit URLs across all LLMs")
        
        # Step 2: Scrape pages (async)
        logger.info("Step 2: Scraping Reddit pages...")
        scraped_pages = self._scrape_pages_async(product, reddit_urls)
        
        if not scraped_pages:
            logger.warning(f"No pages successfully scraped for {product_name}")
            return {
                'product': product,
                'urls_found': len(reddit_urls),
                'pages_scraped': 0,
                'success': False,
                'message': 'No pages successfully scraped'
            }
        
        logger.info(f"Successfully scraped {len(scraped_pages)} pages")
        
        return {
            'product': product,
            'urls_found': len(reddit_urls),
            'pages_scraped': len(scraped_pages),
            'pages': scraped_pages,
            'success': True,
            'message': f'Successfully found and scraped {len(scraped_pages)} Reddit pages'
        }
    
    def _search_reddit_pages_all_llms(self, product_name: str, max_urls: int = 20):
        """
        Search for Reddit pages using all LLM providers and aggregate results.
        
        Args:
            product_name: Name of the product to search for
            max_urls: Maximum number of URLs per LLM provider
            
        Returns:
            list of unique Reddit URLs
        """
        all_urls = set()
        successful_providers = []
        failed_providers = []
        
        for llm_provider in self.llm_providers:
            try:
                logger.info(f"Trying {llm_provider} for product: {product_name}")
                page_finder = ProductPageFinder(product=product_name, llm_option=llm_provider)
                urls = page_finder.find_reddit_pages_sync(max_results=max_urls)
                
                # Add URLs to the set (automatically handles duplicates)
                for url in urls:
                    all_urls.add(url)
                
                logger.info(f"{llm_provider} found {len(urls)} URLs (total unique: {len(all_urls)})")
                successful_providers.append(llm_provider)
                
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
                logger.warning(f"Error using {llm_provider} to search for Reddit pages: {e}")
                failed_providers.append(f"{llm_provider} (error: {str(e)[:50]})")
                continue
        
        if successful_providers:
            logger.info(f"Successfully used {len(successful_providers)} LLM provider(s): {', '.join(successful_providers)}")
        if failed_providers:
            logger.warning(f"Failed to use {len(failed_providers)} LLM provider(s): {', '.join(failed_providers)}")
        
        return list(all_urls)
    
    async def _scrape_single_page(self, product, url: str):
        """Scrape a single Reddit URL and return the ProductPage or None."""
        try:
            logger.info(f"Scraping: {url}")
            
            # Check if page already exists
            existing_pages = self.product_page_service.get_by_product(product)
            existing_page = next((p for p in existing_pages if p.url == url), None)
            
            if existing_page and existing_page.status == 'scraped':
                logger.info(f"Page already scraped: {url}")
                return existing_page
            
            # Create scraper instance
            scraper = WebPageScraper(url=url)
            
            # Scrape the page
            html = await scraper.scrape_page_html()
            
            if html and scraper.is_valid_page(html):
                # Extract text from HTML
                text = scraper.scrape_page_text()
                
                # Create or update ProductPage
                page, created = self.product_page_service.create(
                    product=product,
                    url=url,
                    html=html,
                    text=text,
                    status='scraped'
                )
                
                if created:
                    logger.info(f"Created new page: {url}")
                else:
                    logger.info(f"Updated existing page: {url}")
                
                return page
            else:
                # Mark as failed if it exists
                if existing_page:
                    self.product_page_service.update_status(existing_page, 'failed')
                else:
                    # Create failed page record
                    self.product_page_service.create(
                        product=product,
                        url=url,
                        status='failed'
                    )
                logger.warning(f"Failed to scrape: {url}")
                return None
                
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            # Create failed page record
            try:
                self.product_page_service.create(
                    product=product,
                    url=url,
                    status='failed'
                )
            except Exception:
                pass
            return None
    
    def _scrape_pages_async(self, product, urls: list):
        """Scrape each Reddit URL and store in database (async)."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        async def scrape_all():
            tasks = [self._scrape_single_page(product, url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            scraped_pages = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Scraping task failed: {result}")
                elif result is not None:
                    scraped_pages.append(result)
            
            return scraped_pages
        
        return loop.run_until_complete(scrape_all())

