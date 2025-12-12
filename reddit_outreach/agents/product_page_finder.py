import asyncio
import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional
from pydantic import BaseModel, Field

from reddit_outreach.clients.llm import create_llm_client, BaseLLM

logger = logging.getLogger(__name__)


class RedditUrlsResponse(BaseModel):
    """Structured response model for Reddit URLs."""
    urls: List[str] = Field(description="List of Reddit URLs related to the product")


@dataclass
class ProductPageFinder:
    """LLM-based agent for finding Reddit product pages using built-in web search."""
    
    product: str
    llm_option: str = "openai"
    llm: BaseLLM = field(init=False, repr=False)
    
    def __post_init__(self):
        """Initialize the LLM client after dataclass initialization."""
        self.llm_option = self.llm_option.lower()
        self.llm = create_llm_client(
            provider=self.llm_option,
            enable_web_search=True,
        )
    
    async def find_reddit_pages(self, max_results: int = 20) -> List[str]:
        """
        Find Reddit product pages for the given product.
        
        Uses the LLM's built-in web search to find Reddit URLs where the product
        is discussed or mentioned.
        
        Args:
            max_results: Maximum number of Reddit URLs to return
            
        Returns:
            List of Reddit URLs (strings)
        """
        try:
            logger.info(f"Finding Reddit pages for product: {self.product} using {self.llm_option}")
            
            system_prompt = (
                "You are a helpful assistant that finds Reddit URLs related to products. "
                "Use web search to find relevant Reddit discussions, posts, and comments about products. "
                "Return only valid Reddit URLs (reddit.com/r/... or reddit.com/user/...)."
            )
            
            prompt = f"""Find Reddit URLs where users discuss or mention "{self.product}". 

Search the web for Reddit posts, comments, or discussions about this product.

Please provide a list of Reddit URLs (reddit.com URLs) where this product is mentioned.
Format your response as a list of URLs, one per line, or as a numbered list.
Only include valid Reddit URLs (reddit.com/r/... or reddit.com/user/...).

Product: {self.product}

Provide at least {max_results} Reddit URLs if possible."""

            # Run the LLM with web search enabled
            response = await self.llm.run(
                prompt=prompt,
                system_prompt=system_prompt,
            )
            
            # Extract URLs from the response
            urls = self._extract_urls(str(response))
            
            # Limit to max_results
            urls = urls[:max_results]
            
            logger.info(f"Found {len(urls)} Reddit URLs for {self.product} using {self.llm_option}")
            return urls
            
        except Exception as e:
            logger.error(f"Error finding Reddit pages for {self.product} using {self.llm_option}: {e}")
            return []
    
    def find_reddit_pages_sync(self, max_results: int = 20) -> List[str]:
        """
        Synchronous wrapper for find_reddit_pages.
        
        Args:
            max_results: Maximum number of Reddit URLs to return
            
        Returns:
            List of Reddit URLs (strings)
        """
        return asyncio.run(self.find_reddit_pages(max_results=max_results))
    
    def _extract_urls(self, text: str) -> List[str]:
        """Extract Reddit URLs from LLM response text."""
        urls = []
        
        # Pattern to match Reddit URLs
        reddit_url_pattern = r'https?://(?:www\.)?reddit\.com/[^\s\)]+'
        
        matches = re.findall(reddit_url_pattern, text)
        
        for url in matches:
            # Clean up URL (remove trailing punctuation)
            url = url.rstrip('.,;!?)')
            if url not in urls:
                urls.append(url)
        
        # Also try to find URLs without protocol
        no_protocol_pattern = r'reddit\.com/[^\s\)]+'
        matches = re.findall(no_protocol_pattern, text)
        
        for match in matches:
            url = f"https://{match.rstrip('.,;!?)')}"
            if url not in urls:
                urls.append(url)
        
        return urls

