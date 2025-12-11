import asyncio
import re
import logging
from django.conf import settings
from reddit_outreach.clients.search_clients import create_search_client, SearchQuery

logger = logging.getLogger(__name__)


class WebSearchAgent:
    def __init__(self, search_provider='google'):
        """
        Initialize WebSearchAgent with a search client.
        
        Args:
            search_provider: Search provider to use ('google', 'duckduckgo', 'bing')
        """
        self.search_provider = search_provider
        self.search_client = create_search_client(provider=search_provider)

    async def find_reddit_urls(self, product_name, max_results=20):
        """
        Use web search to find Reddit URLs mentioning the product.
        
        Args:
            product_name: Name of the product to search for
            max_results: Maximum number of results to return
            
        Returns:
            list of Reddit URLs (strings)
        """
        try:
            logger.info(f"Searching for Reddit URLs for product: {product_name} using {self.search_provider}")
            
            # Create search query for Reddit pages about the product
            query = SearchQuery(
                query=f"{product_name} site:reddit.com",
                page_size=min(max_results, 10),  # Most APIs return max 10 per page
            )
            
            urls = []
            pages_to_search = (max_results + 9) // 10  # Calculate pages needed
            
            for page_num in range(1, pages_to_search + 1):
                query.page = page_num
                
                async for result in self.search_client.search(query):
                    # Filter to only Reddit URLs
                    if 'reddit.com' in result.url:
                        url = result.url
                        # Clean up URL (remove trailing punctuation)
                        url = url.rstrip('.,;!?)')
                        if url not in urls:
                            urls.append(url)
                            logger.debug(f"Found Reddit URL: {url}")
                    
                    if len(urls) >= max_results:
                        break
                
                if len(urls) >= max_results:
                    break
            
            logger.info(f"Found {len(urls)} Reddit URLs for {product_name}")
            return urls
            
        except Exception as e:
            logger.error(f"Error finding Reddit URLs for {product_name}: {e}")
            return []

    def find_reddit_urls_sync(self, product_name, max_results=20):
        """
        Synchronous wrapper for find_reddit_urls.
        
        Args:
            product_name: Name of the product to search for
            max_results: Maximum number of results to return
            
        Returns:
            list of Reddit URLs (strings)
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.find_reddit_urls(product_name, max_results))

