import asyncio
import re
import logging
from django.conf import settings
from typing import List, Optional

logger = logging.getLogger(__name__)


class WebSearchAgent:
    """LLM-based web search agent for finding Reddit URLs."""
    
    def __init__(self, llm_provider='openai'):
        """
        Initialize WebSearchAgent with an LLM provider.
        
        Args:
            llm_provider: LLM provider to use ('openai', 'gemini', 'grok')
        """
        self.llm_provider = llm_provider
        self._client = self._initialize_client()

    def _initialize_client(self):
        """Initialize the LLM client based on provider."""
        if self.llm_provider == 'openai':
            from openai import OpenAI
            api_key = getattr(settings, 'OPENAI_API_KEY', '')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set in settings")
            return OpenAI(api_key=api_key)
        
        elif self.llm_provider == 'gemini':
            try:
                import google.generativeai as genai
                api_key = getattr(settings, 'GEMINI_API_KEY', '') or getattr(settings, 'GOOGLE_API_KEY', '')
                if not api_key:
                    raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not set in settings")
                genai.configure(api_key=api_key)
                return genai
            except ImportError:
                raise ImportError("google-generativeai package is required. Install with: pip install google-generativeai")
        
        elif self.llm_provider == 'grok':
            try:
                from groq import Groq
                api_key = getattr(settings, 'GROK_API_KEY', '')
                if not api_key:
                    raise ValueError("GROK_API_KEY not set in settings")
                # Groq provides access to various models including those compatible with Grok
                return Groq(api_key=api_key)
            except ImportError:
                raise ImportError("groq package is required for Grok. Install with: pip install groq")
        
        else:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")

    def find_reddit_urls(self, product_name: str, max_results: int = 20) -> List[str]:
        """
        Use LLM with web search to find Reddit URLs mentioning the product.
        
        Args:
            product_name: Name of the product to search for
            max_results: Maximum number of results to return
            
        Returns:
            list of Reddit URLs (strings)
        """
        try:
            logger.info(f"Searching for Reddit URLs for product: {product_name} using {self.llm_provider}")
            
            prompt = f"""Find Reddit URLs where users discuss or mention "{product_name}". 
Search the web for Reddit posts, comments, or discussions about this product.

Please provide a list of Reddit URLs (reddit.com URLs) where this product is mentioned.
Format your response as a list of URLs, one per line, or as a numbered list.
Only include valid Reddit URLs (reddit.com/r/... or reddit.com/user/...).

Product: {product_name}

Provide at least {max_results} Reddit URLs if possible."""

            response_content = self._call_llm(prompt)
            urls = self._extract_urls(response_content)
            
            # Limit to max_results
            urls = urls[:max_results]
            
            logger.info(f"Found {len(urls)} Reddit URLs for {product_name} using {self.llm_provider}")
            return urls
            
        except Exception as e:
            logger.error(f"Error finding Reddit URLs for {product_name} using {self.llm_provider}: {e}")
            return []

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM with the given prompt."""
        if self.llm_provider == 'openai':
            response = self._client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that finds Reddit URLs related to products. You use web search capabilities to find relevant Reddit discussions."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=getattr(settings, 'AI_MAX_TOKENS', 2000),
                temperature=getattr(settings, 'AI_TEMPERATURE', 0.7),
            )
            return response.choices[0].message.content
        
        elif self.llm_provider == 'gemini':
            model = self._client.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            return response.text
        
        elif self.llm_provider == 'grok':
            # Groq client uses OpenAI-compatible API
            response = self._client.chat.completions.create(
                model="llama-3.1-70b-versatile",  # Groq compatible model (can be changed to other models)
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that finds Reddit URLs related to products. You use web search capabilities to find relevant Reddit discussions."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=getattr(settings, 'AI_MAX_TOKENS', 2000),
                temperature=getattr(settings, 'AI_TEMPERATURE', 0.7),
            )
            return response.choices[0].message.content
        
        else:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")

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

