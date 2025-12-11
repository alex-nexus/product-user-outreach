import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generator, List, Optional

import httpx

GOOGLE_API_KEY = (
    os.getenv("GOOGLE_API_KEY") or "AIzaSyAKIGBOROqOrJzTuYW6WvYpmOrdwc3AEsg"
)
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID") or "00414618cab824955"
# https://programmablesearchengine.google.com/u/1/controlpanel/overview?cx=00414618cab824955


@dataclass
class SearchQuery:
    """Generic search query with keyword filtering."""

    query: str
    exclude_keywords: List[str] = field(default_factory=list)
    exclude_domains: List[str] = field(default_factory=list)
    page: int = 1
    page_size: int = 10

    def format_query(self) -> str:
        """Format the query string with exclusions."""
        q = self.query

        if self.exclude_keywords:
            q += " " + " ".join([f"-{k}" for k in self.exclude_keywords])

        if self.exclude_domains:
            q += " " + " ".join([f"-site:{d}" for d in self.exclude_domains])

        return q


@dataclass
class SearchResult:
    """Generic search result item."""

    title: str
    snippet: str
    url: str
    source: Optional[str] = None  # Optional source identifier

    def to_prompt(self) -> str:
        """Generate a prompt representation of this search result."""
        parts = [f"URL: {self.url}"]
        if self.title:
            parts.append(f"Title: {self.title}")
        if self.snippet:
            parts.append(f"Snippet: {self.snippet}")
        return "\n".join(parts)


class SearchClient(ABC):
    """Abstract base class for search clients."""

    @abstractmethod
    async def search(self, query: SearchQuery) -> Generator[SearchResult, None, None]:
        """
        Search for items matching the query.

        Args:
            query: SearchQuery object with search parameters

        Yields:
            SearchResult objects
        """
        raise NotImplementedError


class GoogleSearchClient(SearchClient):
    """Google Custom Search API client."""

    BASE_URL = "https://customsearch.googleapis.com/customsearch/v1"
    DEFAULT_PAGE_SIZE = 10
    DEFAULT_CSE_ID = "00414618cab824955"

    def __init__(
        self,
        api_key: Optional[str] = None,
        search_engine_id: Optional[str] = None,
    ):
        """
        Initialize Google Search Client.

        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY env var)
            search_engine_id: Custom Search Engine ID
                (defaults to GOOGLE_CSE_ID env var, or DEFAULT_CSE_ID)
        """
        self.api_key = api_key or GOOGLE_API_KEY
        self.search_engine_id = search_engine_id or GOOGLE_CSE_ID or self.DEFAULT_CSE_ID

        if not self.api_key:
            raise ValueError("Google API key is required")
        if not self.search_engine_id:
            raise ValueError("Google Custom Search Engine ID is required")

    async def search(self, query: SearchQuery) -> Generator[SearchResult, None, None]:
        """Search using Google Custom Search API."""
        start = (query.page - 1) * query.page_size + 1
        params = {
            "q": query.format_query(),
            "cx": self.search_engine_id,
            "num": query.page_size,
            "key": self.api_key,
            "start": start,
            "alt": "json",
            "language": "en",
            "safe": "off",
        }

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582"
            )
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(self.BASE_URL, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            for item in data.get("items", []):
                yield SearchResult(
                    title=item.get("title", ""),
                    snippet=item.get("snippet", ""),
                    url=item.get("link", ""),
                    source="google",
                )


class DuckDuckGoSearchClient(SearchClient):
    """DuckDuckGo search client."""

    DEFAULT_PAGE_SIZE = 10

    def __init__(self, proxy: Optional[str] = None, timeout: int = 20):
        """
        Initialize DuckDuckGo Search Client.

        Args:
            proxy: Optional proxy URL (e.g., "socks5://localhost:9150")
            timeout: Request timeout in seconds
        """
        self.proxy = proxy
        self.timeout = timeout

    async def search(self, query: SearchQuery) -> Generator[SearchResult, None, None]:
        """Search using DuckDuckGo."""
        try:
            from duckduckgo_search import DDGS

            ddgs = DDGS(proxy=self.proxy, timeout=self.timeout)
            results = ddgs.text(query.format_query(), max_results=query.page_size)

            for item in results:
                yield SearchResult(
                    title=item.get("title", ""),
                    snippet=item.get("body", ""),
                    url=item.get("href", ""),
                    source="duckduckgo",
                )
        except ImportError:
            raise ImportError(
                "duckduckgo_search package is required. "
                "Install it with: pip install duckduckgo-search"
            )
        except Exception as e:
            raise RuntimeError(f"DuckDuckGo search failed: {e}") from e


class BingSearchClient(SearchClient):
    """Bing search client using LangChain wrapper."""

    DEFAULT_PAGE_SIZE = 10

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Bing Search Client.

        Args:
            api_key: Bing API key (defaults to BING_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("BING_API_KEY")

        if not self.api_key:
            raise ValueError("Bing API key is required")

    async def search(self, query: SearchQuery) -> Generator[SearchResult, None, None]:
        """Search using Bing API."""
        try:
            from langchain_community.utilities import BingSearchAPIWrapper

            wrapper = BingSearchAPIWrapper(bing_subscription_key=self.api_key)
            results = wrapper.results(query.format_query(), query.page_size)

            for item in results:
                yield SearchResult(
                    title=item.get("title", ""),
                    snippet=item.get("snippet", ""),
                    url=item.get("link", ""),
                    source="bing",
                )
        except ImportError:
            raise ImportError(
                "langchain_community package is required. "
                "Install it with: pip install langchain-community"
            )
        except Exception as e:
            raise RuntimeError(f"Bing search failed: {e}") from e


def create_search_client(
    provider: str = "google",
    **kwargs,
) -> SearchClient:
    """
    Factory function to create a search client.

    Args:
        provider: Search provider name ("google", "duckduckgo", "bing")
        **kwargs: Additional arguments passed to the client constructor

    Returns:
        SearchClient instance

    Raises:
        ValueError: If provider is not supported
    """
    providers = {
        "google": GoogleSearchClient,
        "duckduckgo": DuckDuckGoSearchClient,
        "bing": BingSearchClient,
    }

    client_class = providers.get(provider.lower())
    if not client_class:
        raise ValueError(
            f"Unsupported provider: {provider}. "
            f"Supported providers: {', '.join(providers.keys())}"
        )

    return client_class(**kwargs)
