"""LLM client wrappers (OpenAI, Gemini, Groq) using PydanticAI."""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Type, TypeVar, Union

import httpx
from django.conf import settings
from pydantic import BaseModel

try:
    from pydantic_ai import Agent, WebSearchTool, models
    from pydantic_ai.models.gemini import GeminiModel
    from pydantic_ai.models.groq import GroqModel
    from pydantic_ai.models.openai import OpenAIResponsesModel
    from pydantic_ai.providers.groq import GroqProvider
    from pydantic_ai.providers.openai import OpenAIProvider
except ImportError as e:
    raise ImportError(
        "pydantic-ai is required. Install with: pip install pydantic-ai"
    ) from e


T = TypeVar("T", bound=BaseModel)

# In this environment, reading system/site-packages CA bundles may be blocked.
# If a CA bundle is present in the workspace, point SSL to it.
_WORKSPACE_CA_BUNDLE = Path(__file__).resolve().parents[2] / "certs" / "cacert.pem"
if _WORKSPACE_CA_BUNDLE.exists():
    os.environ.setdefault("SSL_CERT_FILE", str(_WORKSPACE_CA_BUNDLE))
    os.environ.setdefault("REQUESTS_CA_BUNDLE", str(_WORKSPACE_CA_BUNDLE))


class BaseLLM(ABC):
    """Base wrapper around PydanticAI models with optional built-in web search."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        enable_web_search: bool = False,
    ):
        """Initialize the wrapper and underlying model."""
        self.api_key = api_key
        self.model = model
        self.enable_web_search = enable_web_search
        self._model = self._initialize_model()

    @abstractmethod
    def _initialize_model(self) -> models.Model:
        raise NotImplementedError

    async def run(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        output_type: Optional[Type[T]] = None,
        *,
        model_settings: Optional[models.ModelSettings] = None,
    ) -> Union[T, str]:
        """Run the model and return either `output_type` or `str` output."""
        builtin_tools = [WebSearchTool()] if self.enable_web_search else []

        agent = Agent(
            model=self._model,
            output_type=output_type or str,
            system_prompt=system_prompt or (),
            builtin_tools=builtin_tools,
        )

        result = await agent.run(prompt, model_settings=model_settings)
        return result.output


class OpenAILLM(BaseLLM):
    """OpenAI via PydanticAI (Responses API)."""

    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        enable_web_search: bool = False,
    ):
        """Initialize OpenAI client (uses Responses API model)."""
        api_key = (
            api_key
            or getattr(settings, "OPENAI_API_KEY", None)
            or os.getenv("OPENAI_API_KEY")
        )
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required")

        os.environ.setdefault("OPENAI_API_KEY", api_key)

        super().__init__(
            api_key=api_key,
            model=model or self.DEFAULT_MODEL,
            enable_web_search=enable_web_search,
        )

    def _initialize_model(self) -> models.Model:
        verify = str(_WORKSPACE_CA_BUNDLE) if _WORKSPACE_CA_BUNDLE.exists() else True
        http_client = httpx.AsyncClient(verify=verify)
        provider = OpenAIProvider(api_key=self.api_key, http_client=http_client)
        return OpenAIResponsesModel(self.model, provider=provider)


class GeminiLLM(BaseLLM):
    """Google Gemini via PydanticAI."""

    DEFAULT_MODEL = "gemini-1.5-flash"

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        enable_web_search: bool = False,
    ):
        """Initialize Gemini client."""
        api_key = (
            api_key
            or getattr(settings, "GEMINI_API_KEY", None)
            or getattr(settings, "GOOGLE_API_KEY", None)
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is required")

        os.environ.setdefault("GEMINI_API_KEY", api_key)
        os.environ.setdefault("GOOGLE_API_KEY", api_key)

        super().__init__(
            api_key=api_key,
            model=model or self.DEFAULT_MODEL,
            enable_web_search=enable_web_search,
        )

    def _initialize_model(self) -> models.Model:
        return GeminiModel(self.model)


class GrokLLM(BaseLLM):
    """Grok option backed by Groq via PydanticAI."""

    DEFAULT_MODEL = "llama-3.1-70b-versatile"

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        enable_web_search: bool = False,
    ):
        """Initialize Groq client (used for 'grok' option)."""
        api_key = (
            api_key
            or getattr(settings, "GROK_API_KEY", None)
            or getattr(settings, "GROQ_API_KEY", None)
            or os.getenv("GROK_API_KEY")
            or os.getenv("GROQ_API_KEY")
        )
        if not api_key:
            raise ValueError("GROK_API_KEY or GROQ_API_KEY is required")

        os.environ.setdefault("GROQ_API_KEY", api_key)

        super().__init__(
            api_key=api_key,
            model=model or self.DEFAULT_MODEL,
            enable_web_search=enable_web_search,
        )

    def _initialize_model(self) -> models.Model:
        verify = str(_WORKSPACE_CA_BUNDLE) if _WORKSPACE_CA_BUNDLE.exists() else True
        http_client = httpx.AsyncClient(verify=verify)
        provider = GroqProvider(api_key=self.api_key, http_client=http_client)
        return GroqModel(self.model, provider=provider)


def create_llm_client(provider: str = "openai", **kwargs) -> BaseLLM:
    """Create a `BaseLLM` instance for the given provider."""
    providers = {
        "openai": OpenAILLM,
        "gemini": GeminiLLM,
        "grok": GrokLLM,
    }
    client_class = providers.get(provider.lower())
    if not client_class:
        supported = ", ".join(providers.keys())
        raise ValueError(
            f"Unsupported provider: {provider}. Supported providers: {supported}"
        )
    return client_class(**kwargs)
