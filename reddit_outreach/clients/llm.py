import os
from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Type, Union
from pydantic import BaseModel

try:
    from pydantic_ai import Agent, ModelClient
    from pydantic_ai.models.openai import OpenAIModel
    from pydantic_ai.models.gemini import GeminiModel
    from pydantic_ai.models.groq import GroqModel
except ImportError:
    raise ImportError(
        "pydantic-ai package is required. Install with: pip install pydantic-ai"
    )

from django.conf import settings

T = TypeVar('T', bound=BaseModel)


class BaseLLM(ABC):
    """Abstract base class for LLM clients using PydanticAI."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the LLM client.
        
        Args:
            api_key: API key for the LLM provider
            model: Model name to use
        """
        self.api_key = api_key
        self.model = model
        self._client = self._initialize_client()
    
    @abstractmethod
    def _initialize_client(self) -> ModelClient:
        """Initialize the PydanticAI ModelClient."""
        raise NotImplementedError
    
    @abstractmethod
    async def run(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        output_type: Optional[Type[T]] = None,
        **kwargs
    ) -> Union[T, str]:
        """
        Run the LLM with the given prompt and return structured output.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            output_type: Optional Pydantic model class for structured output
            **kwargs: Additional arguments for the model
        
        Returns:
            Structured output if output_type is provided, otherwise string
        """
        raise NotImplementedError


class OpenAILLM(BaseLLM):
    """OpenAI LLM client using PydanticAI."""
    
    DEFAULT_MODEL = "gpt-4"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize OpenAI LLM client.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY from settings)
            model: Model name (defaults to gpt-4)
        """
        self.api_key = api_key or getattr(settings, 'OPENAI_API_KEY', None) or os.getenv('OPENAI_API_KEY')
        self.model = model or self.DEFAULT_MODEL
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required")
        
        super().__init__(api_key=self.api_key, model=self.model)
    
    def _initialize_client(self) -> ModelClient:
        """Initialize OpenAI ModelClient."""
        return OpenAIModel(
            self.model,
            api_key=self.api_key,
        )
    
    async def run(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        output_type: Optional[Type[T]] = None,
        **kwargs
    ) -> Union[T, str]:
        """
        Run OpenAI model with structured output support.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            output_type: Optional Pydantic model class for structured output
            **kwargs: Additional arguments (temperature, max_tokens, etc.)
        
        Returns:
            Structured output if output_type is provided, otherwise string
        """
        agent = Agent(
            self._client,
            system_prompt=system_prompt,
            result_type=output_type,
        )
        
        result = await agent.run(prompt, **kwargs)
        
        if output_type:
            return result.data
        return result.data if isinstance(result.data, str) else str(result.data)


class GeminiLLM(BaseLLM):
    """Google Gemini LLM client using PydanticAI."""
    
    DEFAULT_MODEL = "gemini-pro"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize Gemini LLM client.
        
        Args:
            api_key: Google API key (defaults to GEMINI_API_KEY or GOOGLE_API_KEY from settings)
            model: Model name (defaults to gemini-pro)
        """
        self.api_key = (
            api_key 
            or getattr(settings, 'GEMINI_API_KEY', None) 
            or getattr(settings, 'GOOGLE_API_KEY', None)
            or os.getenv('GEMINI_API_KEY')
            or os.getenv('GOOGLE_API_KEY')
        )
        self.model = model or self.DEFAULT_MODEL
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is required")
        
        super().__init__(api_key=self.api_key, model=self.model)
    
    def _initialize_client(self) -> ModelClient:
        """Initialize Gemini ModelClient."""
        return GeminiModel(
            self.model,
            api_key=self.api_key,
        )
    
    async def run(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        output_type: Optional[Type[T]] = None,
        **kwargs
    ) -> Union[T, str]:
        """
        Run Gemini model with structured output support.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            output_type: Optional Pydantic model class for structured output
            **kwargs: Additional arguments (temperature, max_tokens, etc.)
        
        Returns:
            Structured output if output_type is provided, otherwise string
        """
        agent = Agent(
            self._client,
            system_prompt=system_prompt,
            result_type=output_type,
        )
        
        result = await agent.run(prompt, **kwargs)
        
        if output_type:
            return result.data
        return result.data if isinstance(result.data, str) else str(result.data)


class GrokLLM(BaseLLM):
    """Grok (via Groq) LLM client using PydanticAI."""
    
    DEFAULT_MODEL = "llama-3.1-70b-versatile"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize Grok LLM client.
        
        Args:
            api_key: Groq API key (defaults to GROK_API_KEY or GROQ_API_KEY from settings)
            model: Model name (defaults to llama-3.1-70b-versatile)
        """
        self.api_key = (
            api_key 
            or getattr(settings, 'GROK_API_KEY', None)
            or getattr(settings, 'GROQ_API_KEY', None)
            or os.getenv('GROK_API_KEY')
            or os.getenv('GROQ_API_KEY')
        )
        self.model = model or self.DEFAULT_MODEL
        
        if not self.api_key:
            raise ValueError("GROK_API_KEY or GROQ_API_KEY is required")
        
        super().__init__(api_key=self.api_key, model=self.model)
    
    def _initialize_client(self) -> ModelClient:
        """Initialize Groq ModelClient."""
        return GroqModel(
            self.model,
            api_key=self.api_key,
        )
    
    async def run(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        output_type: Optional[Type[T]] = None,
        **kwargs
    ) -> Union[T, str]:
        """
        Run Groq model with structured output support.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            output_type: Optional Pydantic model class for structured output
            **kwargs: Additional arguments (temperature, max_tokens, etc.)
        
        Returns:
            Structured output if output_type is provided, otherwise string
        """
        agent = Agent(
            self._client,
            system_prompt=system_prompt,
            result_type=output_type,
        )
        
        result = await agent.run(prompt, **kwargs)
        
        if output_type:
            return result.data
        return result.data if isinstance(result.data, str) else str(result.data)


def create_llm_client(
    provider: str = "openai",
    **kwargs,
) -> BaseLLM:
    """
    Factory function to create an LLM client.
    
    Args:
        provider: LLM provider name ("openai", "gemini", "grok")
        **kwargs: Additional arguments passed to the client constructor
    
    Returns:
        BaseLLM instance
    
    Raises:
        ValueError: If provider is not supported
    """
    providers = {
        "openai": OpenAILLM,
        "gemini": GeminiLLM,
        "grok": GrokLLM,
    }
    
    client_class = providers.get(provider.lower())
    if not client_class:
        raise ValueError(
            f"Unsupported provider: {provider}. "
            f"Supported providers: {', '.join(providers.keys())}"
        )
    
    return client_class(**kwargs)

