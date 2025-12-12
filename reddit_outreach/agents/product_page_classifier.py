"""Product page relevance classifier for Reddit pages."""

import logging
from dataclasses import dataclass, field
from typing import Final

from pydantic import BaseModel, Field

from reddit_outreach.clients.llm import BaseLLM, create_llm_client

logger = logging.getLogger(__name__)

_MAX_CHARS: Final[int] = 12_000


class ProductPageRelevance(BaseModel):
    """Structured relevance decision for a product page."""

    relevant: bool = Field(
        description="Whether this Reddit page is relevant to the product"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score between 0 and 1"
    )
    reason: str = Field(description="Short reason for the decision")


@dataclass
class ProductPageClassifier:
    """Classify whether a scraped Reddit page is relevant to a product."""

    product: str
    llm_option: str = "openai"
    llm: BaseLLM = field(init=False, repr=False)

    def __post_init__(self):
        """Initialize the underlying LLM client."""
        self.llm_option = self.llm_option.lower()
        # No web search needed for classification
        self.llm = create_llm_client(
            provider=self.llm_option,
            enable_web_search=False,
        )

    async def classify(self, *, url: str, page_text: str) -> ProductPageRelevance:
        """Return whether the page is relevant to the configured product."""
        snippet = page_text[:_MAX_CHARS]

        system_prompt = (
            "You are a strict relevance classifier. "
            "Decide if a Reddit page is relevant to the given product. "
            "Relevant means the page content strongly indicates discussion about "
            "the product, or clear user mention/usage. "
            "If it's only coincidental text, unrelated, or ambiguous, mark not "
            "relevant."
        )

        prompt = (
            f"Product: {self.product}\n"
            f"URL: {url}\n\n"
            "Classify if this Reddit page is relevant to the product.\n"
            "Return JSON with fields: relevant (bool), confidence (0..1), "
            "reason (string).\n\n"
            "Page text:\n"
            f"{snippet}"
        )

        result = await self.llm.run(
            prompt=prompt,
            system_prompt=system_prompt,
            output_type=ProductPageRelevance,
        )
        return result
